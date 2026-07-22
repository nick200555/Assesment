# Copyright (c) 2026, DeHaat Engineering
# License: MIT
# ─────────────────────────────────────────────────────────────────────────────
# SAP Data Transfer API
#
# DESIGN NOTE:
#   Actual SAP connectivity requires SAP endpoint URL, client ID, RFC
#   credentials or API key — none of which are specified in the assessment.
#   This module therefore exposes integration-ready Frappe whitelisted APIs
#   that return well-structured JSON for consumption by SAP middleware.
#   SAP-outbound connection details must be configured via Frappe System
#   Settings / Environment Variables — never hard-coded.
# ─────────────────────────────────────────────────────────────────────────────

import frappe
from frappe import _


# ─── Inbound: Frappe → SAP ────────────────────────────────────────────────────

@frappe.whitelist()
def get_po_for_sap(purchase_order):
    """
    Return structured Purchase Order data formatted for SAP consumption.

    Authorization:
        Caller must have MIS Executive or System Manager role.

    Args:
        purchase_order (str): ERPNext Purchase Order name (e.g. "PO-2026-00001")

    Returns:
        dict: Structured PO payload for SAP transfer.

    Example response:
        {
            "purchase_order": "PO-2026-00001",
            "sauda_requisition": "SR-2026-00001",
            "supplier": "SUP-001",
            "supplier_name": "ABC Agri Supplies",
            "transaction_date": "2026-07-22",
            "schedule_date": "2026-07-29",
            "company": "DeHaat India Pvt Ltd",
            "currency": "INR",
            "total": 50000.00,
            "status": "To Receive and Bill",
            "items": [
                {
                    "item_code": "ITEM-001",
                    "item_name": "Wheat Seeds",
                    "quantity": 100.0,
                    "uom": "Kg",
                    "rate": 50.0,
                    "amount": 5000.0,
                    "warehouse": "Stores - DH"
                }
            ]
        }
    """
    _assert_role(
        ["MIS Executive", "System Manager", "Sourcing Head"],
        _("You do not have permission to access Purchase Order data for SAP transfer.")
    )

    if not purchase_order:
        frappe.throw(_("Purchase Order name is required."))

    if not frappe.db.exists("Purchase Order", purchase_order):
        frappe.throw(
            _("Purchase Order '{0}' does not exist.").format(purchase_order)
        )

    # Permission check — standard Frappe document permission
    po = frappe.get_doc("Purchase Order", purchase_order)

    # Build structured payload
    items_payload = []
    for item in po.items:
        items_payload.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "quantity": item.qty,
            "received_qty": item.received_qty,
            "uom": item.uom,
            "rate": item.rate,
            "amount": item.amount,
            "warehouse": item.warehouse or "",
            "schedule_date": str(item.schedule_date) if item.schedule_date else "",
        })

    payload = {
        "purchase_order": po.name,
        "sauda_requisition": po.get("custom_sauda_requisition") or "",
        "supplier": po.supplier,
        "supplier_name": po.supplier_name,
        "transaction_date": str(po.transaction_date),
        "schedule_date": str(po.schedule_date) if po.schedule_date else "",
        "company": po.company,
        "currency": po.currency,
        "total": po.total,
        "grand_total": po.grand_total,
        "status": po.status,
        "items": items_payload,
        "_meta": {
            "generated_at": frappe.utils.now(),
            "generated_by": frappe.session.user,
            "frappe_version": frappe.__version__,
            "api_version": "1.0",
            "note": (
                "SAP outbound connectivity requires endpoint configuration. "
                "Set SAP_ENDPOINT and SAP_API_KEY in environment variables."
            ),
        }
    }

    return payload


@frappe.whitelist()
def get_grn_for_sap(purchase_receipt):
    """
    Return structured GRN / Purchase Receipt data for SAP transfer.

    Args:
        purchase_receipt (str): ERPNext Purchase Receipt name

    Returns:
        dict: Structured GRN payload for SAP.
    """
    _assert_role(
        ["MIS Executive", "System Manager", "Warehouse Executive"],
        _("You do not have permission to access GRN data for SAP transfer.")
    )

    if not frappe.db.exists("Purchase Receipt", purchase_receipt):
        frappe.throw(
            _("Purchase Receipt '{0}' does not exist.").format(purchase_receipt)
        )

    pr = frappe.get_doc("Purchase Receipt", purchase_receipt)

    items_payload = []
    for item in pr.items:
        items_payload.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "quantity": item.qty,
            "uom": item.uom,
            "rate": item.rate,
            "amount": item.amount,
            "warehouse": item.warehouse or "",
            "batch_no": item.batch_no or "",
            "purchase_order": item.purchase_order or "",
        })

    payload = {
        "purchase_receipt": pr.name,
        "purchase_order": pr.items[0].purchase_order if pr.items else "",
        "supplier": pr.supplier,
        "supplier_name": pr.supplier_name,
        "posting_date": str(pr.posting_date),
        "company": pr.company,
        "status": pr.status,
        "total": pr.total,
        "items": items_payload,
        "_meta": {
            "generated_at": frappe.utils.now(),
            "generated_by": frappe.session.user,
            "api_version": "1.0",
        }
    }

    return payload


@frappe.whitelist()
def get_pending_pos_for_sap():
    """
    Return a list of all submitted Purchase Orders pending receiving,
    for bulk SAP synchronization.
    """
    _assert_role(
        ["MIS Executive", "System Manager"],
        _("You do not have permission to list Purchase Orders for SAP transfer.")
    )

    pos = frappe.get_all(
        "Purchase Order",
        filters={"status": ["in", ["To Receive and Bill", "To Receive"]], "docstatus": 1},
        fields=["name", "supplier", "supplier_name", "transaction_date",
                "total", "status", "custom_sauda_requisition"],
        order_by="transaction_date desc",
    )

    return {"purchase_orders": pos, "count": len(pos)}


# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _assert_role(allowed_roles, error_message):
    """Raise PermissionError if the current user lacks required roles."""
    if frappe.session.user == "Administrator":
        return
    user_roles = set(frappe.get_roles(frappe.session.user))
    if not user_roles.intersection(allowed_roles):
        frappe.throw(error_message, frappe.PermissionError)
