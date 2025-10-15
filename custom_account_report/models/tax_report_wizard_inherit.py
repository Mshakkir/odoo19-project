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
from odoo import models, fields, api

class AccountTaxReportWizard(models.TransientModel):
    _inherit = 'account.tax.report.wizard'

    detail_line_ids = fields.One2many('tax.report.detail.line', 'wizard_id', string='Tax Summary Lines')

    def compute_tax_summary(self):
        TaxLine = self.env['tax.report.detail.line']

        # Clear existing lines for the wizard
        self.detail_line_ids.unlink()

        sale_total_base = 0
        sale_total_tax = 0
        purchase_total_base = 0
        purchase_total_tax = 0

        # Loop over your tax lines (existing logic)
        for tax_data in self.get_tax_data():  # Replace with your current tax fetching logic
            line = TaxLine.create({
                'wizard_id': self.id,
                'tax_name': tax_data['tax_name'],
                'tax_id': tax_data['tax_id'],
                'type': tax_data['type'],
                'base_amount': tax_data['base_amount'],
                'tax_amount': tax_data['tax_amount'],
                'move_ids': [(6, 0, tax_data['move_ids'])],  # list of invoice IDs
            })

            # Sum for sales/purchases
            if tax_data['type'] == 'sale':
                sale_total_base += tax_data['base_amount']
                sale_total_tax += tax_data['tax_amount']
            else:
                purchase_total_base += tax_data['base_amount']
                purchase_total_tax += tax_data['tax_amount']

        # Add summary rows
        if sale_total_base or sale_total_tax:
            TaxLine.create({
                'wizard_id': self.id,
                'tax_name': 'Total Sales',
                'type': 'sale',
                'base_amount': sale_total_base,
                'tax_amount': sale_total_tax,
                'is_summary_row': True,
            })
        if purchase_total_base or purchase_total_tax:
            TaxLine.create({
                'wizard_id': self.id,
                'tax_name': 'Total Purchases',
                'type': 'purchase',
                'base_amount': purchase_total_base,
                'tax_amount': purchase_total_tax,
                'is_summary_row': True,
            })

        # Net VAT Due row
        net_vat_due = sale_total_tax - purchase_total_tax
        TaxLine.create({
            'wizard_id': self.id,
            'tax_name': 'Net VAT Due',
            'type': 'sale',  # you can keep it sale type or blank
            'base_amount': 0.0,
            'tax_amount': net_vat_due,
            'is_summary_row': True,
        })

    # def compute_tax_summary(self):
    #     self.ensure_one()
    #     TaxLine = self.env['tax.report.detail.line']
    #     self.detail_line_ids.unlink()
    #
    #     tax_summary = {}
    #
    #     # Define date domain
    #     domain = [
    #         ('invoice_date', '>=', self.date_from),
    #         ('invoice_date', '<=', self.date_to),
    #         ('state', '=', 'posted')
    #     ]
    #
    #     # 1️⃣ Sales
    #     sale_moves = self.env['account.move'].search(domain + [('move_type', 'in', ['out_invoice', 'out_refund'])])
    #     for move in sale_moves:
    #         for line in move.invoice_line_ids:
    #             for tax in line.tax_ids:
    #                 key = (tax.id, 'sale')
    #                 if key not in tax_summary:
    #                     tax_summary[key] = {'base': 0.0, 'tax': 0.0, 'moves': []}
    #                 base_amount = line.price_subtotal
    #                 tax_amount = tax.amount / 100 * base_amount if tax.amount_type == 'percent' else tax.amount
    #                 tax_summary[key]['base'] += base_amount
    #                 tax_summary[key]['tax'] += tax_amount
    #                 tax_summary[key]['moves'].append(move.id)
    #
    #     # 2️⃣ Purchases
    #     purchase_moves = self.env['account.move'].search(domain + [('move_type', 'in', ['in_invoice', 'in_refund'])])
    #     for move in purchase_moves:
    #         for line in move.invoice_line_ids:
    #             for tax in line.tax_ids:
    #                 key = (tax.id, 'purchase')
    #                 if key not in tax_summary:
    #                     tax_summary[key] = {'base': 0.0, 'tax': 0.0, 'moves': []}
    #                 base_amount = line.price_subtotal
    #                 tax_amount = tax.amount / 100 * base_amount if tax.amount_type == 'percent' else tax.amount
    #                 tax_summary[key]['base'] += base_amount
    #                 tax_summary[key]['tax'] += tax_amount
    #                 tax_summary[key]['moves'].append(move.id)
    #
    #     # 3️⃣ Create detail lines
    #     sale_total = 0.0
    #     purchase_total = 0.0
    #
    #     for (tax_id, type_), vals in tax_summary.items():
    #         TaxLine.create({
    #             'wizard_id': self.id,
    #             'type': type_,
    #             'tax_id': tax_id,
    #             'base_amount': vals['base'],
    #             'tax_amount': vals['tax'],
    #             'move_ids': [(6, 0, vals['moves'])],
    #         })
    #         if type_ == 'sale':
    #             sale_total += vals['tax']
    #         elif type_ == 'purchase':
    #             purchase_total += vals['tax']
    #
    #     # 4️⃣ Add total rows (display only)
    #     # Sale total row
    #     if sale_total:
    #         TaxLine.create({
    #             'wizard_id': self.id,
    #             'type': 'sale',
    #             'tax_name': 'Total Sales',
    #             'base_amount': 0.0,
    #             'tax_amount': sale_total,
    #         })
    #
    #     # Purchase total row
    #     if purchase_total:
    #         TaxLine.create({
    #             'wizard_id': self.id,
    #             'type': 'purchase',
    #             'tax_name': 'Total Purchases',
    #             'base_amount': 0.0,
    #             'tax_amount': purchase_total,
    #         })
    #
    #     # Net VAT Due row
    #     TaxLine.create({
    #         'wizard_id': self.id,
    #         'type': 'sale',
    #         'tax_name': 'Net VAT Due',
    #         'base_amount': 0.0,
    #         'tax_amount': sale_total - purchase_total,
    #     })

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
