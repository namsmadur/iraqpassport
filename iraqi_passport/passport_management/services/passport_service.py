# -*- coding: utf-8 -*-
# Passport business logic service.

import os
import random

import frappe
from frappe import _
from frappe.utils import getdate, nowdate, today, add_years

from iraqi_passport.passport_management.services.base_service import BaseService

ALLOWED_PHOTO_EXT = {".jpg", ".jpeg", ".png"}
MAX_PHOTO_SIZE_MB = 2
ACTIVE_STATES = (
    "Draft",
    "Officer Review",
    "Manager Review",
    "Escalated",
    "Returned for Correction",
)
VERIFICATION_FIELDS = (
    "full_name_ar",
    "full_name_en",
    "date_of_birth",
    "mother_name_ar",
    "mother_name_en",
    "father_name_ar",
    "father_name_en",
    "national_id",
    "gender",
    "place_of_birth",
    "personal_photo",
    "applicant_signature",
)


class PassportService(BaseService):
    """Service handling passport application validation and generation."""

    def validate_application(self, doc):
        """Run all field-level validations for a Passport Application."""
        self._validate_national_id(doc)
        self._validate_date_of_birth(doc)
        self._validate_photo(doc)
        self._check_duplicate_active_application(doc)
        self._validate_verification_remarks(doc)

        previous = doc.get_doc_before_save() if not doc.is_new() else None
        if previous and previous.workflow_state == "Manager Review" and doc.workflow_state == "Officer Review":
            for row in doc.field_remarks:
                row.is_verified = 0
                row.verified_by = None
                row.verified_on = None

    def _validate_verification_remarks(self, doc):
        if doc.workflow_state != "Manager Review":
            return

        verified_fields = {
            row.field_reference
            for row in doc.field_remarks
            if row.is_verified and (row.remark or "").strip()
        }
        missing_fields = [field for field in VERIFICATION_FIELDS if field not in verified_fields]
        if missing_fields:
            frappe.throw(
                _("Every application field must have a verification remark before manager review: {0}").format(
                    ", ".join(missing_fields)
                )
            )

    def _validate_national_id(self, doc):
        if not doc.national_id:
            return
        nid = str(doc.national_id).strip()
        if not nid.isdigit():
            frappe.throw(_("National ID must contain digits only."))
        if len(nid) not in (12, 14):
            frappe.throw(_("National ID length must be 12 or 14 digits."))
        doc.national_id = nid

    def _validate_date_of_birth(self, doc):
        if not doc.date_of_birth:
            return
        dob = getdate(doc.date_of_birth)
        if dob > getdate(nowdate()):
            frappe.throw(_("Date of Birth cannot be in the future."))
        age = (getdate(nowdate()) - dob).days / 365.25
        if age < 0 or age > 120:
            frappe.throw(_("Age is not plausible. Please verify the date of birth."))

    def _validate_photo(self, doc):
        if not doc.personal_photo:
            return
        try:
            file_doc = frappe.get_doc("File", {"file_url": doc.personal_photo})
        except frappe.DoesNotExistError:
            frappe.throw(_("The uploaded personal photo could not be found."))
        if not file_doc:
            return
        ext = os.path.splitext(file_doc.file_name or "")[1].lower()
        if ext not in ALLOWED_PHOTO_EXT:
            frappe.throw(_("Photo must be in JPG or PNG format."))
        if file_doc.file_size and file_doc.file_size > MAX_PHOTO_SIZE_MB * 1024 * 1024:
            frappe.throw(_("Photo size must not exceed {0} MB.").format(MAX_PHOTO_SIZE_MB))

    def _check_duplicate_active_application(self, doc):
        if not doc.national_id:
            return
        existing = frappe.db.exists(
            "Passport Application",
            {
                "national_id": doc.national_id,
                "workflow_state": ["in", ACTIVE_STATES],
                "name": ["!=", doc.name],
            },
        )
        if existing:
            frappe.throw(
                _("An active application already exists for this National ID: {0}").format(existing)
            )

    def generate_passport(self, app_doc):
        """Create a Passport record and back-link it to the application."""
        existing_name = frappe.db.get_value(
            "Passport", {"source_application": app_doc.name}, "name"
        )
        if existing_name:
            passport = frappe.get_doc("Passport", existing_name)
            if passport.status != "Approved":
                passport.status = "Approved"
                passport.issue_date = passport.issue_date or getdate(today())
                passport.expiry_date = passport.expiry_date or add_years(passport.issue_date, 10)
                passport.save(ignore_permissions=True)
            frappe.db.set_value(
                "Passport Application", app_doc.name, "generated_passport", passport.name
            )
            app_doc.generated_passport = passport.name
            return passport

        issue_date = getdate(today())
        expiry_date = add_years(issue_date, 10)

        passport = frappe.get_doc({
            "doctype": "Passport",
            "passport_number": self._generate_passport_number(),
            "status": "Approved",
            "issue_date": issue_date,
            "expiry_date": expiry_date,
            "source_application": app_doc.name,
            "full_name_ar": app_doc.full_name_ar,
            "full_name_en": app_doc.full_name_en,
            "date_of_birth": app_doc.date_of_birth,
            "gender": app_doc.gender,
            "mother_name_ar": app_doc.mother_name_ar,
            "mother_name_en": app_doc.mother_name_en,
            "national_id": app_doc.national_id,
            "place_of_birth": app_doc.place_of_birth,
            "personal_photo": app_doc.personal_photo,
            "issuing_authority": "Republic of Iraq - Ministry of Interior",
        })
        try:
            passport.insert(ignore_permissions=True)
        except frappe.DuplicateEntryError:
            existing_name = frappe.db.get_value(
                "Passport", {"source_application": app_doc.name}, "name"
            )
            if existing_name:
                return frappe.get_doc("Passport", existing_name)
            raise

        frappe.db.set_value(
            "Passport Application", app_doc.name, "generated_passport", passport.name
        )
        app_doc.generated_passport = passport.name

        self.log_activity(
            "Passport Application", app_doc.name,
            "Passport generated",
            {"passport_number": passport.passport_number},
        )
        return passport

    def validate_locked_remarks(self, doc):
        if doc.is_new():
            return
        previous = frappe.get_doc(doc.doctype, doc.name)
        previous_by_name = {row.name: row for row in previous.field_remarks}
        current_names = {row.name for row in doc.field_remarks}
        deleted_locked = [
            row.name
            for row in previous.field_remarks
            if row.is_locked and row.name not in current_names
        ]
        if deleted_locked:
            frappe.throw(_("Locked verification remarks cannot be deleted."))

        for row in doc.field_remarks:
            old_row = previous_by_name.get(row.name)
            if old_row and old_row.is_locked:
                protected = ("field_reference", "is_verified", "remark", "verified_by", "verified_on")
                if any(getattr(row, field) != getattr(old_row, field) for field in protected):
                    frappe.throw(_("Locked verification remarks cannot be changed."))

    def _generate_passport_number(self):
        for _ in range(20):
            number = "A" + str(random.randint(10000000, 99999999))
            if not frappe.db.exists("Passport", {"passport_number": number}):
                return number
        frappe.throw(_("Could not generate a unique passport number. Please retry."))

    def notify_applicant(self, app_doc):
        if isinstance(app_doc, str):
            app_doc = frappe.get_doc("Passport Application", app_doc)
        subject = _("Your passport has been issued — {0}").format(app_doc.name)
        message = _(
            "Your application {0} has been approved. Passport number: {1}.<br>"
            "View passport record: <a href='/app/passport/{1}'>{1}</a>"
        ).format(app_doc.name, app_doc.generated_passport)

        recipients = set()
        if app_doc.owner:
            owner_email = frappe.db.get_value("User", app_doc.owner, "email")
            if owner_email:
                recipients.add(owner_email)
        if getattr(app_doc, "email_id", None):
            recipients.add(app_doc.email_id)

        if recipients and not frappe.conf.get("disable_email_alerts"):
            frappe.sendmail(
                recipients=list(recipients),
                subject=subject,
                message=message,
                reference_doctype="Passport Application",
                reference_name=app_doc.name,
            )

        frappe.publish_realtime(
            event="passport_issued",
            message={"application": app_doc.name, "passport": app_doc.generated_passport},
            user=app_doc.owner,
        )

    def lock_existing_remarks(self, doc):
        for row in doc.field_remarks:
            frappe.db.set_value(
                "Field Verification Remark", row.name, "is_locked", 1
            )

    def add_return_comment(self, doc):
        self.log_activity(
            "Passport Application", doc.name,
            "Application returned for correction",
            {"by": frappe.session.user},
        )


def notify_applicant(app_doc):
    """Background-job entry point for applicant notifications."""
    PassportService().notify_applicant(app_doc)
