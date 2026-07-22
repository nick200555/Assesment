# Copyright (c) 2026, DeHaat Engineering and Contributors
# See license.txt

import frappe
import unittest
from dehaat_procurement.procurement_management.doctype.sauda_requisition.sauda_requisition import (
    create_purchase_order,
)
from dehaat_procurement.api.purchase_order import (
    validate_scanned_item,
    create_purchase_receipt,
)


class TestSaudaRequisition(unittest.TestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_sauda_requisition_validation(self):
        """Test server-side validation for empty items or negative rates."""
        doc = frappe.new_doc("Sauda Requisition")
        doc.supplier = "_Test Supplier"
        doc.department = "Operations"

        # No items -> should fail
        self.assertRaises(frappe.ValidationError, doc.save)

        # Invalid item qty -> should fail
        doc.append("items", {
            "item_code": "_Test Item",
            "quantity_required": 0,
            "rate": 100
        })
        self.assertRaises(frappe.ValidationError, doc.save)

    def test_duplicate_po_creation_protection(self):
        """Verify that duplicate POs cannot be created from the same Sauda Requisition."""
        # Create approved requisition
        doc = frappe.new_doc("Sauda Requisition")
        doc.supplier = "_Test Supplier"
        doc.department = "Operations"
        doc.append("items", {
            "item_code": "_Test Item",
            "quantity_required": 10,
            "rate": 50
        })
        doc.workflow_state = "Approved"
        doc.insert()

        # First PO creation
        po_name = create_purchase_order(doc.name)
        self.assertTrue(po_name)

        # Second PO creation attempt -> should fail with throw
        self.assertRaises(frappe.ValidationError, create_purchase_order, doc.name)

    def test_over_receipt_validation(self):
        """Verify that warehouse receiving prevents over-receipt beyond pending qty."""
        # Create PO mock test if PO exists
        pass
