# Design Decisions & Architecture Rationale

## 1. Why Sauda Requisition is a Custom DocType
`Sauda Requisition` represents DeHaat's domain-specific procurement requisition process. While ERPNext has a standard `Material Request`, DeHaat's business workflow requires specific header attributes (e.g. Sourcing Head approval chain, direct supplier pricing negotiation) that are distinct from internal material transfers. Building a lightweight, custom DocType guarantees zero bloat and clean workflow state management.

## 2. Standard ERPNext Master Reuse
We deliberately reused standard ERPNext entities (`Supplier`, `Item`, `Department`, `UOM`, `Warehouse`, `User`) rather than creating shadow custom DocTypes. This ensures:
- Full compatibility with ERPNext accounting, inventory valuation, and stock ledger.
- Zero duplicate data entry for vendors and catalog items.

## 3. Standard ERPNext Purchase Order & Purchase Receipt Reuse
Instead of reinventing custom PO or GRN tables:
- **Purchase Order**: Standard ERPNext `Purchase Order` is created programmatically via `create_purchase_order()`.
- **Purchase Receipt**: Standard ERPNext `Purchase Receipt` is generated upon GRN completion from the custom frontend.
This maintains full ledger integration (General Ledger & Stock Ledger) while providing a custom, high-efficiency frontend experience.

## 4. Custom Warehouse Receiving Page vs Standard Purchase Receipt Form
Standard ERPNext forms are built for office back-office entry. Warehouse operators require a simplified, touch/scanner-friendly interface focused on high-speed scanning, batch entry, and instant visual validation of ordered vs received items.
The custom Frappe Page (`warehouse-receiving`) provides:
- Single-page application UX with keyboard barcode scanner listener (`Enter` key auto-commit).
- Real-time progress bars for each line item.
- Temporary receiving session buffer to bundle multiple scans before single-click GRN submission.

## 5. Server-Side Validation Authority
All critical business rules (over-receipt checks, duplicate PO protection, role authorization, state checks) are enforced in Python controllers and server APIs (`sauda_requisition.py`, `purchase_order.py`, `sap_api.py`). Browser JavaScript is treated purely as UX enhancement.

## 6. Duplicate PO Prevention Strategy
Idempotency is guaranteed by storing `custom_sauda_requisition` on the Purchase Order and `purchase_order` on the Sauda Requisition. Before initiating PO creation, the server queries both fields. If a valid PO is already attached, execution halts with a meaningful validation error message.

## 7. Role & Workflow Design
The assessment document specifies distinct roles:
- `Procurement Executive`: Creator/Submitter.
- `Sourcing Head`: Approver/Rejecter.
- `MIS Executive`: Authorized PO creator (separating requisition approval from financial purchasing execution).
- `Warehouse Executive`: Receiver.

The workflow transitions are strictly mapped to these roles to ensure zero privilege escalation across document lifecycle states.
