# Copyright (c) 2026, DeHaat Engineering
# License: MIT
# ─────────────────────────────────────────────────────────────────────────────
# Procurement Dashboard — Stats & Drilldown API
# ─────────────────────────────────────────────────────────────────────────────
import frappe
from frappe import _

# category_key -> (doctype, filters)
_CATEGORY_MAP = {
    "pending_approvals": ("Sauda Requisition", {"workflow_state": "Pending Approval"}),
    "approved_requisitions": ("Sauda Requisition", {"workflow_state": "Approved"}),
    "open_purchase_orders": (
        "Purchase Order",
        {"docstatus": 1, "status": ["not in", ["Completed", "Closed", "Cancelled"]]},
    ),
    "pending_grns": ("Sauda Requisition", {"workflow_state": "PO Created"}),
    "completed_grns": ("Sauda Requisition", {"workflow_state": "Completed"}),
}


@frappe.whitelist()
def get_dashboard_stats():
    """
    Return counts for all 5 dashboard cards.
    Visible to any of the core procurement roles.
    """
    _assert_role(
        ["Procurement Executive", "Sourcing Head", "MIS Executive",
         "Warehouse Executive", "System Manager"],
        _("You do not have permission to view the procurement dashboard.")
    )
    stats = {}
    for key, (doctype, filters) in _CATEGORY_MAP.items():
        stats[key] = frappe.db.count(doctype, filters)
    return stats


@frappe.whitelist()
def get_dashboard_list(category):
    """
    Return the underlying records for a given dashboard category,
    used when a user clicks a stat card to drill down.
    """
    _assert_role(
        ["Procurement Executive", "Sourcing Head", "MIS Executive",
         "Warehouse Executive", "System Manager"],
        _("You do not have permission to view the procurement dashboard.")
    )
    if category not in _CATEGORY_MAP:
        frappe.throw(_("Invalid dashboard category: {0}").format(category))

    doctype, filters = _CATEGORY_MAP[category]

    if doctype == "Sauda Requisition":
        fields = ["name", "supplier", "requisition_date", "workflow_state",
                   "purchase_order", "modified"]
    else:
        fields = ["name", "supplier", "supplier_name", "transaction_date",
                   "status", "grand_total", "modified"]

    return {
        "doctype": doctype,
        "records": frappe.get_all(
            doctype, filters=filters, fields=fields,
            order_by="modified desc", limit_page_length=20
        ),
    }


def _assert_role(allowed_roles, error_message):
    if frappe.session.user == "Administrator":
        return
    user_roles = set(frappe.get_roles(frappe.session.user))
    if not user_roles.intersection(allowed_roles):
        frappe.throw(error_message, frappe.PermissionError)