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
    """Remove the preview warning and set the passport heading after fixture sync."""
    import frappe
    import re

    name = "Iraqi Passport Format"
    html = frappe.db.get_value("Print Format", name, "html")
    old_marker = '<div class="mrz-preview-label">PREVIEW ONLY - NOT ICAO 9303</div>'
    if html and '<header class="passport-header">' in html:
        updated_html = html.replace(old_marker, "")
        updated_html = re.sub(
            r'<div\b[^>]*class="[^"]*\bmrz-preview-label\b[^"]*"[^>]*>.*?</div>',
            "",
            updated_html,
            flags=re.DOTALL,
        )
        updated_html = re.sub(
            r'<footer\b[^>]*>[^<]*(?:SAMPLE|NOT A GOVERNMENT DOCUMENT|NOT VALID FOR TRAVEL|نموذج تجريبي غير رسمي)[^<]*</footer>',
            "",
            updated_html,
            flags=re.IGNORECASE,
        )
        updated_html = re.sub(
            r'<div class="emblem">.*?</div>',
            '<div class="emblem">جمهورية العراق<br>'
            '<span>باداره المهندس الكبير نامسمدر</span></div>',
            updated_html,
            count=1,
            flags=re.DOTALL,
        )
        if updated_html != html:
            frappe.db.set_value("Print Format", name, "html", updated_html)

# ---------------------------------------------------------------------------
# Document Events
# Controller functions are thin orchestrators that delegate to services.
# ---------------------------------------------------------------------------
doc_events = {
    "Passport Application": {
        "on_update": "iraqi_passport.passport_management.doctype.passport_application.passport_application.on_application_update",
    }
}

doctype_js = {
    "Passport": "public/js/passport.js",
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
        "Draft", "Officer Review", "Director Review",
        "Approved", "Rejected", "Returned for Correction"
    ]]]},
    {"dt": "Workflow Action Master", "filters": [["name", "in", [
        "Send for Review", "Verify and Send to Director", "Return for Correction",
        "Issue Passport", "Reject",
        "Reset to Draft"
    ]]]},
    {"dt": "Role", "filters": [["name", "in", [
        "Data Entry Clerk", "Verification Officer", "Manager", "Director"
    ]]]},
    {"dt": "Notification", "filters": [["document_type", "=", "Passport Application"]]},
    {"dt": "Print Format", "filters": [["name", "=", "Iraqi Passport Format"]]},
]
