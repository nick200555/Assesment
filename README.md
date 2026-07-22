# DeHaat Procurement Workflow & Warehouse Receiving

## Assessment Objective
Translate DeHaat business procurement requirements into an enterprise Frappe/ERPNext custom application featuring automated requisition approval workflows, role-based security, ERPNext integration, SAP data transfer APIs, and a custom scanning-enabled Warehouse Receiving frontend page.

## Business Scenario
1. **Sauda Requisition**: Created by Procurement Executive.
2. **Sourcing Head Approval**: Sourcing Head approves or rejects requisition.
3. **Purchase Order Creation**: MIS Executive or authorized automated process converts Approved requisition to ERPNext Purchase Order without manual data re-entry.
4. **Warehouse Receiving & Inventory Scanning**: Warehouse Executive scans items, enters received quantities, and verifies pending balances via custom Frappe Page.
5. **Goods Receipt (GRN)**: Submits ERPNext Purchase Receipt and auto-completes the Sauda Requisition upon full quantity receipt.

## Architecture & Process Flow
```
Sauda Requisition (Draft)
       │
       ▼ [Submit - Procurement Executive]
Pending Approval
       │
       ├────► Rejected [Sourcing Head]
       │
       ▼ [Approve - Sourcing Head]
Approved Requisition
       │
       ▼ [Create PO - MIS Executive / Server API]
Purchase Order (PO Created)
       │
       ▼ [Scan & Receive - Warehouse Executive via Custom Page]
Goods Receipt / Purchase Receipt (GRN)
       │
       ▼ [All Items Received]
Completed
```

## Technology Stack
- **Framework**: Frappe Framework (v15)
- **ERP Integration**: ERPNext (v15)
- **Languages**: Python 3.10+, JavaScript (ES6), HTML5, CSS3
- **Database**: MariaDB 10.6+

## Roles & Permissions
- **Procurement Executive**: Creates, edits, and submits Sauda Requisitions. Cannot approve.
- **Sourcing Head**: Approves or rejects requisitions in `Pending Approval` state.
- **MIS Executive**: Triggers Purchase Order creation from Approved requisitions; accesses SAP data APIs.
- **Warehouse Executive**: Accesses custom Warehouse Receiving page to scan items and generate Purchase Receipts.

## Custom DocTypes
- **Sauda Requisition**: Main document tracking requisition headers, supplier, department, workflow status, and linked Purchase Order.
- **Sauda Requisition Item**: Child table storing item code, item name, requested quantity, UOM, and rate.

## Standard ERPNext DocTypes Reused
- `Supplier`, `Item`, `Department`, `UOM`, `Warehouse`, `User`
- `Purchase Order` (with custom field `custom_sauda_requisition` for full bi-directional traceability)
- `Purchase Receipt` (GRN execution)

## Key Validation & Protection Mechanisms
- **Server-Side Validation**: All quantity, item existence, and rate constraints are strictly enforced in Python controllers.
- **Duplicate PO Guard**: Server-side idempotency check prevents raising multiple Purchase Orders from a single requisition.
- **Over-Receipt Guard**: Server recalculates remaining/pending quantities and rejects receipts exceeding ordered limits.
- **Scan Validation**: Hardware scanner/barcode inputs are resolved to valid PO line items before adding to session.

## SAP API Endpoints
Whitelisted integration endpoints in `dehaat_procurement.api.sap_api`:
- `get_po_for_sap(purchase_order)`: Structured JSON payload for outbound PO sync to SAP.
- `get_grn_for_sap(purchase_receipt)`: Structured JSON payload for outbound GRN sync to SAP.
- `get_pending_pos_for_sap()`: Batch list of open POs pending SAP ingestion.

## Installation Instructions
1. Copy/symlink `dehaat_procurement` into `frappe-bench/apps/dehaat_procurement`.
2. Install python package:
   ```bash
   bench pip install -e apps/dehaat_procurement
   ```
3. Install app on site:
   ```bash
   bench --site <site_name> install-app dehaat_procurement
   bench --site <site_name> migrate
   ```
4. Build assets & clear cache:
   ```bash
   bench build --app dehaat_procurement
   bench clear-cache
   ```

## Fixtures Exported
- `Role`: Roles created for assessment.
- `Workflow State`, `Workflow Action Master`, `Workflow`: Complete 6-state 5-action workflow configuration.
- `Custom Field`: Traceability field on Purchase Order.
- `Workspace`: Desk shortcuts and module hub.
