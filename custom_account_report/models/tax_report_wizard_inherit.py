from odoo import models, fields, api

class AccountTaxReportWizard(models.TransientModel):
    _inherit = 'account.tax.report.wizard'

    # Tax summary lines
    detail_line_ids = fields.One2many(
        'tax.report.detail.line', 'wizard_id', string='Tax Summary Lines'
    )

    # Totals fields
    total_sale = fields.Monetary(compute='_compute_totals', store=True)
    total_purchase = fields.Monetary(compute='_compute_totals', store=True)
    net_vat_due = fields.Monetary(compute='_compute_totals', store=True)

    @api.depends('detail_line_ids.base_amount', 'detail_line_ids.type')
    def _compute_totals(self):
        for record in self:
            lines = record.detail_line_ids.filtered(lambda l: l.line_type == 'line')
            record.total_sale = sum(lines.filtered(lambda l: l.type == 'sale').mapped('base_amount'))
            record.total_purchase = sum(lines.filtered(lambda l: l.type == 'purchase').mapped('base_amount'))
            record.net_vat_due = record.total_sale - record.total_purchase

    def compute_tax_summary(self):
        self.ensure_one()
        TaxLine = self.env['tax.report.detail.line']
        # Remove previous lines
        self.detail_line_ids.unlink()

        tax_summary = {}

        # Define date domain
        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted')
        ]

        # 1️⃣ Sales invoices
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

        # 2️⃣ Purchase invoices
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

        # 3️⃣ Create normal tax lines
        for (tax_id, type_), vals in tax_summary.items():
            TaxLine.create({
                'wizard_id': self.id,
                'type': type_,
                'tax_id': tax_id,
                'base_amount': vals['base'],
                'tax_amount': vals['tax'],
                'move_ids': [(6, 0, vals['moves'])],
                'line_type': 'line',  # Normal line
            })

        # 4️⃣ Add total lines
        total_sale_base = sum([v['base'] for k, v in tax_summary.items() if k[1]=='sale'])
        total_sale_tax = sum([v['tax'] for k, v in tax_summary.items() if k[1]=='sale'])
        total_purchase_base = sum([v['base'] for k, v in tax_summary.items() if k[1]=='purchase'])
        total_purchase_tax = sum([v['tax'] for k, v in tax_summary.items() if k[1]=='purchase'])

        # Sales Total
        TaxLine.create({
            'wizard_id': self.id,
            'type': 'sale',
            'tax_id': False,
            'base_amount': total_sale_base,
            'tax_amount': total_sale_tax,
            'line_type': 'total_sale',
        })

        # Purchase Total
        TaxLine.create({
            'wizard_id': self.id,
            'type': 'purchase',
            'tax_id': False,
            'base_amount': total_purchase_base,
            'tax_amount': total_purchase_tax,
            'line_type': 'total_purchase',
        })

        # Net VAT Due
        TaxLine.create({
            'wizard_id': self.id,
            'type': False,
            'tax_id': False,
            'base_amount': total_sale_base - total_purchase_base,
            'tax_amount': total_sale_tax - total_purchase_tax,
            'line_type': 'net_vat_due',
        })

    def open_tax_report_details(self):
        """Compute summary and open tax lines"""
        self.compute_tax_summary()
        return {
            'name': 'Tax Report Summary',
            'type': 'ir.actions.act_window',
            'res_model': 'tax.report.detail.line',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('wizard_id', '=', self.id)],
        }
