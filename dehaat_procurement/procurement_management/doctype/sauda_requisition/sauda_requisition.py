# Copyright (c) 2026, DeHaat Engineering and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document


class SaudaRequisition(Document):
    # ─── Lifecycle Hooks ──────────────────────────────────────────────────────

    def before_insert(self):
        """Set defaults before first save."""
        if not self.requisition_date:
            self.requisition_date = frappe.utils.today()
        if not self.requested_by:
            self.requested_by = frappe.session.user

    def validate(self):
        """Run all server-side validation rules."""
        self._validate_supplier()
        self._validate_department()
        self._validate_items()
        self._set_requisition_number()

    def before_save(self):
        """Sync workflow_state label if not set by workflow engine."""
        if not self.workflow_state:
            self.workflow_state = "Draft"

    # ─── Validation Helpers ───────────────────────────────────────────────────

    def _validate_supplier(self):
        if not self.supplier:
            frappe.throw(_("Supplier is required."))
        if not frappe.db.exists("Supplier", self.supplier):
            frappe.throw(_("Supplier '{0}' does not exist.").format(self.supplier))

    def _validate_department(self):
        if not self.department:
            frappe.throw(_("Department is required."))
        if not frappe.db.exists("Department", self.department):
            frappe.throw(_("Department '{0}' does not exist.").format(self.department))

    def _validate_items(self):
        if not self.items:
            frappe.throw(_("Please add at least one item to the requisition."))

        seen_items = {}
        for idx, item in enumerate(self.items):
            row_label = _("Row {0}").format(idx + 1)

            # Item Code must be provided
            if not item.item_code:
                frappe.throw(
                    _("{0}: Item Code is required.").format(row_label)
                )

            # Item must exist in Item master
            if not frappe.db.exists("Item", item.item_code):
                frappe.throw(
                    _("{0}: Item '{1}' does not exist in the system.").format(
                        row_label, item.item_code
                    )
                )

            # Quantity must be > 0
            if not item.quantity_required or item.quantity_required <= 0:
                frappe.throw(
                    _("Quantity for {0} must be greater than zero.").format(
                        item.item_code
                    )
                )

            # Rate cannot be negative
            if item.rate is not None and item.rate < 0:
                frappe.throw(
                    _("Rate for {0} cannot be negative.").format(item.item_code)
                )

            # Warn on duplicate item codes
            if item.item_code in seen_items:
                frappe.msgprint(
                    _("Item '{0}' appears more than once (rows {1} and {2}). "
                      "Consider consolidating.").format(
                        item.item_code, seen_items[item.item_code], idx + 1
                    ),
                    indicator="orange",
                    title=_("Duplicate Item Warning"),
                )
            else:
                seen_items[item.item_code] = idx + 1

    def _set_requisition_number(self):
        """Mirror the document name into the display field."""
        if self.name and self.name != "New Sauda Requisition":
            self.requisition_number = self.name

    # ─── Permission Query (list view filtering) ───────────────────────────────

    @staticmethod
    def get_permission_query_conditions(user=None):
        """
        Procurement Executives can only see their own requisitions.
        Sourcing Heads, MIS Executives, Warehouse Executives see all.
        Administrators see all.
        """
        if not user:
            user = frappe.session.user

        if user == "Administrator":
            return ""

        roles = frappe.get_roles(user)
        privileged_roles = {"Sourcing Head", "MIS Executive", "Warehouse Executive", "System Manager"}

        if privileged_roles.intersection(roles):
            return ""

        if "Procurement Executive" in roles:
            return f"`tabSauda Requisition`.`requested_by` = {frappe.db.escape(user)}"

        return "1=0"  # deny access to all others

    @staticmethod
    def has_permission(doc, ptype="read", user=None):
        """Fine-grained permission check."""
        if not user:
            user = frappe.session.user

        if user == "Administrator":
            return True

        roles = frappe.get_roles(user)

        if "System Manager" in roles:
            return True

        if ptype in ("read", "print", "email", "export"):
            allowed_roles = {
                "Procurement Executive", "Sourcing Head",
                "MIS Executive", "Warehouse Executive"
            }
            if allowed_roles.intersection(roles):
                return True

        if ptype in ("write", "create"):
            if "Procurement Executive" in roles:
                return True

        return False


# ─── Whitelisted API Methods ──────────────────────────────────────────────────

@frappe.whitelist()
def create_purchase_order(requisition_name):
    """
    Create a standard ERPNext Purchase Order from an approved Sauda Requisition.

    Rules enforced:
    - Requisition must exist and be in 'Approved' workflow state.
    - Only MIS Executive or System Manager may call this.
    - A PO must not already exist for this requisition (idempotency).
    - All items and quantities are validated server-side.

    Returns the Purchase Order name on success.
    """
    # ── Authorization check ────────────────────────────────────────────────
    _assert_role(["MIS Executive", "System Manager"],
                 _("Only MIS Executive can create a Purchase Order."))

    # ── Load and validate requisition ─────────────────────────────────────
    if not frappe.db.exists("Sauda Requisition", requisition_name):
        frappe.throw(_("Sauda Requisition '{0}' does not exist.").format(requisition_name))

    sr = frappe.get_doc("Sauda Requisition", requisition_name)

    if sr.workflow_state != "Approved":
        frappe.throw(
            _("Purchase Order can only be created for an Approved requisition. "
              "Current status: {0}").format(sr.workflow_state)
        )

    # ── Duplicate PO guard ─────────────────────────────────────────────────
    if sr.purchase_order and frappe.db.exists("Purchase Order", sr.purchase_order):
        frappe.throw(
            _("Purchase Order {0} already exists for Sauda Requisition {1}.").format(
                sr.purchase_order, requisition_name
            )
        )

    # ── Build Purchase Order document ──────────────────────────────────────
    po = frappe.new_doc("Purchase Order")
    po.supplier = sr.supplier
    po.transaction_date = frappe.utils.today()
    po.schedule_date = frappe.utils.add_days(frappe.utils.today(), 7)
    po.company = frappe.defaults.get_user_default("Company") or _get_default_company()
    po.custom_sauda_requisition = requisition_name  # traceability link

    if not po.company:
        frappe.throw(_("No default Company set. Please configure Company in ERPNext."))

    if not sr.items:
        frappe.throw(_("Sauda Requisition has no items. Cannot create Purchase Order."))

    for sr_item in sr.items:
        if not sr_item.quantity_required or sr_item.quantity_required <= 0:
            frappe.throw(
                _("Quantity for item '{0}' must be greater than zero.").format(
                    sr_item.item_code
                )
            )

        po.append("items", {
            "item_code": sr_item.item_code,
            "item_name": sr_item.item_name,
            "qty": sr_item.quantity_required,
            "uom": sr_item.unit,
            "rate": sr_item.rate or 0,
            "schedule_date": po.schedule_date,
            "description": sr_item.item_name,
        })

    po.set_missing_values()
    po.flags.ignore_permissions = False
    po.insert()
    po.submit()

    # ── Update requisition with PO link ────────────────────────────────────
    frappe.db.set_value(
        "Sauda Requisition", requisition_name,
        {"purchase_order": po.name, "workflow_state": "PO Created"},
        update_modified=True
    )

    frappe.msgprint(
        _("Purchase Order {0} created successfully.").format(po.name),
        title=_("Purchase Order Created"),
        indicator="green"
    )

    return po.name


@frappe.whitelist()
def get_requisition_status(requisition_name):
    """Return current workflow state and PO link for a requisition."""
    if not frappe.db.exists("Sauda Requisition", requisition_name):
        frappe.throw(_("Sauda Requisition '{0}' not found.").format(requisition_name))

    doc = frappe.get_doc("Sauda Requisition", requisition_name)
    return {
        "name": doc.name,
        "workflow_state": doc.workflow_state,
        "purchase_order": doc.purchase_order,
        "supplier": doc.supplier,
    }


# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _assert_role(allowed_roles, error_message):
    """Throw PermissionError if current user does not have any of the allowed roles."""
    user_roles = frappe.get_roles(frappe.session.user)
    if not set(allowed_roles).intersection(user_roles):
        frappe.throw(error_message, frappe.PermissionError)


def _get_default_company():
    """Retrieve the first company in the system as a fallback."""
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        company = frappe.db.get_value("Company", {}, "name")
    return company


def get_permission_query_conditions(user=None):
    """Module-level wrapper required by hooks.py."""
    return SaudaRequisition.get_permission_query_conditions(user)


def has_permission(doc, ptype="read", user=None):
    """Module-level wrapper required by hooks.py."""
    return SaudaRequisition.has_permission(doc, ptype, user)
