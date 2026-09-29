// Client-side logic for Passport Application form.

frappe.ui.form.on("Passport Application", {
    refresh(frm) {
        if (["Approved", "Rejected"].includes(frm.doc.workflow_state)) {
            frm.set_read_only();
            frm.disable_save();
        }

        const can_edit = frm.doc.workflow_state === "Officer Review";
        ["field_reference", "is_verified", "remark"].forEach((field) => {
            frm.fields_dict.field_remarks.grid.update_docfield_property(
                field, "read_only", can_edit ? 0 : 1
            );
        });
    },

    national_id(frm) {
        if (frm.doc.national_id && !/^\d+$/.test(frm.doc.national_id)) {
            frappe.msgprint(__("National ID must contain digits only."));
        }
    },
});

frappe.ui.form.on("Field Verification Remark", {
    is_verified(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.is_verified) {
            frappe.model.set_value(cdt, cdn, "verified_by", frappe.session.user);
            frappe.model.set_value(cdt, cdn, "verified_on", frappe.datetime.now_datetime());
        }
    },
});
