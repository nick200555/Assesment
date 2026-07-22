from . import __version__ as app_version

app_name = "dehaat_procurement"
app_title = "Dehaat Procurement"
app_publisher = "DeHaat Engineering"
app_description = "DeHaat Procurement Workflow & Warehouse Receiving Application"
app_email = "engineering@dehaat.com"
app_license = "MIT"
app_version = "1.0.0"

# ─── Required Apps ────────────────────────────────────────────────────────────
required_apps = ["frappe", "erpnext"]

# ─── Fixtures ─────────────────────────────────────────────────────────────────
# Fixtures are imported on bench migrate and export via bench export-fixtures
fixtures = [
    {"dt": "Role", "filters": [["name", "in", [
        "Procurement Executive",
        "Sourcing Head",
        "Warehouse Executive",
        "MIS Executive"
    ]]]},
    {"dt": "Workflow", "filters": [["name", "in", ["Sauda Requisition Workflow"]]]},
    {"dt": "Workflow State", "filters": [["workflow_state_name", "in", [
        "Draft",
        "Pending Approval",
        "Approved",
        "Rejected",
        "PO Created",
        "Completed"
    ]]]},
    {"dt": "Workflow Action Master", "filters": [["name", "in", [
        "Submit",
        "Approve",
        "Reject",
        "Create Purchase Order",
        "Complete GRN"
    ]]]},
    {"dt": "Custom Field", "filters": [["module", "=", "Procurement Management"]]},
    # Note: Workspace fixture removed — Frappe v15 Workspace requires a complex
    # block-editor 'content' JSON field that must be created via the Frappe UI.
    # Create the Procurement Management workspace manually after installation.
]

# ─── DocType Class Overrides ───────────────────────────────────────────────────
# (none needed — we use our own custom DocTypes)

# ─── Document Events ──────────────────────────────────────────────────────────
doc_events = {
    "Purchase Order": {
        "on_submit": "dehaat_procurement.api.purchase_order.on_purchase_order_submit",
        "on_cancel": "dehaat_procurement.api.purchase_order.on_purchase_order_cancel",
    },
    "Purchase Receipt": {
        "on_submit": "dehaat_procurement.api.purchase_order.on_purchase_receipt_submit",
    },
}

# ─── Scheduled Tasks ──────────────────────────────────────────────────────────
scheduler_events = {
    # "hourly": ["dehaat_procurement.api.tasks.hourly"],
    # "daily": ["dehaat_procurement.api.tasks.daily"],
}

# ─── Website Routes ───────────────────────────────────────────────────────────
website_route_rules = []

# ─── Permission Query Conditions ──────────────────────────────────────────────
# Restrict what users see in list view
permission_query_conditions = {
    "Sauda Requisition": (
        "dehaat_procurement.procurement_management.doctype"
        ".sauda_requisition.sauda_requisition.get_permission_query_conditions"
    ),
}

# ─── Has Permission ───────────────────────────────────────────────────────────
has_permission = {
    "Sauda Requisition": (
        "dehaat_procurement.procurement_management.doctype"
        ".sauda_requisition.sauda_requisition.has_permission"
    ),
}

# ─── App Includes (global JS/CSS) ─────────────────────────────────────────────
app_include_css = []
app_include_js = []

# ─── Web Include ──────────────────────────────────────────────────────────────
web_include_css = []
web_include_js = []

# ─── Override Whitelisted Methods ─────────────────────────────────────────────
override_whitelisted_methods = {}
