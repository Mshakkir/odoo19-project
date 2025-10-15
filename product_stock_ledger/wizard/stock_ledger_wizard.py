from odoo import fields, models, api, _
from odoo.exceptions import UserError

class StockLedgerWizard(models.TransientModel):
    _name = "product.stock.ledger.wizard"
    _description = "Product Stock Ledger Wizard"

    product_id = fields.Many2one('product.product', string='Product', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False)
    date_from = fields.Datetime(string='Date From', required=True, default=fields.Datetime.now)
    date_to = fields.Datetime(string='Date To', required=True, default=fields.Datetime.now)

    def action_print_report(self):
        data = {
            'product_id': self.product_id.id,
            'warehouse_id': self.warehouse_id.id if self.warehouse_id else False,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return self.env.ref('product_stock_ledger.action_report_product_stock_ledger').report_action(self, data=data)

    def action_view_moves(self):
        """Open stock.move records matching the wizard criteria in a new window/modal."""
        self.ensure_one()
        domain = [
            ('product_id', '=', self.product_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'done'),
        ]

        if self.warehouse_id and self.warehouse_id.view_location_id:
            loc_ids = self.env['stock.location'].search([
                ('id', 'child_of', self.warehouse_id.view_location_id.id)
            ]).ids
            if loc_ids:
                domain = [
                    ('product_id', '=', self.product_id.id),
                    ('date', '>=', self.date_from),
                    ('date', '<=', self.date_to),
                    ('state', '=', 'done'),
                    '|',
                    ('location_id', 'in', loc_ids),
                    ('location_dest_id', 'in', loc_ids),
                ]

        # ✅ FIXED view_mode (use 'list' instead of 'tree')
        action = {
            'name': _('Stock Moves for %s') % (self.product_id.display_name,),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],  # ✅ explicitly define
            'domain': domain,
            'context': dict(self.env.context, search_default_groupby_date=False),
            'target': 'current',  # better UX; 'new' may cause overlay rendering issues
        }
        return action
