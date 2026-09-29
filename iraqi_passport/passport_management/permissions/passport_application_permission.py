# -*- coding: utf-8 -*-
# This file controls who can view, edit, and list Passport Application records.
# It implements custom permission logic for different workflow states and user roles.

import frappe


def has_permission(doc, ptype, user):
    """Check whether a user is allowed to access a Passport Application document.

    This function is used by Frappe when a user tries to read, write, create,
    or delete a Passport Application record.

    Rules:
    - Approved or Rejected applications can only be changed by System Manager.
    - A Data Entry Clerk can manage only the applications they created.
    - Users in workflow-related roles can access records matching their review state.
    - All other decisions are left to Frappe's role permission checks.
    """
    roles = frappe.get_roles(user)

    # Prevent non-admin users from modifying applications that are already closed.
    if doc and doc.workflow_state in ("Approved", "Rejected"):
        if ptype in ("write", "create", "delete"):
            if "System Manager" not in roles:
                return False

    # Users in Data Entry Clerk role can only edit or read their own submitted record.
    if (
        doc
        and ptype in ("read", "write")
        and "Data Entry Clerk" in roles
        and doc.owner == user
    ):
        return True

    # Match the workflow state with the required role for review stages.
    state_roles = {
        "Officer Review": "Verification Officer",
        "Manager Review": "Manager",
        "Escalated": "Director",
    }
    if doc and ptype in ("read", "write") and state_roles.get(doc.workflow_state) in roles:
        return True

    # Frappe treats a falsy controller-hook result as an explicit denial.
    return True


def permission_query_conditions(user):
    """Return the SQL filter used when listing Passport Application records.

    This limits the records shown in list views. The Data Entry Clerk only sees
    their own entries, while other users can keep the normal full list visibility.
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    # Restrict Data Entry Clerk to records they created, unless they are a System Manager.
    if "Data Entry Clerk" in roles and "System Manager" not in roles:
        return "`tabPassport Application`.owner = {0}".format(
            frappe.db.escape(user)
        )

    # No custom filter for other roles.
    return ""


def has_passport_permission(doc, ptype, user):
    """Restrict passport creation, approval, and deletion by role."""
    roles = set(frappe.get_roles(user))
    if ptype == "create" and not roles.intersection({"System Manager", "Data Entry Clerk"}):
        return False
    if ptype == "write" and not roles.intersection({"System Manager", "Manager", "Director"}):
        return False
    if ptype == "delete" and "System Manager" not in roles:
        return False

    return True


def passport_query_conditions(user):
    """Return the SQL filter used when listing Passport records.

    This ensures a Data Entry Clerk can only see Passport records associated with
    applications they own, while System Managers keep unrestricted access.
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    # Limit Data Entry Clerk to the Passport records created from their own applications.
    if "Data Entry Clerk" in roles and "System Manager" not in roles:
        return "`tabPassport`.source_application in (select name from `tabPassport Application` where owner = {0})".format(
            frappe.db.escape(user)
        )

    # No custom filter for roles that should see everything.
    return ""
