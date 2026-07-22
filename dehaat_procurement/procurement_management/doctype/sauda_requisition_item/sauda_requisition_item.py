# Copyright (c) 2026, DeHaat Engineering
# License: MIT

import frappe
from frappe.model.document import Document


class SaudaRequisitionItem(Document):
    """Child table row — no independent controller logic needed.
    All validation happens in the parent SaudaRequisition.validate()."""
    pass
