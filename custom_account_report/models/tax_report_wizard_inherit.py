from odoo import models, api

class AccountTaxReportWizard(models.TransientModel):
    _inherit = 'account.tax.report.wizard'

    @api.multi
    def open_tax_report_details(self):
        """Open account.move list view filtered by wizard dates."""
        self.ensure_one()

        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('move_type', 'in', ['out_invoice', 'out_refund']),  # sales invoices; adjust if you want purchases too
        ]

        # Build the action dict for list view
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tax Report Details',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': domain,
            'target': 'current',
        }
