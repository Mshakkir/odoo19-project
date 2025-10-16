from odoo import models, fields, api


class AccountTaxReportWizard(models.TransientModel):
    _inherit = 'account.tax.report.wizard'

    detail_line_ids = fields.One2many('tax.report.detail.line', 'wizard_id', string='Tax Summary Lines')

    def compute_tax_summary(self):
        self.ensure_one()
        TaxLine = self.env['tax.report.detail.line']
        self.detail_line_ids.unlink()

        tax_summary = {}
        total_sales_base = 0.0
        total_sales_tax = 0.0
        total_purchase_base = 0.0
        total_purchase_tax = 0.0

        # Define date domain
        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted')
        ]

        sequence = 10

        # 1️⃣ Sales
        sale_moves = self.env['account.move'].search(domain + [('move_type', 'in', ['out_invoice', 'out_refund'])])
        for move in sale_moves:
            for line in move.invoice_line_ids:
                for tax in line.tax_ids:
                    key = (tax.id, 'sale')
                    if key not in tax_summary:
                        tax_summary[key] = {'base': 0.0, 'tax': 0.0, 'moves': [], 'sequence': sequence}
                        sequence += 10
                    base_amount = line.price_subtotal

                    # Calculate actual tax from account.move.line (tax lines)
                    tax_lines = move.line_ids.filtered(
                        lambda l: l.tax_line_id.id == tax.id and l.display_type == 'tax'
                    )
                    tax_amount = sum(tax_lines.mapped('balance')) * (-1 if move.move_type == 'out_invoice' else 1)

                    tax_summary[key]['base'] += base_amount
                    tax_summary[key]['tax'] += tax_amount
                    tax_summary[key]['moves'].append(move.id)

        # Create sales tax lines
        for (tax_id, type_), vals in tax_summary.items():
            if type_ == 'sale':
                TaxLine.create({
                    'wizard_id': self.id,
                    'type': type_,
                    'tax_id': tax_id,
                    'tax_name': self.env['account.tax'].browse(tax_id).name,
                    'base_amount': vals['base'],
                    'tax_amount': vals['tax'],
                    'move_ids': [(6, 0, vals['moves'])],
                    'is_summary_row': False,
                    'sequence': vals['sequence'],
                })
                total_sales_base += vals['base']
                total_sales_tax += vals['tax']

        # Add Total Sales Summary Row
        TaxLine.create({
            'wizard_id': self.id,
            'type': 'sale',
            'tax_name': 'Total Sales',
            'base_amount': total_sales_base,
            'tax_amount': total_sales_tax,
            'is_summary_row': True,
            'sequence': sequence,
        })
        sequence += 10

        # 2️⃣ Purchases
        purchase_moves = self.env['account.move'].search(domain + [('move_type', 'in', ['in_invoice', 'in_refund'])])
        for move in purchase_moves:
            for line in move.invoice_line_ids:
                for tax in line.tax_ids:
                    key = (tax.id, 'purchase')
                    if key not in tax_summary:
                        tax_summary[key] = {'base': 0.0, 'tax': 0.0, 'moves': [], 'sequence': sequence}
                        sequence += 10
                    base_amount = line.price_subtotal

                    # Calculate actual tax from account.move.line (tax lines)
                    tax_lines = move.line_ids.filtered(
                        lambda l: l.tax_line_id.id == tax.id and l.display_type == 'tax'
                    )
                    tax_amount = sum(tax_lines.mapped('balance')) * (1 if move.move_type == 'in_invoice' else -1)

                    tax_summary[key]['base'] += base_amount
                    tax_summary[key]['tax'] += tax_amount
                    tax_summary[key]['moves'].append(move.id)

        # Create purchase tax lines
        for (tax_id, type_), vals in tax_summary.items():
            if type_ == 'purchase':
                TaxLine.create({
                    'wizard_id': self.id,
                    'type': type_,
                    'tax_id': tax_id,
                    'tax_name': self.env['account.tax'].browse(tax_id).name,
                    'base_amount': vals['base'],
                    'tax_amount': vals['tax'],
                    'move_ids': [(6, 0, vals['moves'])],
                    'is_summary_row': False,
                    'sequence': vals['sequence'],
                })
                total_purchase_base += vals['base']
                total_purchase_tax += vals['tax']

        # Add Total Purchases Summary Row
        TaxLine.create({
            'wizard_id': self.id,
            'type': 'purchase',
            'tax_name': 'Total Purchases',
            'base_amount': total_purchase_base,
            'tax_amount': total_purchase_tax,
            'is_summary_row': True,
            'sequence': sequence,
        })
        sequence += 10

        # Add Net VAT Due Summary Row
        net_vat_due = total_sales_tax - total_purchase_tax
        TaxLine.create({
            'wizard_id': self.id,
            'tax_name': 'Net VAT Due',
            'base_amount': 0.0,
            'tax_amount': net_vat_due,
            'is_summary_row': True,
            'sequence': sequence,
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