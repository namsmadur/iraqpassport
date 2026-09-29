# -*- coding: utf-8 -*-
# Controller for Passport. Provides a non-official MRZ preview helper.

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_years, getdate, today


class Passport(Document):
    """Passport document controller."""

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
            "place_of_birth", "personal_photo",
        )
        changed_fields = [
            field for field in protected_fields
            if self.get(field) != previous.get(field)
        ]
        if status_changed:
            changed_fields = [
                field for field in changed_fields if field not in ("issue_date", "expiry_date")
            ]
        if "System Manager" not in roles and changed_fields:
            frappe.throw(_("Passport details cannot be changed after creation."))

    def _validate_approval(self, roles):
        if "System Manager" not in roles and not ({"Manager", "Director"} & set(roles)):
            frappe.throw(_("Only a Manager or Director can approve a passport."))
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
