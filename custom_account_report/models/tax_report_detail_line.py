# from odoo import models, fields
#
# class TaxReportDetailLine(models.TransientModel):
#     _name = "tax.report.detail.line"
#     _description = "Tax Report Detail Line"
#
#     wizard_id = fields.Many2one('account.tax.report.wizard')
#     type = fields.Selection([
#         ('sale', 'Sale'),
#         ('purchase', 'Purchase')
#     ], string='Type')
#
#     tax_id = fields.Many2one('account.tax', string='Tax')
#     # Remove this line — Odoo automatically shows the tax name in the list
#     # tax_name = fields.Char(related='tax_id.name', string='Tax Name')
#
#     base_amount = fields.Monetary(string='Net Amount')
#     tax_amount = fields.Monetary(string='Tax Amount')
#     currency_id = fields.Many2one(
#         'res.currency',
#         default=lambda self: self.env.company.currency_id
#     )
#     move_ids = fields.Many2many('account.move', string='Invoices')
#
#     def open_moves(self):
#         """Open invoices related to this tax line"""
#         self.ensure_one()
#         return {
#             'name': 'Invoices for Tax',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'list,form',
#             'domain': [('id', 'in', self.move_ids.ids)],
#             'target': 'current',
#         }
from odoo import models, fields, api

class TaxReportDetailLine(models.TransientModel):
    _name = "tax.report.detail.line"
    _description = "Tax Report Detail Line"

    wizard_id = fields.Many2one('account.tax.report.wizard')
    type = fields.Selection([
        ('sale', 'Sale'),
        ('purchase', 'Purchase')
    ], string='Type')
    tax_id = fields.Many2one('account.tax', string='Tax')
    base_amount = fields.Monetary(string='Net Amount')
    tax_amount = fields.Monetary(string='Tax Amount')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )
    move_ids = fields.Many2many('account.move', string='Invoices')

    # NEW FIELDS
    sale_total = fields.Monetary(string='Sales Total', compute='_compute_totals')
    purchase_total = fields.Monetary(string='Purchase Total', compute='_compute_totals')
    net_vat_due = fields.Monetary(string='Net VAT Due', compute='_compute_totals')

    @api.depends('move_ids')
    def _compute_totals(self):
        for line in self:
            sale_total = sum(line.move_ids.filtered(lambda m: m.move_type in ['out_invoice', 'out_refund']).mapped('amount_total'))
            purchase_total = sum(line.move_ids.filtered(lambda m: m.move_type in ['in_invoice', 'in_refund']).mapped('amount_total'))
            line.sale_total = sale_total
            line.purchase_total = purchase_total
            line.net_vat_due = sale_total - purchase_total

    def open_moves(self):
        """Open invoices related to this tax line"""
        self.ensure_one()
        return {
            'name': 'Invoices for Tax',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.move_ids.ids)],
            'target': 'current',
        }
