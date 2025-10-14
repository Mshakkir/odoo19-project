from odoo import models, fields, api

class AccountTaxReportWizard(models.TransientModel):
    _inherit = 'account.tax.report.wizard'


    detail_line_ids = fields.One2many('tax.report.detail.line', 'wizard_id', string='Tax Summary Lines')

    def compute_tax_summary(self):
        self.ensure_one()
        TaxLine = self.env['tax.report.detail.line']

        # Clear previous lines
        self.detail_line_ids.unlink()

        # Sales
        moves = self.env['account.move'].search([
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('move_type', 'in', ['out_invoice', 'out_refund'])
        ])
        tax_summary = {}
        for move in moves:
            for line in move.line_ids.tax_ids:
                key = (line.id, 'sale')
                if key not in tax_summary:
                    tax_summary[key] = {'base': 0.0, 'tax': 0.0, 'moves': []}
                tax_summary[key]['base'] += line.base
                tax_summary[key]['tax'] += line.amount
                tax_summary[key]['moves'].append(move.id)

        # Purchases
        moves = self.env['account.move'].search([
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('move_type', 'in', ['in_invoice', 'in_refund'])
        ])
        for move in moves:
            for line in move.line_ids.tax_ids:
                key = (line.id, 'purchase')
                if key not in tax_summary:
                    tax_summary[key] = {'base': 0.0, 'tax': 0.0, 'moves': []}
                tax_summary[key]['base'] += line.base
                tax_summary[key]['tax'] += line.amount
                tax_summary[key]['moves'].append(move.id)

        # Create summary lines
        for (tax_id, type_), vals in tax_summary.items():
            TaxLine.create({
                'wizard_id': self.id,
                'type': type_,
                'tax_id': tax_id,
                'base_amount': vals['base'],
                'tax_amount': vals['tax'],
                'move_ids': [(6, 0, vals['moves'])],
            })

    def open_tax_report_details(self):
        self.compute_tax_summary()
        return {
            'name': 'Tax Report Summary',
            'type': 'ir.actions.act_window',
            'res_model': 'tax.report.detail.line',
            'view_mode': 'list,form',
            'target': 'current',
            'context': {'default_wizard_id': self.id},
            'domain': [('wizard_id', '=', self.id)],
        }

