# -*- coding: utf-8 -*-
# Controller for Passport. Provides a non-official MRZ preview helper.

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_years, getdate, today


class Passport(Document):
    """Passport document controller."""

    OFFICER_EDITABLE_FIELDS = {
        "full_name_ar", "full_name_en", "date_of_birth", "gender",
        "mother_name_ar", "mother_name_en", "national_id", "place_of_birth",
        "personal_photo", "applicant_signature",
    }

    def validate(self):
        if not self.status:
            self.status = "Draft"

        roles = frappe.get_roles()
        if self.is_new():
            if self.status == "Approved":
                self._validate_approval(roles)
            return

        previous = self.get_doc_before_save()
        if not previous:
            return

        status_changed = self.status != previous.status
        if status_changed:
            if previous.status != "Draft" or self.status != "Approved":
                frappe.throw(_("A passport can only move from Draft to Approved."))
            self.issue_date = getdate(today())
            self.expiry_date = add_years(self.issue_date, 10)
            self._validate_approval(roles)

        protected_fields = (
            "passport_number", "issue_date", "expiry_date", "issuing_authority",
            "source_application", "full_name_ar", "full_name_en", "date_of_birth",
            "gender", "mother_name_ar", "mother_name_en", "national_id",
            "place_of_birth", "personal_photo", "applicant_signature",
        )
        changed_fields = [
            field for field in protected_fields
            if self.get(field) != previous.get(field)
        ]
        if status_changed:
            changed_fields = [
                field for field in changed_fields if field not in ("issue_date", "expiry_date")
            ]
        officer_edit = (
            "Verification Officer" in roles
            and previous.status == "Draft"
            and self.status == "Draft"
            and self.source_application == previous.source_application
            and frappe.db.get_value(
                "Passport Application", self.source_application, "workflow_state"
            ) == "Officer Review"
        )
        if officer_edit:
            disallowed = set(changed_fields) - self.OFFICER_EDITABLE_FIELDS
            if disallowed:
                frappe.throw(_("Only holder details can be edited during officer review."))
        elif "System Manager" not in roles and changed_fields:
            frappe.throw(_("Passport details cannot be changed after creation."))

    def _validate_approval(self, roles):
        if "System Manager" not in roles and "Director" not in roles:
            frappe.throw(_("Only the Director General can approve a passport."))
        if not self.issue_date or not self.expiry_date:
            frappe.throw(_("Issue date and expiry date are required for an approved passport."))
        if getdate(self.expiry_date) <= getdate(self.issue_date):
            frappe.throw(_("Expiry date must be after the issue date."))
        if self.source_application:
            state = frappe.db.get_value(
                "Passport Application", self.source_application, "workflow_state"
            )
            if state != "Approved":
                frappe.throw(_("The linked application must be approved before the passport."))
        elif "System Manager" not in roles:
            frappe.throw(_("An approved application must be linked before approving the passport."))


def get_mrz_lines(doc):
    """
    Build a two-line MRZ-like preview string.
    This output is not an official ICAO 9303 document field.
    """
    def pad(value, length, filler="<"):
        value = (value or "").upper()
        value = "".join(c if c.isalnum() else "<" for c in value)
        return (value + filler * length)[:length]

    line1 = "P<IRQ" + pad(doc.full_name_en, 39)
    line2 = (
        pad(doc.passport_number, 9)
        + "IRQ"
        + pad(getdate(doc.date_of_birth).strftime("%y%m%d"), 6)
        + pad(doc.gender[0] if doc.gender else "X", 1)
        + pad(getdate(doc.expiry_date).strftime("%y%m%d"), 6)
        + pad(doc.national_id, 14)
    )
    return f"{line1}\n{line2}"


@frappe.whitelist()
def download_passport_pdf(name):
    """Render an approved passport with the installed WeasyPrint backend."""
    passport = frappe.get_doc("Passport", name)
    passport.check_permission("print")
    if passport.status != "Approved":
        frappe.throw(_("Only approved passports can be downloaded as PDF."))

    html = frappe.get_print(
        "Passport",
        passport.name,
        print_format="Iraqi Passport Format",
        doc=passport,
        as_pdf=False,
        no_letterhead=1,
    )
    try:
        from weasyprint import HTML
        from frappe.utils.pdf import inline_private_images

        html = inline_private_images(html)
        pdf = HTML(string=html, base_url=frappe.utils.get_url()).write_pdf()
    except (ImportError, OSError) as exc:
        frappe.throw(_("The PDF renderer is unavailable: {0}").format(str(exc)))

    frappe.local.response.filename = f"{passport.name}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "pdf"
