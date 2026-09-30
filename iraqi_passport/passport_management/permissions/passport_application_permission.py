# -*- coding: utf-8 -*-
# This file controls who can view, edit, and list Passport Application records.
# It implements custom permission logic for different workflow states and user roles.

import frappe


def has_permission(doc, ptype, user):
    """Restrict application access to the role responsible for each workflow step."""
    roles = set(frappe.get_roles(user))
    if "System Manager" in roles:
        return True

    if ptype == "create":
        return "Data Entry Clerk" in roles
    if ptype == "delete":
        return False
    if not doc:
        return None

    state = doc.workflow_state
    owner = doc.owner == user
    if ptype == "read":
        if "Data Entry Clerk" in roles:
            return owner
        if "Verification Officer" in roles:
            return state == "Officer Review"
        if "Director" in roles:
            return state in ("Director Review", "Approved", "Rejected")
        return "Manager" in roles

    if ptype == "write":
        # File uploads on a new Desk form check write access before the document exists.
        if doc.is_new():
            return "Data Entry Clerk" in roles

        saved = frappe.db.get_value(
            "Passport Application",
            doc.name,
            ["owner", "workflow_state"],
            as_dict=True,
        )
        if not saved:
            return False
        owner = saved.owner == user
        saved_state = saved.workflow_state
        if "Data Entry Clerk" in roles:
            return owner and (
                (saved_state == "Draft" and state in ("Draft", "Officer Review"))
                or (
                    saved_state == "Returned for Correction"
                    and state in ("Returned for Correction", "Draft")
                )
            )
        if "Verification Officer" in roles:
            return state == "Officer Review" or saved_state == "Officer Review"
        if "Director" in roles:
            return state == "Director Review" or saved_state == "Director Review"
        return False

    return None


def permission_query_conditions(user):
    """Return the SQL filter used when listing Passport Application records.

    This limits the records shown in list views. The Data Entry Clerk only sees
    their own entries, while other users can keep the normal full list visibility.
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    if "System Manager" in roles:
        return ""
    if "Director" in roles:
        return "`tabPassport Application`.workflow_state in ('Director Review', 'Approved', 'Rejected')"
    if "Verification Officer" in roles:
        return "`tabPassport Application`.workflow_state = 'Officer Review'"
    if "Data Entry Clerk" in roles:
        return "`tabPassport Application`.owner = {0}".format(
            frappe.db.escape(user)
        )

    # No custom filter for other roles.
    return ""


def has_passport_permission(doc, ptype, user):
    """Allow officers to edit drafts during verification and Directors to issue them."""
    roles = set(frappe.get_roles(user))
    if "System Manager" in roles:
        return True
    if ptype == "create":
        return False
    if ptype == "write":
        if "Director" in roles:
            return False
        if "Verification Officer" in roles and doc:
            application_state = frappe.db.get_value(
                "Passport Application", doc.source_application, "workflow_state"
            ) if doc.source_application else None
            return doc.status == "Draft" and application_state == "Officer Review"
        return False
    if ptype == "print":
        return bool(
            doc
            and doc.status == "Approved"
            and roles.intersection({"Director", "Manager"})
        )
    if ptype == "delete":
        return False
    if ptype == "read":
        if "Data Entry Clerk" in roles:
            return False
        if not doc:
            return None
        if "Verification Officer" in roles and doc:
            state = frappe.db.get_value(
                "Passport Application", doc.source_application, "workflow_state"
            ) if doc.source_application else None
            return doc.status == "Draft" and state == "Officer Review"
        if "Director" in roles and doc:
            state = frappe.db.get_value(
                "Passport Application", doc.source_application, "workflow_state"
            ) if doc.source_application else None
            return doc.status == "Approved" or state == "Director Review"
        return "Manager" in roles
    return None


def passport_query_conditions(user):
    """Return the SQL filter used when listing Passport records.

    This ensures a Data Entry Clerk can only see Passport records associated with
    applications they own, while System Managers keep unrestricted access.
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    if "System Manager" in roles:
        return ""
    if "Data Entry Clerk" in roles:
        return "1=0"
    if "Verification Officer" in roles:
        return "`tabPassport`.status = 'Draft' and `tabPassport`.source_application in (select name from `tabPassport Application` where workflow_state = 'Officer Review')"
    if "Director" in roles:
        return "(`tabPassport`.status = 'Approved' or `tabPassport`.source_application in (select name from `tabPassport Application` where workflow_state = 'Director Review'))"

    # No custom filter for roles that should see everything.
    return ""
