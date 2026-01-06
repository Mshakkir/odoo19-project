from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    source_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Source Warehouse',
        help='The warehouse from which this delivery order was created',
        readonly=True,
        copy=False
    )

    def action_confirm(self):
        """
        Override to handle batch confirmation when multiple warehouses are involved
        Confirm pickings one at a time to avoid singleton errors in other modules
        """
        # Check if we're in multi-warehouse mode and have multiple pickings
        if self.env.context.get('multi_warehouse_separate_confirm') and len(self) > 1:
            # Confirm each picking individually
            for picking in self:
                super(StockPicking, picking).action_confirm()
            return True
        else:
            # Standard confirmation
            return super(StockPicking, self).action_confirm()


class StockMove(models.Model):
    _inherit = 'stock.move'

    source_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Source Warehouse',
        help='The warehouse from which this move was initiated',
        readonly=True,
        copy=False
    )

    def _assign_picking(self):
        """Override to set source warehouse on picking when creating it"""
        result = super()._assign_picking()

        # After picking is assigned, update it with source warehouse
        for move in self:
            if move.picking_id and move.source_warehouse_id and not move.picking_id.source_warehouse_id:
                move.picking_id.source_warehouse_id = move.source_warehouse_id

        return result


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom,
                               location_dest_id, name, origin, company_id, values):
        """Override to capture source warehouse in picking"""
        move_values = super()._get_stock_move_values(
            product_id, product_qty, product_uom,
            location_dest_id, name, origin, company_id, values
        )

        # Store source warehouse ID to be used when creating picking
        if values.get('source_warehouse_id'):
            move_values['source_warehouse_id'] = values['source_warehouse_id']

        return move_values

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        """Override to preserve source warehouse in pushed moves"""
        values = super()._push_prepare_move_copy_values(move_to_copy, new_date)

        if hasattr(move_to_copy, 'source_warehouse_id') and move_to_copy.source_warehouse_id:
            values['source_warehouse_id'] = move_to_copy.source_warehouse_id.id

        return values