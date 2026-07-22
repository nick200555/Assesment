# Technical Implementation Notes

## Architecture Decisions

### Why a Custom DocType for Sauda Requisition
ERPNext's built-in `Material Request` is designed for internal warehouse transfers. DeHaat's procurement process involves external supplier quoting, approval chains, and direct PO generation — making a clean, dedicated custom DocType the right choice to avoid polluting standard ERPNext processes.

### Standard ERPNext Masters Reused
`Supplier`, `Item`, `Department`, `UOM`, `Warehouse`, `User` are all reused as-is. This ensures full ERPNext master data compatibility, avoids data duplication, and makes reports and dashboards automatically include our data.

### Why Purchase Order and Purchase Receipt Are Not Replaced
Replacing standard ERPNext financial documents would break the stock ledger, general ledger entries, accounts payable, and all related ERPNext reports. The correct approach is to *create* these documents programmatically and leverage their full ERPNext accounting integration.

---

## Workflow Design

### State Machine
```
Draft ──[Submit: Procurement Executive]──► Pending Approval
Pending Approval ──[Approve: Sourcing Head]──► Approved
Pending Approval ──[Reject: Sourcing Head]──► Rejected
Approved ──[Create Purchase Order: MIS Executive]──► PO Created
PO Created ──[Complete GRN: Warehouse Executive]──► Completed
```

### workflow_state_field
The Workflow engine writes the current state name to the `workflow_state` (Data) field on `Sauda Requisition`. This is declared as `workflow_state_field` in `workflow.json`.

### Terminal State (Completed)
Frappe v15 requires `allow_edit` to be non-empty on all Workflow States. The `Completed` state uses `System Manager` — the correct Frappe convention for locked terminal states. No other role can transition out of Completed.

---

## Purchase Order Creation

### Idempotency
Before creating any PO:
1. Check `sr.purchase_order` — if set, throw "PO already exists"
2. Verify `sr.workflow_state == "Approved"`
3. Verify the PO document actually exists in DB (not just the field)

### Traceability
A custom field `custom_sauda_requisition` (Link → Sauda Requisition) is added to the standard `Purchase Order` DocType via a `Custom Field` fixture. This enables bidirectional lookup: SR → PO and PO → SR.

---

## Warehouse Receiving Design

### Why a Custom Page Instead of Standard Purchase Receipt Form
The standard Purchase Receipt form is designed for office back-office entry with full accounting context. Warehouse operators need a simplified, fast, scanner-optimised interface. The custom Frappe Page provides a single-screen scanning flow.

### Barcode Resolution
Scan input is first checked against the `Item Barcode` child table. If no barcode match is found, the input is treated as a direct Item Code. This supports both barcode-labelled and manually entered items.

### Session Buffer
Scanned items are held in a browser-side JavaScript array before GRN submission. On "Complete GRN", all items are sent to `create_purchase_receipt()` in a single server call. The server re-validates all quantities independently of the client-side calculations.

### Partial Receiving
`get_po_receiving_status()` queries the live Purchase Order document for `received_qty` per line. ERPNext maintains this aggregate automatically. The custom app never stores its own received quantity state — it always defers to the source-of-truth in ERPNext.

---

## Security

### Server-Side Authority
All business rules (over-receipt, role checks, duplicate PO, state validation) are enforced in Python. JavaScript is used purely for UX.

### Permission Helpers
- `get_permission_query_conditions()`: filters Sauda Requisition list view so Procurement Executives only see their own documents
- `has_permission()`: document-level access control
- `_assert_role()`: inline role check inside whitelisted API methods

### No Guest Access
All whitelisted methods require authenticated sessions. `allow_guest=True` is never used.

### No Hard-coded Credentials
The application contains no passwords, API keys, database credentials, or SAP connection strings. SAP connectivity must be configured via environment variables at deployment time.

---

## Completion Logic

The Sauda Requisition is marked Completed when:
1. A Purchase Receipt is submitted (`on_purchase_receipt_submit` hook fires)
2. The hook reloads the linked Purchase Order
3. It checks that `received_qty >= qty` for ALL line items
4. Only then does it set `workflow_state = "Completed"` on the Sauda Requisition

Partial GRNs do not trigger completion.

---

## Assumptions

1. SAP connectivity specifications (endpoint URL, authentication) are not provided — the API returns structured JSON payloads for integration by a middleware layer.
2. The ERPNext `Company` must be set up (via Setup Wizard) before the app is fully usable.
3. Item batch tracking is optional — if an Item has `has_batch_no = 1`, the warehouse operator must provide a batch number in the receiving form.
