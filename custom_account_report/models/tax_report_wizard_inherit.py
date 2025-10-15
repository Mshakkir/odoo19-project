from odoo import models, fields, api

class AccountTaxReportWizard(models.TransientModel):
    _inherit = 'account.tax.report.wizard'

    detail_line_ids = fields.One2many('tax.report.detail.line', 'wizard_id', string='Tax Summary Lines')

    def compute_tax_summary(self):
        self.ensure_one()
        TaxLine = self.env['tax.report.detail.line']
        self.detail_line_ids.unlink()

        tax_summary = {}

        # Define date domain
        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted')
        ]

        # 1️⃣ Sales
        sale_moves = self.env['account.move'].search(domain + [('move_type', 'in', ['out_invoice', 'out_refund'])])
        for move in sale_moves:
            for line in move.invoice_line_ids:
                for tax in line.tax_ids:
                    key = (tax.id, 'sale')
                    if key not in tax_summary:
                        tax_summary[key] = {'base': 0.0, 'tax': 0.0, 'moves': []}
                    base_amount = line.price_subtotal
                    tax_amount = tax.amount / 100 * base_amount if tax.amount_type == 'percent' else tax.amount
                    tax_summary[key]['base'] += base_amount
                    tax_summary[key]['tax'] += tax_amount
                    tax_summary[key]['moves'].append(move.id)

        # 2️⃣ Purchases
        purchase_moves = self.env['account.move'].search(domain + [('move_type', 'in', ['in_invoice', 'in_refund'])])
        for move in purchase_moves:
            for line in move.invoice_line_ids:
                for tax in line.tax_ids:
                    key = (tax.id, 'purchase')
                    if key not in tax_summary:
                        tax_summary[key] = {'base': 0.0, 'tax': 0.0, 'moves': []}
                    base_amount = line.price_subtotal
                    tax_amount = tax.amount / 100 * base_amount if tax.amount_type == 'percent' else tax.amount
                    tax_summary[key]['base'] += base_amount
                    tax_summary[key]['tax'] += tax_amount
                    tax_summary[key]['moves'].append(move.id)

        # 3️⃣ Create detail lines
        sale_total = 0.0
        purchase_total = 0.0

        for (tax_id, type_), vals in tax_summary.items():
            TaxLine.create({
                'wizard_id': self.id,
                'type': type_,
                'tax_id': tax_id,
                'base_amount': vals['base'],
                'tax_amount': vals['tax'],
                'move_ids': [(6, 0, vals['moves'])],
            })
            if type_ == 'sale':
                sale_total += vals['tax']
            elif type_ == 'purchase':
                purchase_total += vals['tax']

        # 4️⃣ Add total rows (display only)
        # Sale total row
        if sale_total:
            TaxLine.create({
                'wizard_id': self.id,
                'type': 'sale',
                'tax_name': 'Total Sales',
                'base_amount': 0.0,
                'tax_amount': sale_total,
            })

        # Purchase total row
        if purchase_total:
            TaxLine.create({
                'wizard_id': self.id,
                'type': 'purchase',
                'tax_name': 'Total Purchases',
                'base_amount': 0.0,
                'tax_amount': purchase_total,
            })

        # Net VAT Due row
        TaxLine.create({
            'wizard_id': self.id,
            'type': 'sale',
            'tax_name': 'Net VAT Due',
            'base_amount': 0.0,
            'tax_amount': sale_total - purchase_total,
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
