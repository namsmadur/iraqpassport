# -*- coding: utf-8 -*-
# hooks.py — Application hooks and event bindings for iraqi_passport

app_name = "iraqi_passport"
app_title = "Iraqi Passport Management"
app_publisher = "Ministry of Interior"
app_description = "Iraqi Passport Issuance Lifecycle Management"
app_email = "info@example.iq"
app_license = "mit"

after_migrate = ["iraqi_passport.hooks.mark_print_format_preview"]


def mark_print_format_preview():
    """Mark the illustrative MRZ block as non-official after fixture sync."""
    import frappe

    name = "Iraqi Passport Format"
    marker = (
        '<div class="mrz-preview-label" style="border:2px solid #b42318;color:#b42318;'
        'font-weight:bold;text-align:center;padding:8px;margin-bottom:8mm">'
        'SAMPLE - NOT A GOVERNMENT DOCUMENT - NOT VALID FOR TRAVEL<br>'
        'نموذج غير رسمي - غير صالح للسفر</div>'
    )
    html = frappe.db.get_value("Print Format", name, "html")
    old_marker = '<div class="mrz-preview-label">PREVIEW ONLY - NOT ICAO 9303</div>'
    if html and '<header class="passport-header">' in html:
        html = html.replace(old_marker, "")
        if marker not in html:
            html = html.replace('<header class="passport-header">', marker + '<header class="passport-header">', 1)
        frappe.db.set_value("Print Format", name, "html", html)

# ---------------------------------------------------------------------------
# Document Events
# Controller functions are thin orchestrators that delegate to services.
# ---------------------------------------------------------------------------
doc_events = {
    "Passport Application": {
        "on_update": "iraqi_passport.passport_management.doctype.passport_application.passport_application.on_application_update",
    }
}

# ---------------------------------------------------------------------------
# Permission Hooks
# has_permission can ONLY deny (return False). Returning None continues standard checks.
# ---------------------------------------------------------------------------
has_permission = {
    "Passport Application": "iraqi_passport.passport_management.permissions.passport_application_permission.has_permission",
    "Passport": "iraqi_passport.passport_management.permissions.passport_application_permission.has_passport_permission",
}

permission_query_conditions = {
    "Passport Application": "iraqi_passport.passport_management.permissions.passport_application_permission.permission_query_conditions",
    "Passport": "iraqi_passport.passport_management.permissions.passport_application_permission.passport_query_conditions",
}

# ---------------------------------------------------------------------------
# Fixtures — exported for version control and re-import on any site.
# ---------------------------------------------------------------------------
fixtures = [
    {"dt": "Workflow", "filters": [["name", "=", "Passport Approval Workflow"]]},
    {"dt": "Workflow State", "filters": [["name", "in", [
        "Draft", "Officer Review", "Manager Review",
        "Escalated", "Approved", "Rejected", "Returned for Correction"
    ]]]},
    {"dt": "Workflow Action Master", "filters": [["name", "in", [
        "Send for Review", "Verify and Approve", "Return for Correction",
        "Send Back to Officer",
        "Approve", "Reject", "Escalate", "Final Approve", "Final Reject",
        "Reset to Draft"
    ]]]},
    {"dt": "Role", "filters": [["name", "in", [
        "Data Entry Clerk", "Verification Officer", "Manager", "Director"
    ]]]},
    {"dt": "Notification", "filters": [["document_type", "=", "Passport Application"]]},
    {"dt": "Print Format", "filters": [["name", "=", "Iraqi Passport Format"]]},
]
