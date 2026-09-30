"""Move in-progress applications to the new Director General decision queue."""

import frappe


def execute():
	if not frappe.db.has_column("Passport Application", "workflow_state"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabPassport Application`
		SET workflow_state = %s
		WHERE workflow_state IN (%s, %s)
		""",
		("Director Review", "Manager Review", "Escalated"),
	)
