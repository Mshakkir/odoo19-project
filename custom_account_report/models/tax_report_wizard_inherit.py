from odoo import models, api

class AccountTaxReportWizard(models.TransientModel):
    _inherit = 'account.tax.report.wizard'

    def open_tax_report_details(self):
        self.ensure_one()

        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),  # sales + purchases
        ]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Tax Report Details',
            'res_model': 'account.move',
            'view_mode': 'list,form',  # Odoo 19: list instead of tree
            'domain': domain,
            'target': 'current',
        }

