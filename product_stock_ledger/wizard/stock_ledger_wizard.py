# product_stock_ledger/wizard/stock_ledger_wizard.py
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
