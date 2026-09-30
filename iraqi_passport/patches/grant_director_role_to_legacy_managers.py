"""Grant Director permissions to accounts using the legacy Manager role."""

import frappe


def execute():
	if not frappe.db.exists("Role", "Director"):
		frappe.get_doc(
			{"doctype": "Role", "role_name": "Director", "desk_access": 1}
		).insert(ignore_permissions=True)

	manager_users = frappe.get_all(
		"Has Role",
		filters={"role": "Manager", "parenttype": "User"},
		pluck="parent",
	)

	for user in manager_users:
		if not frappe.db.exists(
			"Has Role", {"parent": user, "parenttype": "User", "role": "Director"}
		):
			frappe.get_doc("User", user).add_roles("Director")
