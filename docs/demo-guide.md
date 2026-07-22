# Demonstration & Interview Walkthrough Guide

## Recommended 8-10 Minute Demonstration Script

### Step 1: System Overview & Architecture (1 min)
- Introduce the app `dehaat_procurement` and module `Procurement Management`.
- Explain how standard ERPNext masters (`Supplier`, `Item`, `Purchase Order`, `Purchase Receipt`) integrate seamlessly with custom workflows.

### Step 2: Sauda Requisition Creation (2 mins)
1. Log in as **Procurement Executive** (`procurement@example.com`).
2. Open **Sauda Requisition** -> Click **New**.
3. Select Supplier (`ABC Agri`), Department (`Operations`).
4. In **Item Details**, select `ITEM-001` (Qty: 100, Rate: 50) and `ITEM-002` (Qty: 50, Rate: 100).
5. Show auto-population of Item Name and UOM upon item selection.
6. Click **Save** (State = `Draft`).
7. Click **Submit** (State updates to `Pending Approval`).
8. Demonstrate role boundary: Note that Procurement Executive cannot see any Approve/Reject buttons.

### Step 3: Sourcing Head Approval (2 mins)
1. Log in as **Sourcing Head** (`sourcing@example.com`).
2. Open the submitted Sauda Requisition.
3. Review line items and pricing.
4. Click Workflow Action -> **Approve** (State updates to `Approved`).

### Step 4: Purchase Order Generation & Idempotency (2 mins)
1. Log in as **MIS Executive** (`mis@example.com`).
2. Open the Approved Sauda Requisition.
3. Click Action -> **Create Purchase Order**.
4. Show automatic navigation to the created ERPNext **Purchase Order**.
5. Demonstrate **Duplicate PO Protection**: Return to the requisition and attempt to trigger PO creation again — show the validation warning.

### Step 5: Warehouse Receiving & Barcode Scanning (2 mins)
1. Log in as **Warehouse Executive** (`warehouse@example.com`).
2. Open Desk -> **Warehouse Receiving** page.
3. Select the generated Purchase Order from dropdown.
4. Show **Pending Items** table with progress bars (100% pending).
5. Scan/enter `ITEM-001` -> Received Qty: `60` -> Click **Add to Receipt**.
6. Demonstrate **Over-Receipt Guard**: Enter Received Qty: `50` for remaining 40 units -> Show validation error "Cannot receive 50 units. Only 40 units remain."
7. Enter valid Qty: `40` -> Click **Add to Receipt**.
8. Click **Complete GRN**.
9. Show generated ERPNext **Purchase Receipt** and verify that Sauda Requisition workflow state automatically updates to **Completed**.

### Step 6: SAP API Demonstration (1 min)
1. Call API method via Frappe Console / Postman:
   `dehaat_procurement.api.sap_api.get_po_for_sap(purchase_order="PO-2026-00001")`
2. Show structured JSON payload containing header, item line rates, quantities, and traceability metadata.
