# -*- coding: utf-8 -*-
# Controller for Passport Application.
# Thin orchestrator — all business logic lives in PassportService.

import frappe
from frappe.model.document import Document

from iraqi_passport.passport_management.services.passport_service import PassportService


class PassportApplication(Document):
    """Passport Application document controller."""

    def validate(self):
        PassportService().validate_application(self)

    def before_save(self):
        PassportService().validate_locked_remarks(self)


def on_application_update(doc, method=None):
    """Hook entry point for on_update event."""
    service = PassportService()
    previous = doc.get_doc_before_save()
    entered_officer_review = (
        doc.workflow_state == "Officer Review"
        and (not previous or previous.workflow_state != "Officer Review")
    )
    if entered_officer_review:
        service.create_draft_passport(doc, refresh_existing=True)

    if doc.workflow_state == "Approved":
        existing_status = frappe.db.get_value("Passport", doc.generated_passport, "status") if doc.generated_passport else None
        newly_issued = existing_status != "Approved"
        service.generate_passport(doc)
        if newly_issued:
            frappe.enqueue(
                "iraqi_passport.passport_management.services.passport_service.notify_applicant",
                queue="short",
                enqueue_after_commit=True,
                app_doc=doc.name,
            )

    if doc.workflow_state == "Returned for Correction":
        service.lock_existing_remarks(doc)
        service.add_return_comment(doc)
