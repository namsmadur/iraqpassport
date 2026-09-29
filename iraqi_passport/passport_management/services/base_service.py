# -*- coding: utf-8 -*-
# Base service class providing common functionality for all services.

import frappe
from frappe import _


class BaseService:
    """Base class for all service layer classes.

    Services contain business rules and coordinate Frappe documents. Database
    access is currently performed through Frappe APIs; repository classes can
    be introduced when persistence needs to be shared or independently tested.
    """

    def __init__(self, user=None):
        self.user = user or frappe.session.user

    def check_permission(self, doctype, ptype="read", doc=None, throw=True):
        """Check if current user has permission on a DocType or document."""
        return frappe.has_permission(
            doctype=doctype,
            ptype=ptype,
            doc=doc,
            user=self.user,
            throw=throw,
        )

    def validate_mandatory(self, data, fields):
        """Validate that mandatory fields are present in the data dict."""
        missing = [f for f in fields if not data.get(f)]
        if missing:
            frappe.throw(
                _("Missing required fields: {0}").format(", ".join(missing))
            )

    def log_activity(self, doctype, docname, action, details=None):
        """Log service activity for audit trail via Comment."""
        content = f"{action}: {details}" if details else action
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": doctype,
            "reference_name": docname,
            "content": content,
        }).insert(ignore_permissions=True)
