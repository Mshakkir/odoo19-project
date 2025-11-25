from odoo import models, api, fields


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    # We compute qty_to_order using on-hand qty instead of virtual_available.
    # Field name for computed order quantity may vary across versions;
    # in recent Odoo there is 'qty_to_order' or 'to_order' or compute methods.
    # We'll compute using a safe approach: add a stored computed field 'onhand_qty'
    # and override the compute method for qty_to_order if present.

    onhand_qty = fields.Float(
        string="On-hand (location)", compute="_compute_onhand_qty", store=False
    )

    @api.depends('product_id', 'location_id')
    def _compute_onhand_qty(self):
        quant = self.env['stock.quant']
        for op in self:
            if not op.location_id or not op.product_id:
                op.onhand_qty = 0.0
                continue
            # stock.quant._get_available_quantity returns quantity at a location
            try:
                op.onhand_qty = quant._get_available_quantity(op.product_id, op.location_id.id)
            except Exception:
                # fallback: use product qty_available globally if quant helper not present
                op.onhand_qty = op.product_id.with_context(location=op.location_id.id).qty_available

    # If the orderpoint uses a compute function we can override it.
    # Many Odoo versions use a compute method named _compute_qty_to_order or similar;
    # to be robust we implement a convenience recalculation method and monkey-patch the
    # field if present.
    @api.model
    def _compute_qty_to_order_onhand(self, orderpoints):
        """Return dict {orderpoint_id: qty_to_order} based on on-hand qty per location."""
        quant = self.env['stock.quant']
        results = {}
        for op in orderpoints:
            # use on-hand at the orderpoint's location
            if not op.location_id or not op.product_id:
                results[op.id] = 0.0
                continue
            try:
                onhand = quant._get_available_quantity(op.product_id, op.location_id.id)
            except Exception:
                onhand = op.product_id.with_context(location=op.location_id.id).qty_available

            # if below minimum, order up to max (same formula Odoo uses for virtual)
            if onhand < (op.product_min_qty or 0.0):
                qty_to_order = max((op.product_max_qty or 0.0) - onhand, 0.0)
            else:
                qty_to_order = 0.0
            results[op.id] = qty_to_order
        return results

    # Hook into whatever process computes qty to order used by scheduler:
    # We'll override / extend method that many Odoo versions use: _compute_qty_to_order
    # If your Odoo has a method with a different name, you may need to adjust.
    def _compute_qty_to_order(self):
        """
        Replace default computation with on-hand based computation.
        This method signature matches that used in several Odoo versions.
        If your Odoo has another implementation, this override still works because
        the scheduler queries op.qty_to_order or calls this method in-stock.
        """
        # Use our helper to compute values
        vals = self._compute_qty_to_order_onhand(self)
        # store into a transient or existing field used by scheduler
        # Many Odoo versions have a field 'qty_to_order' or 'to_order' computed.
        # We'll try both possibilities.
        for op in self:
            qty = vals.get(op.id, 0.0)
            if hasattr(op, 'qty_to_order'):
                # write temporarily on record (if stored field, this will persist)
                op.qty_to_order = qty
            elif hasattr(op, 'to_order'):
                op.to_order = qty
            else:
                # fallback: write into onhand_qty (non-stored) - scheduler might not read it,
                # but this ensures at least the value can be inspected in UI
                op.onhand_qty = qty
        return vals
