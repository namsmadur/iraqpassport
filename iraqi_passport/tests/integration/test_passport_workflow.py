# -*- coding: utf-8 -*-
# Integration tests for Passport Application workflow.
#
# Each test uses a unique national_id to avoid cross-test contamination.
# `flags.ignore_mandatory = True` skips the mandatory personal_photo field.
# Workflow transitions are bypassed in tests via direct DB updates and
# equivalent service calls, since Frappe's workflow validation blocks direct
# state assignment in an automated test flow.

import unittest

import frappe
from frappe.tests import IntegrationTestCase
from frappe.model.workflow import apply_workflow

from iraqi_passport.passport_management.doctype.passport_application.passport_application import (
    on_application_update,
)
from iraqi_passport.passport_management.permissions.passport_application_permission import (
    has_permission,
    has_passport_permission,
    passport_query_conditions,
)
from iraqi_passport.passport_management.services.passport_service import (
    VERIFICATION_FIELDS,
    PassportService,
)


class TestPassportWorkflowIntegration(IntegrationTestCase):
    """Integration tests covering the full passport issuance workflow."""

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _cleanup_by_national_id(self, national_id):
        """Delete any existing applications/passports for a national_id."""
        apps = frappe.get_all(
            "Passport Application",
            filters={"national_id": national_id},
            pluck="name",
        )
        for app_name in apps:
            passports = frappe.get_all(
                "Passport",
                filters={"source_application": app_name},
                pluck="name",
            )
            for p in passports:
                frappe.delete_doc("Passport", p, force=True, ignore_permissions=True)
            frappe.delete_doc(
                "Passport Application", app_name, force=True, ignore_permissions=True
            )
        frappe.db.commit()

    def _create_draft_application(self, national_id="123456789012", **overrides):
        """Create a valid draft application with a unique national_id."""
        self._cleanup_by_national_id(national_id)
        data = {
            "doctype": "Passport Application",
            "full_name_ar": "محمد علي حسين",
            "full_name_en": "Mohammed Ali Hussein",
            "date_of_birth": "1990-05-15",
            "gender": "Male",
            "mother_name_ar": "فاطمة أحمد",
            "mother_name_en": "Fatima Ahmed",
            "national_id": national_id,
            "place_of_birth": "بغداد",
        }
        data.update(overrides)
        doc = frappe.get_doc(data)
        doc.owner = frappe.session.user
        doc.flags.ignore_mandatory = True
        doc = doc.insert(ignore_permissions=True)
        if doc.owner != frappe.session.user:
            frappe.db.set_value(doc.doctype, doc.name, "owner", frappe.session.user)
            doc.reload()
        return doc

    def _ensure_user(self, email, role):
        if not frappe.db.exists("User", email):
            user = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": role,
                "enabled": 1,
                "send_welcome_email": 0,
            })
            user.insert(ignore_permissions=True)
        user = frappe.get_doc("User", email)
        if role not in frappe.get_roles(email):
            user.add_roles(role)
        return email

    def _set_workflow_state(self, app, state):
        """Set a workflow state directly without triggering workflow validation."""
        frappe.db.set_value("Passport Application", app.name, "workflow_state", state)
        frappe.db.commit()
        return frappe.get_doc("Passport Application", app.name)

    def _simulate_approval(self, app):
        """Simulate approval side effects without traversing every workflow state."""
        app = self._set_workflow_state(app, "Approved")
        passport = PassportService().generate_passport(app)
        app = frappe.get_doc("Passport Application", app.name)
        return app, passport

    def _simulate_return_for_correction(self, app):
        """Simulate return-for-correction side effects without workflow validation."""
        app = self._set_workflow_state(app, "Returned for Correction")
        service = PassportService()
        service.lock_existing_remarks(app)
        service.add_return_comment(app)
        return frappe.get_doc("Passport Application", app.name)

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_create_draft_application(self):
        """Creating a valid application should succeed with Draft state."""
        app = self._create_draft_application(national_id="100000000001")
        self.assertTrue(app.name.startswith("PA-"))
        self.assertEqual(app.workflow_state, "Draft")

    def test_national_id_must_be_numeric(self):
        """Non-numeric national_id should be rejected."""
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc({
                "doctype": "Passport Application",
                "full_name_ar": "اختبار",
                "full_name_en": "Test",
                "date_of_birth": "1990-01-01",
                "gender": "Male",
                "mother_name_ar": "اختبار",
                "mother_name_en": "Test",
                "national_id": "ABC123",
            })
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)

    def test_national_id_length_validation(self):
        """national_id with wrong length should be rejected."""
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc({
                "doctype": "Passport Application",
                "full_name_ar": "اختبار",
                "full_name_en": "Test",
                "date_of_birth": "1990-01-01",
                "gender": "Male",
                "mother_name_ar": "اختبار",
                "mother_name_en": "Test",
                "national_id": "12345",
            })
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)

    def test_national_id_is_normalized(self):
        """National IDs are stored without surrounding whitespace."""
        app = self._create_draft_application(national_id=" 100000000009 ")
        self.assertEqual(app.national_id, "100000000009")

    def test_passport_generation_on_approval(self):
        """Approving an application should auto-generate a Passport."""
        app = self._create_draft_application(national_id="100000000002")
        app, passport = self._simulate_approval(app)

        self.assertTrue(app.generated_passport)
        self.assertTrue(passport.passport_number.startswith("A"))
        self.assertEqual(passport.status, "Approved")
        self.assertEqual(passport.source_application, app.name)
        self.assertEqual(passport.full_name_ar, "محمد علي حسين")

    def test_passport_draft_can_be_created_and_approved(self):
        """A clerk can create a draft passport for an approved application."""
        app = self._create_draft_application(national_id="100000000013")
        app = self._set_workflow_state(app, "Approved")
        clerk = self._ensure_user("passport-draft-clerk@example.com", "Data Entry Clerk")
        manager = self._ensure_user("passport-draft-manager@example.com", "Manager")

        frappe.set_user(clerk)
        passport = frappe.get_doc({
            "doctype": "Passport",
            "passport_number": "DRAFT-100000000013",
            "source_application": app.name,
            "full_name_ar": app.full_name_ar,
            "full_name_en": app.full_name_en,
            "date_of_birth": app.date_of_birth,
            "gender": app.gender,
            "mother_name_ar": app.mother_name_ar,
            "mother_name_en": app.mother_name_en,
            "national_id": app.national_id,
            "status": "Draft",
        }).insert()
        self.assertEqual(passport.status, "Draft")

        frappe.set_user(manager)
        passport.reload()
        passport.status = "Approved"
        passport.save()
        self.assertEqual(passport.status, "Approved")
        self.assertTrue(passport.issue_date)
        self.assertTrue(passport.expiry_date)

    def test_passport_generation_is_idempotent(self):
        """Repeated approval handling must not issue a second passport."""
        app = self._create_draft_application(national_id="100000000007")
        app = self._set_workflow_state(app, "Approved")

        first = PassportService().generate_passport(app)
        second = PassportService().generate_passport(app)

        self.assertEqual(first.name, second.name)
        self.assertEqual(frappe.db.count("Passport", {"source_application": app.name}), 1)

    def test_approving_application_promotes_existing_passport_draft(self):
        """Application approval promotes its linked draft passport."""
        app = self._create_draft_application(national_id="100000000014")
        app = self._set_workflow_state(app, "Approved")
        passport = frappe.get_doc({
            "doctype": "Passport",
            "passport_number": "DRAFT-100000000014",
            "source_application": app.name,
            "full_name_ar": app.full_name_ar,
            "full_name_en": app.full_name_en,
            "date_of_birth": app.date_of_birth,
            "gender": app.gender,
            "mother_name_ar": app.mother_name_ar,
            "mother_name_en": app.mother_name_en,
            "national_id": app.national_id,
            "status": "Draft",
        }).insert(ignore_permissions=True)

        passport = PassportService().generate_passport(app)

        self.assertEqual(passport.status, "Approved")
        self.assertTrue(frappe.db.get_value("Passport Application", app.name, "generated_passport"))

    def test_approval_hook_generates_passport_once(self):
        """The document event should generate one passport on approval."""
        app = self._create_draft_application(national_id="100000000008")
        app = self._set_workflow_state(app, "Approved")

        on_application_update(app)
        on_application_update(frappe.get_doc("Passport Application", app.name))

        self.assertEqual(frappe.db.count("Passport", {"source_application": app.name}), 1)

    def test_approval_hook_queues_notification(self):
        """Approval should queue notification delivery after commit."""
        app = self._create_draft_application(national_id="100000000012")
        app = self._set_workflow_state(app, "Approved")

        with unittest.mock.patch("frappe.enqueue") as enqueue:
            on_application_update(app)

        enqueue.assert_called_once()
        self.assertEqual(enqueue.call_args.kwargs["app_doc"], app.name)

    def test_real_workflow_transitions_enforce_roles(self):
        """The normal approval path requires the configured role sequence."""
        clerk = self._ensure_user("passport-clerk@example.com", "Data Entry Clerk")
        officer = self._ensure_user("passport-officer@example.com", "Verification Officer")
        manager = self._ensure_user("passport-manager@example.com", "Manager")

        frappe.set_user(clerk)
        app = self._create_draft_application(national_id="100000000011")
        frappe.db.set_value("Passport Application", app.name, "owner", clerk)
        frappe.db.commit()
        app = frappe.get_doc("Passport Application", app.name)
        app.flags.ignore_mandatory = True
        self.assertTrue(app.has_permission("read"))
        app = apply_workflow(app, "Send for Review")
        self.assertEqual(app.workflow_state, "Officer Review")

        frappe.set_user(officer)
        app = frappe.get_doc("Passport Application", app.name)
        app.flags.ignore_mandatory = True
        app.flags.ignore_permissions = True
        for field in VERIFICATION_FIELDS:
            app.append("field_remarks", {
                "field_reference": field,
                "is_verified": 1,
                "remark": f"Verified {field}",
            })
        app.save()
        self.assertEqual(
            {row.field_reference for row in app.field_remarks if row.is_verified and row.remark},
            set(VERIFICATION_FIELDS),
        )
        app.flags.ignore_permissions = True
        app = apply_workflow(app, "Verify and Approve")
        self.assertEqual(app.workflow_state, "Manager Review")

        frappe.set_user(manager)
        app = frappe.get_doc("Passport Application", app.name)
        app.flags.ignore_mandatory = True
        app.flags.ignore_permissions = True
        app = apply_workflow(app, "Send Back to Officer")
        self.assertEqual(app.workflow_state, "Officer Review")
        self.assertFalse(any(row.is_verified for row in app.field_remarks))

        frappe.set_user(officer)
        app = frappe.get_doc("Passport Application", app.name)
        for row in app.field_remarks:
            row.is_verified = 1
        app.flags.ignore_mandatory = True
        app.flags.ignore_permissions = True
        app.save()
        app = apply_workflow(app, "Verify and Approve")

        frappe.set_user(manager)
        app = frappe.get_doc("Passport Application", app.name)
        app.flags.ignore_mandatory = True
        app.flags.ignore_permissions = True
        app = apply_workflow(app, "Approve")
        self.assertEqual(app.workflow_state, "Approved")

    def test_manager_review_requires_all_fields_verified_with_remarks(self):
        """Every applicant field needs a verified remark before manager review."""
        app = self._create_draft_application(national_id="100000000015")
        app.workflow_state = "Manager Review"
        app.append("field_remarks", {
            "field_reference": "full_name_ar",
            "is_verified": 1,
            "remark": "Name checked",
        })

        with self.assertRaises(frappe.ValidationError):
            PassportService().validate_application(app)

    def test_expiry_date_is_10_years_after_issue(self):
        """Expiry date must be exactly 10 years after issue date."""
        app = self._create_draft_application(national_id="100000000003")
        app, passport = self._simulate_approval(app)

        self.assertEqual(passport.expiry_date.year - passport.issue_date.year, 10)

    def test_duplicate_active_application_rejected(self):
        """A second active application for the same national_id should fail."""
        self._create_draft_application(national_id="100000000004")

        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc({
                "doctype": "Passport Application",
                "full_name_ar": "شخص آخر",
                "full_name_en": "Another Person",
                "date_of_birth": "1995-03-20",
                "gender": "Female",
                "mother_name_ar": "اسم",
                "mother_name_en": "Name",
                "national_id": "100000000004",
            })
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)

    def test_inactive_application_allows_new_application(self):
        """An inactive application should not block a new application."""
        national_id = "100000000006"
        app = self._create_draft_application(national_id=national_id)
        self._set_workflow_state(app, "Rejected")

        new_app = frappe.get_doc({
            "doctype": "Passport Application",
            "full_name_ar": "شخص آخر",
            "full_name_en": "Another Person",
            "date_of_birth": "1995-03-20",
            "gender": "Female",
            "mother_name_ar": "اسم",
            "mother_name_en": "Name",
            "national_id": national_id,
        })
        new_app.flags.ignore_mandatory = True

        self.assertTrue(new_app.insert(ignore_permissions=True).name)

    def test_return_for_correction_locks_remarks(self):
        """Returning for correction should lock existing remarks."""
        app = self._create_draft_application(national_id="100000000005")
        app.append("field_remarks", {
            "field_reference": "full_name_ar",
            "is_verified": 1,
            "remark": "Verified",
        })
        app.flags.ignore_mandatory = True
        app.save(ignore_permissions=True)

        app = self._simulate_return_for_correction(app)

        row_name = app.field_remarks[0].name
        self.assertTrue(
            frappe.db.get_value("Field Verification Remark", row_name, "is_locked")
        )

        app = frappe.get_doc("Passport Application", app.name)
        app.field_remarks = []
        with self.assertRaises(frappe.ValidationError):
            app.save(ignore_permissions=True)

        app = frappe.get_doc("Passport Application", app.name)
        app.field_remarks[0].remark = "Changed after lock"
        with self.assertRaises(frappe.ValidationError):
            app.save(ignore_permissions=True)

    def test_permission_hook_handles_missing_document(self):
        """Permission checks without a document must not raise an exception."""
        self.assertTrue(has_permission(None, "read", "Administrator"))

    def test_permission_hook_defers_to_doctype_role_permissions(self):
        """Unrestricted records should use the configured DocType role permissions."""
        user = self._ensure_user("passport-manager@example.com", "Manager")
        app = self._create_draft_application(national_id="100000000011")

        self.assertTrue(
            frappe.has_permission(
                app.doctype, ptype="write", doc=app, user=user
            )
        )

    def test_permission_hook_denies_final_state_edits(self):
        """Non-system users cannot modify approved applications."""
        app = self._create_draft_application(national_id="100000000010")
        app = self._set_workflow_state(app, "Approved")

        self.assertFalse(has_permission(app, "write", "Data Entry Clerk"))

    def test_passport_permissions_allow_draft_creation_and_approval(self):
        """Clerks may create drafts and managers may approve without deleting."""
        clerk = self._ensure_user("passport-permission-clerk@example.com", "Data Entry Clerk")
        manager = self._ensure_user("passport-permission-manager@example.com", "Manager")

        self.assertTrue(has_passport_permission(None, "read", manager))
        self.assertTrue(has_passport_permission(None, "create", clerk))
        self.assertTrue(has_passport_permission(None, "write", manager))
        self.assertFalse(has_passport_permission(None, "delete", manager))
        self.assertIn("source_application", passport_query_conditions("passport-clerk@example.com"))
