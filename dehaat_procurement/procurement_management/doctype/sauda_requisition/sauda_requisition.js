// Copyright (c) 2026, DeHaat Engineering
// Client Script: Sauda Requisition

frappe.ui.form.on("Sauda Requisition", {

    // ── Form Setup ────────────────────────────────────────────────────────
    setup: function (frm) {
        // Restrict 'Requested By' field to actual users
        frm.set_query("requested_by", function () {
            return { filters: { enabled: 1 } };
        });
        // Restrict suppliers to enabled ones
        frm.set_query("supplier", function () {
            return { filters: { disabled: 0 } };
        });
    },

    refresh: function (frm) {
        frm._set_field_properties();
        frm._render_workflow_buttons();
        frm._render_status_badge();
    },

    onload: function (frm) {
        // Set defaults for new documents
        if (frm.is_new()) {
            frm.set_value("requisition_date", frappe.datetime.get_today());
            frm.set_value("requested_by", frappe.session.user);
            frm.set_value("workflow_state", "Draft");
        }
    },

    // ── Field Change Handlers ─────────────────────────────────────────────
    supplier: function (frm) {
        if (frm.doc.supplier) {
            frappe.db.get_value("Supplier", frm.doc.supplier, ["supplier_name"])
                .then(r => {
                    if (r && r.message) {
                        frappe.show_alert({
                            message: __("Supplier set: {0}", [r.message.supplier_name || frm.doc.supplier]),
                            indicator: "green"
                        }, 3);
                    }
                });
        }
    },

    // ── Internal Helpers ──────────────────────────────────────────────────
    _set_field_properties: function (frm) {
        let state = frm.doc.workflow_state || "Draft";
        let is_draft = (state === "Draft");
        let is_approved = (state === "Approved");

        // Make core fields read-only once submitted
        let lock_fields = ["supplier", "department", "requested_by", "requisition_date"];
        lock_fields.forEach(f => frm.set_df_property(f, "read_only", is_draft ? 0 : 1));

        // Items table editable only in Draft
        frm.set_df_property("items", "read_only", is_draft ? 0 : 1);
    },

    _render_workflow_buttons: function (frm) {
        let state = frm.doc.workflow_state || "Draft";
        let roles = frappe.user_roles;

        // ── Create Purchase Order button ───────────────────────────────
        if (state === "Approved" && roles.includes("MIS Executive")) {
            if (!frm.doc.purchase_order) {
                frm.add_custom_button(__("Create Purchase Order"), function () {
                    frappe.confirm(
                        __("Create a Purchase Order from this Sauda Requisition?"),
                        function () {
                            frappe.show_progress(__("Creating Purchase Order"), 30, 100);
                            frappe.call({
                                method: "dehaat_procurement.procurement_management.doctype.sauda_requisition.sauda_requisition.create_purchase_order",
                                args: { requisition_name: frm.doc.name },
                                freeze: true,
                                freeze_message: __("Creating Purchase Order..."),
                                callback: function (r) {
                                    frappe.show_progress(__("Creating Purchase Order"), 100, 100);
                                    if (r.message) {
                                        frappe.set_route("Form", "Purchase Order", r.message);
                                    }
                                    frm.reload_doc();
                                },
                            });
                        }
                    );
                }, __("Actions"));
            }
        }

        // ── View Purchase Order button ──────────────────────────────────
        if (frm.doc.purchase_order) {
            frm.add_custom_button(__("View Purchase Order"), function () {
                frappe.set_route("Form", "Purchase Order", frm.doc.purchase_order);
            }, __("Links"));
        }
    },

    _render_status_badge: function (frm) {
        let state = frm.doc.workflow_state || "Draft";
        let color_map = {
            "Draft": "gray",
            "Pending Approval": "orange",
            "Approved": "green",
            "Rejected": "red",
            "PO Created": "blue",
            "Completed": "darkgreen"
        };
        let color = color_map[state] || "gray";
        let badge = `<span class="indicator-pill ${color}" style="margin-left:8px;">${state}</span>`;
        frm.set_intro(badge, color);
    },
});


// ── Child Table: Sauda Requisition Item ───────────────────────────────────────
frappe.ui.form.on("Sauda Requisition Item", {

    item_code: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.item_code) return;

        // Auto-populate item_name and unit from Item master
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Item",
                name: row.item_code,
                filters: { disabled: 0 }
            },
            callback: function (r) {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, "item_name", r.message.item_name);
                    frappe.model.set_value(cdt, cdn, "unit", r.message.stock_uom);
                } else {
                    frappe.msgprint({
                        message: __("Item '{0}' not found.", [row.item_code]),
                        indicator: "red",
                        title: __("Item Not Found")
                    });
                    frappe.model.set_value(cdt, cdn, "item_code", "");
                }
            }
        });
    },

    quantity_required: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.quantity_required <= 0) {
            frappe.msgprint({
                message: __("Quantity must be greater than zero for item {0}.", [row.item_code]),
                indicator: "orange"
            });
        }
    },

    rate: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.rate < 0) {
            frappe.msgprint({
                message: __("Rate cannot be negative for item {0}.", [row.item_code]),
                indicator: "orange"
            });
            frappe.model.set_value(cdt, cdn, "rate", 0);
        }
    },
});
