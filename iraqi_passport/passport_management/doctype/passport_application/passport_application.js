// Client-side logic for Passport Application form.

function download_passport_pdf(passport_name) {
    const params = new URLSearchParams({ name: passport_name });
    window.open(
        frappe.urllib.get_full_url(
            `/api/method/iraqi_passport.passport_management.doctype.passport.passport.download_passport_pdf?${params}`
        ),
        "_blank"
    );
}

frappe.ui.form.on("Passport Application", {
    refresh(frm) {
        const roles = frappe.user_roles || [];
        const can_open_passport = roles.some((role) =>
            ["System Manager", "Verification Officer", "Director", "Manager"].includes(role)
        );
        frm.toggle_display("generated_passport", can_open_passport);
        if (
            frm.doc.workflow_state === "Officer Review"
            && frm.doc.generated_passport
            && roles.includes("Verification Officer")
        ) {
            frm.add_custom_button(__("Open Passport for Editing"), () => {
                frappe.set_route("Form", "Passport", frm.doc.generated_passport);
            }, __("Passport"));
        }

        if (
            frm.doc.workflow_state === "Approved"
            && frm.doc.generated_passport
            && roles.some((role) => ["System Manager", "Director", "Manager"].includes(role))
        ) {
            frm.add_custom_button(__("Download Passport PDF"), () => {
                download_passport_pdf(frm.doc.generated_passport);
            }, __("Passport"));
        }

        if (
            frm.doc.workflow_state === "Director Review"
            && roles.some((role) => ["System Manager", "Director", "Manager"].includes(role))
        ) {
            frm.add_custom_button(__("Issue Passport and Download PDF"), async () => {
                const pdf_window = window.open("about:blank", "_blank");
                try {
                    await frappe.xcall("frappe.model.workflow.apply_workflow", {
                        doc: frm.doc,
                        action: "Issue Passport",
                    });
                    await frm.reload_doc();
                    if (frm.doc.workflow_state !== "Approved" || !frm.doc.generated_passport) {
                        throw new Error(__("The passport was not issued."));
                    }
                    const params = new URLSearchParams({ name: frm.doc.generated_passport });
                    pdf_window.location = frappe.urllib.get_full_url(
                        `/api/method/iraqi_passport.passport_management.doctype.passport.passport.download_passport_pdf?${params}`
                    );
                } catch (error) {
                    if (pdf_window) pdf_window.close();
                    frappe.msgprint(error.message || __("Could not issue and download the passport."));
                }
            }, __("Passport"));
        }

        if (["Approved", "Rejected"].includes(frm.doc.workflow_state)) {
            frm.set_read_only();
            frm.disable_save();
        }

        const can_verify = frm.doc.workflow_state === "Officer Review";
        const can_decide = frm.doc.workflow_state === "Director Review";
        ["field_reference", "field_value"].forEach((field) => {
            frm.fields_dict.field_remarks.grid.update_docfield_property(
                field, "read_only", 1
            );
        });
        ["is_verified", "remark"].forEach((field) => {
            frm.fields_dict.field_remarks.grid.update_docfield_property(
                field, "read_only", can_verify ? 0 : 1
            );
        });
        frm.set_df_property("rejection_reason", "read_only", can_decide ? 0 : 1);
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
