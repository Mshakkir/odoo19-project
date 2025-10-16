# from odoo import models, fields, api
#
# class AccountTaxReportWizard(models.TransientModel):
#     _inherit = 'account.tax.report.wizard'
#
#
#     detail_line_ids = fields.One2many('tax.report.detail.line', 'wizard_id', string='Tax Summary Lines')
#
#     def compute_tax_summary(self):
#         self.ensure_one()
#         TaxLine = self.env['tax.report.detail.line']
#         self.detail_line_ids.unlink()
#
#         tax_summary = {}
#
#         # Define date domain
#         domain = [
#             ('invoice_date', '>=', self.date_from),
#             ('invoice_date', '<=', self.date_to),
#             ('state', '=', 'posted')
#         ]
#
#         # 1️⃣ Sales
#         sale_moves = self.env['account.move'].search(domain + [('move_type', 'in', ['out_invoice', 'out_refund'])])
#         for move in sale_moves:
#             for line in move.invoice_line_ids:
#                 for tax in line.tax_ids:
#                     key = (tax.id, 'sale')
#                     if key not in tax_summary:
#                         tax_summary[key] = {'base': 0.0, 'tax': 0.0, 'moves': []}
#                     # Compute base and tax from line
#                     base_amount = line.price_subtotal
#                     tax_amount = tax.amount / 100 * base_amount if tax.amount_type == 'percent' else tax.amount
#                     tax_summary[key]['base'] += base_amount
#                     tax_summary[key]['tax'] += tax_amount
#                     tax_summary[key]['moves'].append(move.id)
#
#         # 2️⃣ Purchases
#         purchase_moves = self.env['account.move'].search(domain + [('move_type', 'in', ['in_invoice', 'in_refund'])])
#         for move in purchase_moves:
#             for line in move.invoice_line_ids:
#                 for tax in line.tax_ids:
#                     key = (tax.id, 'purchase')
#                     if key not in tax_summary:
#                         tax_summary[key] = {'base': 0.0, 'tax': 0.0, 'moves': []}
#                     base_amount = line.price_subtotal
#                     tax_amount = tax.amount / 100 * base_amount if tax.amount_type == 'percent' else tax.amount
#                     tax_summary[key]['base'] += base_amount
#                     tax_summary[key]['tax'] += tax_amount
#                     tax_summary[key]['moves'].append(move.id)
#
#         # 3️⃣ Create summary lines
#         for (tax_id, type_), vals in tax_summary.items():
#             TaxLine.create({
#                 'wizard_id': self.id,
#                 'type': type_,
#                 'tax_id': tax_id,
#                 'base_amount': vals['base'],
#                 'tax_amount': vals['tax'],
#                 'move_ids': [(6, 0, vals['moves'])],
#             })
#
#     def open_tax_report_details(self):
#         self.compute_tax_summary()
#         return {
#             'name': 'Tax Report Summary',
#             'type': 'ir.actions.act_window',
#             'res_model': 'tax.report.detail.line',
#             'view_mode': 'list,form',
#             'target': 'current',
#             'context': {'default_wizard_id': self.id},
#             'domain': [('wizard_id', '=', self.id)],
#         }
#
# models/tax_report_wizard_inherrit.py (or update existing file)
from odoo import models, fields, api

class AccountTaxReportWizard(models.TransientModel):
    _inherit = 'account.tax.report.wizard'

    detail_line_ids = fields.One2many('tax.report.detail.line', 'wizard_id', string='Tax Summary Lines')

    def compute_tax_summary(self):
        self.ensure_one()
        TaxLine = self.env['tax.report.detail.line']
        # remove old transient lines for this wizard
        self.detail_line_ids.unlink()

        tax_summary = {}    # key: (tax_id, type) -> {'base':..., 'tax':..., 'moves': set()}
        # date domain
        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted')
        ]

        # 1) Sales moves
        sale_moves = self.env['account.move'].search(domain + [('move_type', 'in', ['out_invoice', 'out_refund'])])
        for move in sale_moves:
            for line in move.invoice_line_ids:
                for tax in line.tax_ids:
                    key = (tax.id, 'sale')
                    vals = tax_summary.setdefault(key, {'base': 0.0, 'tax': 0.0, 'moves': set()})
                    base_amount = line.price_subtotal
                    # compute tax amount depending on tax configuration
                    if tax.amount_type == 'percent':
                        tax_amount = (tax.amount / 100.0) * base_amount
                    else:
                        tax_amount = tax.amount
                    vals['base'] += base_amount
                    vals['tax'] += tax_amount
                    vals['moves'].add(move.id)

        # 2) Purchase moves
        purchase_moves = self.env['account.move'].search(domain + [('move_type', 'in', ['in_invoice', 'in_refund'])])
        for move in purchase_moves:
            for line in move.invoice_line_ids:
                for tax in line.tax_ids:
                    key = (tax.id, 'purchase')
                    vals = tax_summary.setdefault(key, {'base': 0.0, 'tax': 0.0, 'moves': set()})
                    base_amount = line.price_subtotal
                    if tax.amount_type == 'percent':
                        tax_amount = (tax.amount / 100.0) * base_amount
                    else:
                        tax_amount = tax.amount
                    vals['base'] += base_amount
                    vals['tax'] += tax_amount
                    vals['moves'].add(move.id)

        # Totals for sales & purchases (for summary rows)
        total_sales_base = 0.0
        total_sales_tax = 0.0
        total_purchase_base = 0.0
        total_purchase_tax = 0.0

        # 3) Create per-tax lines
        for (tax_id, type_), vals in tax_summary.items():
            move_list = list(vals['moves'])
            TaxLine.create({
                'wizard_id': self.id,
                'type': type_,
                'tax_id': tax_id,
                'tax_name': self.env['account.tax'].browse(tax_id).display_name,
                'base_amount': vals['base'],
                'tax_amount': vals['tax'],
                'move_ids': [(6, 0, move_list)],
            })
            # accumulate totals
            if type_ == 'sale':
                total_sales_base += vals['base']
                total_sales_tax += vals['tax']
            elif type_ == 'purchase':
                total_purchase_base += vals['base']
                total_purchase_tax += vals['tax']

        # 4) Create a blank separator if desired (optional)
        # (not necessary)

        # 5) Create summary rows
        # Total Sales summary row
        TaxLine.create({
            'wizard_id': self.id,
            'type': 'sale',
            'tax_id': False,
            'tax_name': 'Total Sales',
            'base_amount': total_sales_base,
            'tax_amount': total_sales_tax,
            'move_ids': [(6, 0, [])],   # empty so Show Invoices won't appear
        })

        # Total Purchases summary row
        TaxLine.create({
            'wizard_id': self.id,
            'type': 'purchase',
            'tax_id': False,
            'tax_name': 'Total Purchases',
            'base_amount': total_purchase_base,
            'tax_amount': total_purchase_tax,
            'move_ids': [(6, 0, [])],
        })

        # Net VAT Due row (Sales tax - Purchase tax)
        net_tax = total_sales_tax - total_purchase_tax
        net_base = total_sales_base - total_purchase_base
        TaxLine.create({
            'wizard_id': self.id,
            'type': 'net',
            'tax_id': False,
            'tax_name': 'Net VAT Due',
            'base_amount': net_base,
            'tax_amount': net_tax,
            'move_ids': [(6, 0, [])],
        })
