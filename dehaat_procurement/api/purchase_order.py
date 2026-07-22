# Copyright (c) 2026, DeHaat Engineering
# License: MIT
# ─────────────────────────────────────────────────────────────────────────────
# Purchase Order & Purchase Receipt event hooks + server methods
# ─────────────────────────────────────────────────────────────────────────────

import frappe
from frappe import _


# ─── Document Event Hooks (called from hooks.py) ──────────────────────────────

def on_purchase_order_submit(doc, method=None):
    """
    Called when a Purchase Order is submitted.
    Syncs the linked Sauda Requisition state to 'PO Created'.
    """
    sr_name = doc.get("custom_sauda_requisition")
    if sr_name and frappe.db.exists("Sauda Requisition", sr_name):
        current_state = frappe.db.get_value("Sauda Requisition", sr_name, "workflow_state")
        if current_state == "Approved":
            frappe.db.set_value(
                "Sauda Requisition", sr_name,
                {
                    "workflow_state": "PO Created",
                    "purchase_order": doc.name,
                },
                update_modified=True
            )


def on_purchase_order_cancel(doc, method=None):
    """
    Called when a Purchase Order is cancelled.
    Rolls back Sauda Requisition to 'Approved' so a new PO can be raised.
    """
    sr_name = doc.get("custom_sauda_requisition")
    if sr_name and frappe.db.exists("Sauda Requisition", sr_name):
        frappe.db.set_value(
            "Sauda Requisition", sr_name,
            {
                "workflow_state": "Approved",
                "purchase_order": None,
            },
            update_modified=True
        )
        frappe.msgprint(
            _("Sauda Requisition {0} has been reset to 'Approved' because PO was cancelled.").format(sr_name),
            indicator="orange"
        )


def on_purchase_receipt_submit(doc, method=None):
    """
    Called when a Purchase Receipt is submitted.
    Checks if ALL items in the linked PO are fully received;
    if so, marks the Sauda Requisition as 'Completed'.
    """
    # Find the SR linked to any PO in this receipt
    po_names = list(set(
        item.purchase_order for item in doc.items if item.purchase_order
    ))

    for po_name in po_names:
        sr_name = frappe.db.get_value(
            "Purchase Order", po_name, "custom_sauda_requisition"
        )
        if not sr_name:
            continue
        if not frappe.db.exists("Sauda Requisition", sr_name):
            continue

        # Check if PO is now fully received
        po_doc = frappe.get_doc("Purchase Order", po_name)
        fully_received = all(
            (item.received_qty >= item.qty) for item in po_doc.items
        )

        if fully_received:
            frappe.db.set_value(
                "Sauda Requisition", sr_name,
                "workflow_state", "Completed",
                update_modified=True
            )
            frappe.msgprint(
                _("Sauda Requisition {0} marked as Completed — all items fully received.").format(sr_name),
                indicator="green"
            )


# ─── Whitelisted Utility APIs ─────────────────────────────────────────────────

@frappe.whitelist()
def get_po_receiving_status(purchase_order):
    """
    Return receiving progress for each item in a Purchase Order.
    Used by the Warehouse Receiving page to show pending quantities.

    Args:
        purchase_order (str): Purchase Order name

    Returns:
        dict: {
            "purchase_order": "PO-XXXX",
            "supplier": "...",
            "status": "...",
            "is_completed": bool,
            "items": [
                {
                    "item_code": ...,
                    "item_name": ...,
                    "ordered_qty": ...,
                    "received_qty": ...,
                    "pending_qty": ...,
                    "uom": ...,
                    "warehouse": ...,
                }
            ]
        }
    """
    _assert_role(
        ["Warehouse Executive", "MIS Executive", "System Manager", "Sourcing Head"],
        _("You do not have permission to view Purchase Order receiving status.")
    )

    if not frappe.db.exists("Purchase Order", purchase_order):
        frappe.throw(_("Purchase Order '{0}' not found.").format(purchase_order))

    po = frappe.get_doc("Purchase Order", purchase_order)

    if po.docstatus != 1:
        frappe.throw(
            _("Purchase Order '{0}' is not submitted. Cannot receive against it.").format(purchase_order)
        )

    items = []
    is_fully_received = True
    for item in po.items:
        pending = max(0, (item.qty or 0) - (item.received_qty or 0))
        if pending > 0:
            is_fully_received = False
        items.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "ordered_qty": item.qty,
            "received_qty": item.received_qty or 0,
            "pending_qty": pending,
            "uom": item.uom,
            "warehouse": item.warehouse or "",
            "rate": item.rate,
        })

    return {
        "purchase_order": po.name,
        "supplier": po.supplier,
        "supplier_name": po.supplier_name,
        "status": po.status,
        "is_completed": is_fully_received,
        "sauda_requisition": po.get("custom_sauda_requisition") or "",
        "items": items,
    }


@frappe.whitelist()
def validate_scanned_item(purchase_order, item_code=None, barcode=None):
    """
    Validate a scanned barcode or item code against a Purchase Order.
    Resolves barcode → item code if barcode is provided.

    Args:
        purchase_order (str): PO name
        item_code (str, optional): Direct item code entry
        barcode (str, optional): Barcode scan input

    Returns:
        dict: Item details with receiving status, or error.
    """
    _assert_role(
        ["Warehouse Executive", "System Manager"],
        _("You do not have permission to perform warehouse receiving.")
    )

    if not frappe.db.exists("Purchase Order", purchase_order):
        frappe.throw(_("Purchase Order '{0}' not found.").format(purchase_order))

    po = frappe.get_doc("Purchase Order", purchase_order)

    if po.docstatus != 1:
        frappe.throw(_("Purchase Order is not submitted."))

    # ── Resolve barcode to item_code ──────────────────────────────────────
    resolved_item_code = item_code
    if barcode and not item_code:
        # Check Item Barcode table
        barcode_item = frappe.db.get_value(
            "Item Barcode",
            {"barcode": barcode},
            "parent"
        )
        if barcode_item:
            resolved_item_code = barcode_item
        else:
            # Try direct item_code match
            if frappe.db.exists("Item", barcode):
                resolved_item_code = barcode
            else:
                frappe.throw(
                    _("Barcode '{0}' does not match any Item in the system.").format(barcode)
                )

    if not resolved_item_code:
        frappe.throw(_("Please provide an Item Code or scan a Barcode."))

    # Check if PO is already fully received
    all_received = all(
        (item.received_qty or 0) >= item.qty for item in po.items
    )
    if all_received:
        frappe.throw(
            _("Purchase Order '{0}' is already fully received. No further receiving allowed.").format(
                purchase_order
            )
        )

    # ── Find item in PO ───────────────────────────────────────────────────
    po_item = None
    for item in po.items:
        if item.item_code == resolved_item_code:
            po_item = item
            break

    if not po_item:
        frappe.throw(
            _("Item '{0}' is not present in Purchase Order '{1}'.").format(
                resolved_item_code, purchase_order
            )
        )

    pending = max(0, (po_item.qty or 0) - (po_item.received_qty or 0))

    if pending <= 0:
        frappe.throw(
            _("Item '{0}' has already been fully received in Purchase Order '{1}'.").format(
                resolved_item_code, purchase_order
            )
        )

    return {
        "item_code": po_item.item_code,
        "item_name": po_item.item_name,
        "ordered_qty": po_item.qty,
        "received_qty": po_item.received_qty or 0,
        "pending_qty": pending,
        "uom": po_item.uom,
        "warehouse": po_item.warehouse or "",
        "rate": po_item.rate,
    }


@frappe.whitelist()
def create_purchase_receipt(purchase_order, items, warehouse=None):
    """
    Create a Purchase Receipt (GRN) from a Warehouse Receiving session.

    All validation is performed server-side. The frontend must NOT be
    trusted for quantity calculations.

    Args:
        purchase_order (str): PO name
        items (list | str): JSON list of {item_code, qty, warehouse, batch_no}
        warehouse (str, optional): Default warehouse if not per-item

    Returns:
        dict: {"purchase_receipt": "PR-XXXX", "status": "success"}
    """
    _assert_role(
        ["Warehouse Executive", "System Manager"],
        _("Only Warehouse Executive can create a Goods Receipt.")
    )

    import json
    if isinstance(items, str):
        items = json.loads(items)

    if not items:
        frappe.throw(_("No items provided for Goods Receipt creation."))

    if not frappe.db.exists("Purchase Order", purchase_order):
        frappe.throw(_("Purchase Order '{0}' not found.").format(purchase_order))

    po = frappe.get_doc("Purchase Order", purchase_order)

    if po.docstatus != 1:
        frappe.throw(_("Purchase Order '{0}' is not submitted.").format(purchase_order))

    # Build PO item lookup map (server-side authoritative quantities)
    po_item_map = {}
    for po_item in po.items:
        po_item_map[po_item.item_code] = {
            "ordered_qty": po_item.qty,
            "received_qty": po_item.received_qty or 0,
            "pending_qty": max(0, po_item.qty - (po_item.received_qty or 0)),
            "uom": po_item.uom,
            "rate": po_item.rate,
            "warehouse": po_item.warehouse or warehouse,
        }

    # Validate each incoming item
    receipt_items = []
    for recv_item in items:
        item_code = recv_item.get("item_code")
        qty = frappe.utils.flt(recv_item.get("qty", 0))
        item_warehouse = recv_item.get("warehouse") or warehouse

        if item_code not in po_item_map:
            frappe.throw(
                _("Item '{0}' is not in Purchase Order '{1}'.").format(item_code, purchase_order)
            )

        po_data = po_item_map[item_code]

        if qty <= 0:
            frappe.throw(
                _("Received quantity for '{0}' must be greater than zero.").format(item_code)
            )

        if qty > po_data["pending_qty"]:
            frappe.throw(
                _("Cannot receive {0} units of '{1}'. Only {2} units remain to be received.").format(
                    qty, item_code, po_data["pending_qty"]
                )
            )

        if not item_warehouse:
            frappe.throw(
                _("Warehouse is required for item '{0}'.").format(item_code)
            )

        if not frappe.db.exists("Warehouse", item_warehouse):
            frappe.throw(
                _("Warehouse '{0}' does not exist.").format(item_warehouse)
            )

        receipt_item = {
            "item_code": item_code,
            "item_name": po_data.get("item_name", item_code),
            "qty": qty,
            "uom": po_data["uom"],
            "rate": po_data["rate"],
            "warehouse": item_warehouse,
            "purchase_order": purchase_order,
            "purchase_order_item": None,  # Frappe will map this
        }

        # Batch number (optional, required only if item has batch tracking)
        batch_no = recv_item.get("batch_no", "")
        if batch_no:
            receipt_item["batch_no"] = batch_no

        receipt_items.append(receipt_item)

    # Create Purchase Receipt
    pr = frappe.new_doc("Purchase Receipt")
    pr.supplier = po.supplier
    pr.posting_date = frappe.utils.today()
    pr.company = po.company
    pr.buying_price_list = po.buying_price_list

    for ri in receipt_items:
        pr.append("items", ri)

    pr.set_missing_values()
    pr.insert()
    pr.submit()

    # Update Sauda Requisition if fully received
    sr_name = po.get("custom_sauda_requisition")
    if sr_name and frappe.db.exists("Sauda Requisition", sr_name):
        # Reload PO to get updated received_qty
        po.reload()
        fully_received = all(
            (item.received_qty or 0) >= item.qty for item in po.items
        )
        if fully_received:
            frappe.db.set_value(
                "Sauda Requisition", sr_name,
                "workflow_state", "Completed",
                update_modified=True
            )

    return {
        "purchase_receipt": pr.name,
        "status": "success",
        "message": _("Goods Receipt {0} created successfully.").format(pr.name),
    }


# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _assert_role(allowed_roles, error_message):
    if frappe.session.user == "Administrator":
        return
    user_roles = set(frappe.get_roles(frappe.session.user))
    if not user_roles.intersection(allowed_roles):
        frappe.throw(error_message, frappe.PermissionError)
