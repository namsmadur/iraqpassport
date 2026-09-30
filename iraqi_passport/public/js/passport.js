frappe.ui.form.on("Passport", {
	refresh(frm) {
		const can_issue = (frappe.user_roles || []).some((role) =>
			["System Manager", "Director"].includes(role)
		);
		if (frm.doc.status === "Approved" && !frm.is_new() && can_issue) {
			frm.add_custom_button(
				__("Download Passport PDF"),
				() => {
					const params = new URLSearchParams({ name: frm.doc.name });
					window.open(
						frappe.urllib.get_full_url(
							`/api/method/iraqi_passport.passport_management.doctype.passport.passport.download_passport_pdf?${params}`
						),
						"_blank"
					);
				},
				__("Print")
			);
		}
	},
});
