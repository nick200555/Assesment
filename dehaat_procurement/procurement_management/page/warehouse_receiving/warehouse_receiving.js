// Copyright (c) 2026, DeHaat Engineering
// Warehouse Receiving Page — Main JavaScript Controller
// ─────────────────────────────────────────────────────────────────────────────

frappe.pages["warehouse-receiving"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __("Warehouse Receiving"),
        single_column: true,
    });

    // Inject page styles
    frappe.require("assets/dehaat_procurement/css/warehouse_receiving.css");

    // Mount the app
    new WarehouseReceivingApp(page, wrapper);
};


// ─── Main Application Class ───────────────────────────────────────────────────
class WarehouseReceivingApp {
    constructor(page, wrapper) {
        this.page = page;
        this.wrapper = wrapper;
        this.$body = $(wrapper).find(".page-content");

        // State
        this.selected_po = null;
        this.po_data = null;              // full PO receiving status from server
        this.session_items = [];          // items scanned in current session
        this.default_warehouse = "";

        this._render_ui();
        this._bind_events();
        this._load_default_warehouse();
    }

    // ─── UI Rendering ─────────────────────────────────────────────────────────

    _render_ui() {
        this.$body.html(`
        <div class="wr-container">

            <!-- ═══ SECTION 1: Purchase Order Selection ═══ -->
            <div class="wr-card" id="wr-po-section">
                <div class="wr-card-header">
                    <span class="wr-icon">📋</span>
                    <h3>${__("Purchase Order")}</h3>
                </div>
                <div class="wr-card-body">
                    <div class="wr-row">
                        <div class="wr-field-group" style="flex:2">
                            <label>${__("Select Purchase Order")}</label>
                            <div id="wr-po-input-wrap"></div>
                        </div>
                        <div class="wr-field-group" style="flex:1">
                            <label>${__("Supplier")}</label>
                            <div class="wr-readonly-val" id="wr-supplier">—</div>
                        </div>
                        <div class="wr-field-group" style="flex:1">
                            <label>${__("Status")}</label>
                            <div class="wr-readonly-val" id="wr-po-status">—</div>
                        </div>
                    </div>
                    <div class="wr-row" id="wr-po-info" style="display:none">
                        <div class="wr-badge-row" id="wr-progress-badges"></div>
                    </div>
                </div>
            </div>

            <!-- ═══ SECTION 2: Pending Items ═══ -->
            <div class="wr-card" id="wr-pending-section" style="display:none">
                <div class="wr-card-header">
                    <span class="wr-icon">📦</span>
                    <h3>${__("Pending Items")}</h3>
                </div>
                <div class="wr-card-body">
                    <table class="wr-table" id="wr-pending-table">
                        <thead>
                            <tr>
                                <th>${__("Item Code")}</th>
                                <th>${__("Item Name")}</th>
                                <th>${__("Ordered")}</th>
                                <th>${__("Received")}</th>
                                <th>${__("Pending")}</th>
                                <th>${__("UOM")}</th>
                                <th>${__("Progress")}</th>
                            </tr>
                        </thead>
                        <tbody id="wr-pending-tbody"></tbody>
                    </table>
                </div>
            </div>

            <!-- ═══ SECTION 3: Scanning ═══ -->
            <div class="wr-card" id="wr-scan-section" style="display:none">
                <div class="wr-card-header">
                    <span class="wr-icon">🔍</span>
                    <h3>${__("Scan Item")}</h3>
                    <span class="wr-hint">${__("Scan barcode or type Item Code and press Enter")}</span>
                </div>
                <div class="wr-card-body">
                    <div class="wr-scan-row">
                        <div class="wr-field-group" style="flex:2">
                            <label>${__("Barcode / Item Code")}</label>
                            <input type="text" id="wr-barcode-input"
                                   class="wr-input wr-barcode"
                                   placeholder="${__("Scan or type here...")}"
                                   autocomplete="off" autofocus />
                        </div>
                        <div class="wr-field-group" style="flex:1">
                            <label>${__("Item Name")}</label>
                            <div class="wr-readonly-val" id="wr-scan-item-name">—</div>
                        </div>
                    </div>
                    <div class="wr-scan-row" id="wr-scan-details" style="display:none">
                        <div class="wr-field-group">
                            <label>${__("Ordered")}</label>
                            <div class="wr-readonly-val" id="wr-scan-ordered">—</div>
                        </div>
                        <div class="wr-field-group">
                            <label>${__("Already Received")}</label>
                            <div class="wr-readonly-val" id="wr-scan-received">—</div>
                        </div>
                        <div class="wr-field-group">
                            <label>${__("Pending")}</label>
                            <div class="wr-readonly-val wr-highlight" id="wr-scan-pending">—</div>
                        </div>
                        <div class="wr-field-group">
                            <label>${__("Received Qty")} <span class="wr-required">*</span></label>
                            <input type="number" id="wr-recv-qty" class="wr-input"
                                   min="0.001" step="any" placeholder="0" />
                        </div>
                        <div class="wr-field-group">
                            <label>${__("Batch No")} (${__("optional")})</label>
                            <input type="text" id="wr-batch-no" class="wr-input"
                                   placeholder="${__("e.g. BATCH-001")}" />
                        </div>
                        <div class="wr-field-group">
                            <label>${__("Warehouse")} <span class="wr-required">*</span></label>
                            <div id="wr-warehouse-input-wrap"></div>
                        </div>
                    </div>
                    <div class="wr-scan-actions" id="wr-scan-actions" style="display:none">
                        <button class="wr-btn wr-btn-primary" id="wr-add-btn">
                            ✅ ${__("Add to Receipt")}
                        </button>
                        <button class="wr-btn wr-btn-secondary" id="wr-clear-btn">
                            🗑 ${__("Clear")}
                        </button>
                    </div>
                    <div id="wr-scan-message"></div>
                </div>
            </div>

            <!-- ═══ SECTION 4: Current Session ═══ -->
            <div class="wr-card" id="wr-session-section" style="display:none">
                <div class="wr-card-header">
                    <span class="wr-icon">📝</span>
                    <h3>${__("Current Receiving Session")}</h3>
                </div>
                <div class="wr-card-body">
                    <table class="wr-table" id="wr-session-table">
                        <thead>
                            <tr>
                                <th>${__("Item Code")}</th>
                                <th>${__("Item Name")}</th>
                                <th>${__("Qty to Receive")}</th>
                                <th>${__("Batch No")}</th>
                                <th>${__("Warehouse")}</th>
                                <th>${__("Remove")}</th>
                            </tr>
                        </thead>
                        <tbody id="wr-session-tbody"></tbody>
                    </table>
                    <div class="wr-grn-actions">
                        <button class="wr-btn wr-btn-success" id="wr-grn-btn">
                            🏁 ${__("Complete GRN")}
                        </button>
                    </div>
                </div>
            </div>

        </div>
        `);
    }

    // ─── Event Binding ────────────────────────────────────────────────────────

    _bind_events() {
        // Barcode / Item Code — supports hardware scanner (types + Enter)
        this.$body.on("keydown", "#wr-barcode-input", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                this._handle_scan();
            }
        });

        // Add to session
        this.$body.on("click", "#wr-add-btn", () => this._add_to_session());

        // Clear scan area
        this.$body.on("click", "#wr-clear-btn", () => this._clear_scan());

        // Complete GRN
        this.$body.on("click", "#wr-grn-btn", () => this._complete_grn());

        // Remove row from session
        this.$body.on("click", ".wr-remove-row", (e) => {
            const idx = $(e.currentTarget).data("idx");
            this.session_items.splice(idx, 1);
            this._render_session();
        });
    }

    // ─── PO Selection ─────────────────────────────────────────────────────────

    _render_po_selector() {
        const $wrap = this.$body.find("#wr-po-input-wrap");
        $wrap.html("");

        const field = frappe.ui.form.make_control({
            parent: $wrap[0],
            df: {
                fieldtype: "Link",
                options: "Purchase Order",
                fieldname: "purchase_order",
                placeholder: __("Select Purchase Order..."),
                filters: { docstatus: 1, status: ["not in", ["Closed", "Cancelled"]] },
            },
            render_input: true,
        });
        field.refresh();

        field.$input.on("change", () => {
            const po = field.get_value();
            if (po) {
                this._load_po(po);
            }
        });
    }

    _render_warehouse_selector() {
        const $wrap = this.$body.find("#wr-warehouse-input-wrap");
        $wrap.html("");

        const field = frappe.ui.form.make_control({
            parent: $wrap[0],
            df: {
                fieldtype: "Link",
                options: "Warehouse",
                fieldname: "warehouse",
                placeholder: __("Select Warehouse..."),
                get_query: () => ({ filters: { disabled: 0 } }),
            },
            render_input: true,
        });

        if (this.default_warehouse) {
            field.set_value(this.default_warehouse);
        }
        field.refresh();

        this._warehouse_field = field;
    }

    _load_default_warehouse() {
        frappe.db.get_value("User", frappe.session.user, "name").then(() => {
            frappe.db.get_single_value("Stock Settings", "default_warehouse").then(wh => {
                if (wh) this.default_warehouse = wh;
                this._render_po_selector();
                this._render_warehouse_selector();
            });
        });
    }

    _load_po(po_name) {
        this.selected_po = null;
        this.po_data = null;
        this._show_loading(__("Loading Purchase Order..."));

        frappe.call({
            method: "dehaat_procurement.api.purchase_order.get_po_receiving_status",
            args: { purchase_order: po_name },
            callback: (r) => {
                this._hide_loading();
                if (r.exc || !r.message) {
                    this._show_error(__("Could not load Purchase Order details."));
                    return;
                }
                this.selected_po = po_name;
                this.po_data = r.message;
                this.session_items = [];
                this._render_po_details();
            },
        });
    }

    _render_po_details() {
        const d = this.po_data;

        this.$body.find("#wr-supplier").text(d.supplier_name || d.supplier);
        this.$body.find("#wr-po-status").html(
            `<span class="wr-status-badge wr-status-${(d.status || "").toLowerCase().replace(/\s/g, "-")}">${d.status}</span>`
        );

        if (d.is_completed) {
            this.$body.find("#wr-pending-section").show();
            this._render_pending_table();
            this.$body.find("#wr-scan-section").hide();
            this._show_info(
                __("Purchase Order '{0}' is fully received. No further receiving allowed.", [this.selected_po])
            );
            return;
        }

        this._render_pending_table();
        this.$body.find("#wr-pending-section").show();
        this.$body.find("#wr-scan-section").show();
        this.$body.find("#wr-po-info").show();
        this._render_progress_badges();
    }

    _render_pending_table() {
        const items = (this.po_data && this.po_data.items) || [];
        let rows = "";
        items.forEach(item => {
            const pct = item.ordered_qty > 0
                ? Math.min(100, Math.round((item.received_qty / item.ordered_qty) * 100))
                : 0;
            const bar_color = pct >= 100 ? "#28a745" : pct > 50 ? "#ffc107" : "#007bff";
            rows += `
            <tr class="${item.pending_qty <= 0 ? 'wr-row-done' : ''}">
                <td><strong>${item.item_code}</strong></td>
                <td>${item.item_name}</td>
                <td>${frappe.utils.fmt_money(item.ordered_qty, null, item.uom)}</td>
                <td>${frappe.utils.fmt_money(item.received_qty, null, item.uom)}</td>
                <td><strong>${frappe.utils.fmt_money(item.pending_qty, null, item.uom)}</strong></td>
                <td>${item.uom}</td>
                <td>
                    <div class="wr-progress-bar">
                        <div class="wr-progress-fill" style="width:${pct}%;background:${bar_color}"></div>
                        <span>${pct}%</span>
                    </div>
                </td>
            </tr>`;
        });
        this.$body.find("#wr-pending-tbody").html(rows);
    }

    _render_progress_badges() {
        const items = (this.po_data && this.po_data.items) || [];
        const total = items.length;
        const done = items.filter(i => i.pending_qty <= 0).length;
        this.$body.find("#wr-progress-badges").html(`
            <span class="wr-badge wr-badge-blue">${__("{0} Total Items", [total])}</span>
            <span class="wr-badge wr-badge-green">${__("{0} Fully Received", [done])}</span>
            <span class="wr-badge wr-badge-orange">${__("{0} Pending", [total - done])}</span>
        `);
    }

    // ─── Scan Handling ────────────────────────────────────────────────────────

    _handle_scan() {
        const barcode_input = this.$body.find("#wr-barcode-input").val().trim();
        if (!barcode_input) return;

        if (!this.selected_po) {
            this._show_error(__("Please select a Purchase Order first."));
            return;
        }

        this._hide_scan_details();
        this._show_loading(__("Validating item..."));

        frappe.call({
            method: "dehaat_procurement.api.purchase_order.validate_scanned_item",
            args: {
                purchase_order: this.selected_po,
                barcode: barcode_input,
            },
            callback: (r) => {
                this._hide_loading();
                if (r.exc) return;  // error shown by frappe automatically
                if (!r.message) {
                    this._show_error(__("Item not found in PO."));
                    return;
                }
                this._scanned_item = r.message;
                this._show_scan_details(r.message);
            },
        });
    }

    _show_scan_details(item) {
        this.$body.find("#wr-scan-item-name").text(item.item_name);
        this.$body.find("#wr-scan-ordered").text(`${item.ordered_qty} ${item.uom}`);
        this.$body.find("#wr-scan-received").text(`${item.received_qty} ${item.uom}`);
        this.$body.find("#wr-scan-pending").text(`${item.pending_qty} ${item.uom}`);
        this.$body.find("#wr-recv-qty").val(item.pending_qty).attr("max", item.pending_qty);
        if (item.warehouse) {
            this._warehouse_field && this._warehouse_field.set_value(item.warehouse);
        }
        this.$body.find("#wr-scan-details").show();
        this.$body.find("#wr-scan-actions").show();
        this.$body.find("#wr-recv-qty").focus();
    }

    _hide_scan_details() {
        this._scanned_item = null;
        this.$body.find("#wr-scan-item-name").text("—");
        this.$body.find("#wr-scan-details").hide();
        this.$body.find("#wr-scan-actions").hide();
        this.$body.find("#wr-scan-message").html("");
    }

    // ─── Session Management ───────────────────────────────────────────────────

    _add_to_session() {
        if (!this._scanned_item) {
            this._show_error(__("No item scanned. Please scan an item first."));
            return;
        }

        const qty = parseFloat(this.$body.find("#wr-recv-qty").val());
        const warehouse = this._warehouse_field ? this._warehouse_field.get_value() : "";
        const batch_no = this.$body.find("#wr-batch-no").val().trim();

        // Client-side pre-validation (server will re-validate)
        if (!qty || qty <= 0) {
            this._show_error(__("Received Quantity must be greater than zero."));
            return;
        }
        if (qty > this._scanned_item.pending_qty) {
            this._show_error(
                __("Cannot receive {0} units. Only {1} units remain.", [qty, this._scanned_item.pending_qty])
            );
            return;
        }
        if (!warehouse) {
            this._show_error(__("Please select a Warehouse."));
            return;
        }

        // Check for duplicate in current session
        const existing = this.session_items.findIndex(
            i => i.item_code === this._scanned_item.item_code
        );
        if (existing >= 0) {
            frappe.confirm(
                __("Item '{0}' is already in the session with qty {1}. Add {2} more?", [
                    this._scanned_item.item_code,
                    this.session_items[existing].qty,
                    qty
                ]),
                () => {
                    this.session_items[existing].qty += qty;
                    this._render_session();
                    this._clear_scan();
                    frappe.show_alert({ message: __("Quantity updated."), indicator: "green" });
                }
            );
            return;
        }

        this.session_items.push({
            item_code: this._scanned_item.item_code,
            item_name: this._scanned_item.item_name,
            qty: qty,
            uom: this._scanned_item.uom,
            batch_no: batch_no,
            warehouse: warehouse,
        });

        this._render_session();
        this._clear_scan();
        frappe.show_alert({
            message: __("'{0}' added to receipt.", [this._scanned_item.item_code]),
            indicator: "green"
        }, 3);
    }

    _clear_scan() {
        this.$body.find("#wr-barcode-input").val("").focus();
        this.$body.find("#wr-batch-no").val("");
        this.$body.find("#wr-recv-qty").val("");
        this._hide_scan_details();
    }

    _render_session() {
        if (this.session_items.length === 0) {
            this.$body.find("#wr-session-section").hide();
            return;
        }

        let rows = "";
        this.session_items.forEach((item, idx) => {
            rows += `
            <tr>
                <td><strong>${item.item_code}</strong></td>
                <td>${item.item_name}</td>
                <td>${item.qty} ${item.uom}</td>
                <td>${item.batch_no || "—"}</td>
                <td>${item.warehouse}</td>
                <td>
                    <button class="wr-btn wr-btn-danger wr-remove-row" data-idx="${idx}">✖</button>
                </td>
            </tr>`;
        });

        this.$body.find("#wr-session-tbody").html(rows);
        this.$body.find("#wr-session-section").show();
    }

    // ─── GRN Completion ───────────────────────────────────────────────────────

    _complete_grn() {
        if (!this.session_items.length) {
            this._show_error(__("No items in the receiving session."));
            return;
        }

        frappe.confirm(
            __("Complete GRN for {0} item(s) against PO '{1}'?", [
                this.session_items.length,
                this.selected_po
            ]),
            () => {
                frappe.call({
                    method: "dehaat_procurement.api.purchase_order.create_purchase_receipt",
                    args: {
                        purchase_order: this.selected_po,
                        items: JSON.stringify(this.session_items),
                        warehouse: (this._warehouse_field && this._warehouse_field.get_value()) || "",
                    },
                    freeze: true,
                    freeze_message: __("Creating Goods Receipt..."),
                    callback: (r) => {
                        if (r.exc) return;
                        if (r.message && r.message.purchase_receipt) {
                            frappe.msgprint({
                                message: __("Goods Receipt <strong>{0}</strong> created successfully!", [
                                    r.message.purchase_receipt
                                ]),
                                title: __("GRN Complete"),
                                indicator: "green",
                            });
                            this.session_items = [];
                            this._render_session();
                            // Reload PO status
                            this._load_po(this.selected_po);
                        }
                    },
                });
            }
        );
    }

    // ─── UI Helpers ───────────────────────────────────────────────────────────

    _show_loading(msg) {
        frappe.show_progress(msg || __("Loading..."), 60, 100, msg);
    }

    _hide_loading() {
        frappe.hide_progress();
    }

    _show_error(msg) {
        frappe.show_alert({ message: msg, indicator: "red" }, 5);
    }

    _show_info(msg) {
        this.$body.find("#wr-scan-message").html(
            `<div class="wr-info-banner">${msg}</div>`
        );
    }
}
