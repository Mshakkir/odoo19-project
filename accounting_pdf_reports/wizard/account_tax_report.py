# from odoo import models, api, fields
# from datetime import date
#
#
# class AccountTaxReport(models.TransientModel):
#     _name = 'account.tax.report.wizard'
#     _inherit = "account.common.report"
#     _description = 'Tax Report'
#
#     date_from = fields.Date(
#         string='Date From', required=True,
#         default=lambda self: fields.Date.to_string(date.today().replace(day=1))
#     )
#     date_to = fields.Date(
#         string='Date To', required=True,
#         default=lambda self: fields.Date.to_string(date.today())
#     )
#
#     def _print_report(self, data):
#         return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(self, data=data)
from odoo import models, api, fields
from datetime import date


class AccountTaxReport(models.TransientModel):
    _name = 'account.tax.report.wizard'
    _inherit = "account.common.report"
    _description = 'Tax Report'

    date_from = fields.Date(
        string='Date From', required=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1))
    )
    date_to = fields.Date(
        string='Date To', required=True,
        default=lambda self: fields.Date.to_string(date.today())
    )

    # 🔹 NEW: Warehouse filter
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    def _print_report(self, data):
        data = {
            'form': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'target_move': self.target_move,
                'warehouse_id': self.warehouse_id.id if self.warehouse_id else False,
            }
        }
        return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(self, data=data)
