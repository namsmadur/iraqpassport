# -*- coding: utf-8 -*-
# Child table controller.

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class FieldVerificationRemark(Document):
    def validate(self):
        if self.is_verified and not self.verified_by:
            self.verified_by = frappe.session.user
            self.verified_on = now_datetime()
