# product_stock_ledger/wizard/stock_ledger_wizard.py
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import urllib.parse

class StockLedgerWizard(models.TransientModel):
    _name = "product.stock.ledger.wizard"
    _description = "Product Stock Ledger Wizard"

    product_id = fields.Many2one('product.product', string='Product', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False)
    date_from = fields.Datetime(string='Date From', required=True, default=fields.Datetime.now)
    date_to = fields.Datetime(string='Date To', required=True, default=fields.Datetime.now)

    def action_print_report(self):
        # Build URL params safely
        params = {
            'product_id': self.product_id.id,
            'date_from': fields.Datetime.to_string(self.date_from) if self.date_from else '',
            'date_to': fields.Datetime.to_string(self.date_to) if self.date_to else '',
        }
        if self.warehouse_id:
            params['warehouse_id'] = self.warehouse_id.id

        base = '/product_stock_ledger/ledger'
        url = base + '?' + urllib.parse.urlencode(params)

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
