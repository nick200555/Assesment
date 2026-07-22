# Copyright (c) 2026, DeHaat Engineering
# License: MIT
# ─────────────────────────────────────────────────────────────────────────────
# Warehouse Receiving Page — Python controller
# (Frappe pages have a thin Python side; main logic lives in JS + API)
# ─────────────────────────────────────────────────────────────────────────────

import frappe
from frappe import _


def get_context(context):
    """Inject server-side context into the page template if needed."""
    # Enforce page-level access
    allowed_roles = {"Warehouse Executive", "System Manager", "MIS Executive"}
    user_roles = set(frappe.get_roles(frappe.session.user))

    if not allowed_roles.intersection(user_roles):
        frappe.throw(
            _("You do not have permission to access Warehouse Receiving."),
            frappe.PermissionError
        )

    context.no_cache = 1
    context.title = "Warehouse Receiving"
