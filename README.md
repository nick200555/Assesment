# DeHaat Procurement Workflow & Warehouse Receiving Application

> **Frappe/ERPNext v15 Custom Application**
> Built for the DeHaat Frappe Workflow & Application Development Intern Assessment

---

## 1. Project Overview

This application implements a workflow-driven **Procurement and Warehouse Receiving** process on top of the Frappe Framework and ERPNext v15.

It covers the complete procurement lifecycle:

- Procurement team raises a **Sauda Requisition**
- The **Sourcing Head** approves or rejects it
- An authorised **MIS Executive** converts the approved requisition to an ERPNext **Purchase Order** — with zero manual data re-entry
- The **Warehouse Executive** uses a custom **Warehouse Receiving** page to scan/enter items and record goods receipt quantities
- A standard ERPNext **Purchase Receipt (GRN)** is created server-side upon completion
- The Sauda Requisition is automatically marked **Completed** when all ordered quantities are received

---

## 2. Technology Stack

| Layer | Technology |
|---|---|
| Framework | Frappe Framework v15 |
| ERP | ERPNext v15 |
| Backend Language | Python 3.12 |
| Frontend Language | JavaScript (ES6+), HTML5, CSS3 |
| Database | MariaDB 10.6+ |
| Cache / Queue | Redis |
| Package Manager | pip / uv |

---

## 3. Architecture

```
Frappe Framework v15
        │
        ▼
dehaat_procurement  (Custom Frappe App)
        │
        ├── Procurement Management  (Module)
        │       │
        │       ├── Sauda Requisition  (Custom DocType)
        │       │       └── Sauda Requisition Item  (Child Table)
        │       │
        │       └── Warehouse Receiving  (Custom Frappe Page)
        │
        ├── Workflow Engine  (Frappe built-in)
        │       └── Sauda Requisition Workflow  (6 States, 5 Transitions)
        │
        ├── Role-based Permissions
        │       ├── Procurement Executive
        │       ├── Sourcing Head
        │       ├── MIS Executive
        │       └── Warehouse Executive
        │
        └── ERPNext Integration
                ├── Purchase Order  (standard, created programmatically)
                └── Purchase Receipt  (standard, created programmatically)
```

---

## 4. Features

### Custom DocTypes
- **Sauda Requisition** — Full procurement requisition header with auto-naming (`SR-.YYYY.-.#####`), supplier, department, requested-by, workflow state, and linked Purchase Order
- **Sauda Requisition Item** — Child table with item code, item name (auto-populated), quantity, UOM (auto-populated from Item master), and rate

### Procurement Workflow
- 6-state Frappe workflow with role-based action buttons
- Draft → Pending Approval → Approved / Rejected → PO Created → Completed

### Role-based Approvals
- Strictly enforced via both Frappe workflow permissions and server-side Python permission checks
- No privilege escalation between roles

### Client-side Validation
- Item name and UOM auto-populated on item selection
- Quantity and rate guards with inline messages
- Conditional action buttons shown/hidden by workflow state and user role
- Status badge on requisition form

### Server-side Validation
- Supplier and department existence checks
- At least one item required
- Quantity > 0 enforcement
- Rate non-negative enforcement
- Duplicate item warning
- Duplicate Purchase Order creation prevention (idempotency guard)
- Role assertion on every whitelisted API method

### Warehouse Receiving (Custom Frappe Page)
- Select Purchase Order → view pending items with progress bars
- Scan barcode or type Item Code (hardware scanner Enter-key compatible)
- Item resolved server-side: validates item in PO, calculates pending quantity
- Over-receipt prevention enforced server-side
- Session buffer of scanned items before single-click GRN submission
- Duplicate item in session handled with merge confirmation

### SAP Integration API
- `get_po_for_sap(purchase_order)` — structured JSON for SAP PO sync
- `get_grn_for_sap(purchase_receipt)` — structured JSON for SAP GRN sync
- `get_pending_pos_for_sap()` — batch list of open POs
- All endpoints are role-protected (`@frappe.whitelist()`)

### GRN / Purchase Receipt
- Standard ERPNext Purchase Receipt created server-side via `create_purchase_receipt()`
- Sauda Requisition automatically marked Completed when all quantities received
- Partial receiving supported — remaining quantities shown correctly on next visit

### Fixtures (portable configuration)
- Roles, Workflow States, Workflow Action Masters, Workflow, Custom Field on Purchase Order

### Workspace
- Procurement Management workspace with shortcuts to Sauda Requisition, Purchase Order, Warehouse Receiving page, and Purchase Receipt

---

## 5. Procurement Workflow

```
Draft
  │
  │  [Submit]  — Procurement Executive
  ▼
Pending Approval
  │
  ├── [Approve]  — Sourcing Head ──► Approved
  │                                     │
  │                                     │ [Create Purchase Order]  — MIS Executive
  │                                     ▼
  │                                  PO Created
  │                                     │
  │                                     │ [Complete GRN]  — Warehouse Executive
  │                                     ▼
  │                                  Completed
  │
  └── [Reject]  — Sourcing Head ──► Rejected
```

---

## 6. Roles

| Role | Responsibilities |
|---|---|
| **Procurement Executive** | Create, edit, and submit Sauda Requisitions. Cannot approve. |
| **Sourcing Head** | View submitted requisitions. Approve or Reject. |
| **MIS Executive** | Create Purchase Orders from Approved requisitions. Access SAP transfer APIs. |
| **Warehouse Executive** | Access Warehouse Receiving page. Scan items. Complete GRN. |

---

## 7. DocTypes

| DocType | Type | Purpose |
|---|---|---|
| Sauda Requisition | Parent (Custom) | Procurement requisition with workflow |
| Sauda Requisition Item | Child (Custom) | Line items for each requisition |
| Purchase Order | Parent (ERPNext Standard) | Reused — created programmatically from approved requisition |
| Purchase Receipt | Parent (ERPNext Standard) | Reused — created programmatically as GRN |
| Supplier | Master (ERPNext Standard) | Supplier reference on requisition |
| Item | Master (ERPNext Standard) | Items on requisition line |
| Department | Master (ERPNext Standard) | Department on requisition header |
| UOM | Master (ERPNext Standard) | Unit of measure on line items |
| Warehouse | Master (ERPNext Standard) | Target warehouse on receiving |

---

## 8. Workspace

**Procurement Management** workspace provides a central hub with four shortcuts:

- **Sauda Requisitions** — open the list of all requisitions
- **Purchase Orders** — open submitted POs
- **Warehouse Receiving** — open the custom receiving page
- **Purchase Receipts (GRN)** — open submitted GRNs

---

## 9. Installation

```bash
# Get the app
bench get-app https://github.com/nick200555/Assesment.git

# Install on your site
bench --site <site-name> install-app dehaat_procurement

# Run migrations (creates DocTypes, imports fixtures, syncs workspace)
bench --site <site-name> migrate

# Build frontend assets
bench build --app dehaat_procurement

# Clear cache
bench --site <site-name> clear-cache
```

---

## 10. Running

```bash
bench start
```

Open browser at: `http://<site-name>:8000`

---

## 11. Assessment Requirements Mapping

| Assessment Requirement | Implementation |
|---|---|
| Custom DocType: Sauda Requisition | `procurement_management/doctype/sauda_requisition/` |
| Child Table: Sauda Requisition Item | `procurement_management/doctype/sauda_requisition_item/` |
| Workflow (6 states, 5 transitions) | `fixtures/workflow.json` |
| Roles (4 roles) | `fixtures/role.json` |
| Role-based Approvals | Workflow transitions + `has_permission()` + `_assert_role()` |
| Client Scripting | `sauda_requisition.js` — auto-populate, conditional buttons, status badge |
| Server-side Validation | `sauda_requisition.py` — `validate()` method |
| Purchase Order generation | `sauda_requisition.py` — `create_purchase_order()` whitelisted API |
| Duplicate PO prevention | `create_purchase_order()` idempotency guard |
| SAP data transfer API | `api/sap_api.py` — 3 whitelisted endpoints |
| Warehouse Receiving Page | `procurement_management/page/warehouse_receiving/` |
| Barcode scanning | `warehouse_receiving.js` — Enter-key listener + server resolve |
| Over-receipt validation | `api/purchase_order.py` — `create_purchase_receipt()` |
| Partial receiving | `get_po_receiving_status()` + pending qty calculation |
| GRN / Purchase Receipt | `api/purchase_order.py` — `create_purchase_receipt()` |
| Completion detection | `on_purchase_receipt_submit()` event hook |
| Fixtures | `fixtures/` directory + `hooks.py` fixtures config |
| Workspace | `procurement_management/workspace/procurement_management/` |

---

## 12. Project Structure

```
dehaat_procurement/
├── setup.py
├── setup.cfg
├── requirements.txt
├── MANIFEST.in
├── README.md
├── docs/
│   ├── IMPLEMENTATION.md
│   ├── design-decisions.md
│   └── demo-guide.md
└── dehaat_procurement/
    ├── __init__.py          # version: 1.0.0
    ├── hooks.py             # app config, fixtures, doc_events
    ├── modules.txt          # declares: Procurement Management
    ├── patches.txt
    ├── api/
    │   ├── purchase_order.py    # PO events, receiving APIs, GRN creation
    │   └── sap_api.py           # SAP data transfer endpoints
    ├── fixtures/
    │   ├── role.json
    │   ├── workflow_state.json
    │   ├── workflow_action_master.json
    │   ├── workflow.json
    │   └── custom_field.json
    └── procurement_management/
        ├── doctype/
        │   ├── sauda_requisition/
        │   │   ├── sauda_requisition.json   # DocType definition
        │   │   ├── sauda_requisition.py     # Python controller
        │   │   ├── sauda_requisition.js     # Client script
        │   │   └── test_sauda_requisition.py
        │   └── sauda_requisition_item/
        │       ├── sauda_requisition_item.json
        │       ├── sauda_requisition_item.py
        │       └── sauda_requisition_item.js
        ├── page/
        │   └── warehouse_receiving/
        │       ├── warehouse_receiving.json  # Page definition + role access
        │       ├── warehouse_receiving.py    # Permission check
        │       └── warehouse_receiving.js    # Full SPA controller
        ├── workspace/
        │   └── procurement_management/
        │       └── procurement_management.json  # Workspace definition
        └── public/
            └── css/
                └── warehouse_receiving.css
```

---

## 13. Demo Flow (Interview)

1. **Login as Procurement Executive** (`procurement@example.com`)
2. Open **Sauda Requisition** → New
3. Select Supplier, Department, add 2+ items — observe auto-populate of Item Name and UOM
4. Save → Submit → state moves to **Pending Approval**
5. **Login as Sourcing Head** (`sourcing@example.com`)
6. Open the requisition → **Approve** → state moves to **Approved**
7. **Login as MIS Executive** (`mis@example.com`)
8. Open approved requisition → **Create Purchase Order** → ERPNext PO created automatically
9. Attempt Create PO again → blocked: "Purchase Order already exists"
10. **Login as Warehouse Executive** (`warehouse@example.com`)
11. Open **Warehouse Receiving** from the sidebar
12. Select the PO → pending items table loads with progress bars
13. Scan Item Code → item details populate with ordered/received/pending quantities
14. Enter received quantity (partial) → Add to Receipt
15. Attempt over-receipt → server blocks: "Only X units remain"
16. Click **Complete GRN** → Purchase Receipt created → quantities updated
17. Return to Warehouse Receiving → pending quantities correctly reduced
18. Complete remaining items → GRN → Sauda Requisition auto-marked **Completed**
19. Open Frappe Console → call `dehaat_procurement.api.sap_api.get_po_for_sap` → show JSON

---

## Demo Users

| Email | Role |
|---|---|
| `procurement@example.com` | Procurement Executive |
| `sourcing@example.com` | Sourcing Head |
| `mis@example.com` | MIS Executive |
| `warehouse@example.com` | Warehouse Executive |

---

## Design Decisions

See [`docs/IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) for full technical design rationale.
