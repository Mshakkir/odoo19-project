# from odoo import models, fields, api, _
# from odoo.exceptions import UserError
#
#
# class PaymentAllocationDisplayWizard(models.TransientModel):
#     """Wizard to display payment allocation history"""
#     _name = 'payment.allocation.display.wizard'
#     _description = 'Payment Allocation Display'
#
#     payment_id = fields.Many2one('account.payment', string='Payment', readonly=True)
#     partner_id = fields.Many2one('res.partner', string='Customer', related='payment_id.partner_id', readonly=True)
#     payment_date = fields.Date(string='Payment Date', related='payment_id.date', readonly=True)
#     payment_amount = fields.Monetary(string='Payment Amount', related='payment_id.amount', readonly=True,
#                                      currency_field='currency_id')
#     payment_number = fields.Char(string='Payment Number', related='payment_id.name', readonly=True)
#     journal_id = fields.Many2one('account.journal', string='Journal', related='payment_id.journal_id', readonly=True)
#     currency_id = fields.Many2one('res.currency', related='payment_id.currency_id', readonly=True)
#     memo = fields.Char(string='Memo', readonly=True)
#
#     allocation_line_ids = fields.One2many('payment.allocation.display.line', 'wizard_id', string='Invoice Allocations')
#
#     # Summary fields
#     total_invoiced = fields.Monetary(string='Total Invoiced', compute='_compute_totals', currency_field='currency_id')
#     total_allocated = fields.Monetary(string='Total Allocated', compute='_compute_totals', currency_field='currency_id')
#     total_balance = fields.Monetary(string='Total Balance', compute='_compute_totals', currency_field='currency_id')
#
#     @api.depends('allocation_line_ids.amount_total', 'allocation_line_ids.amount_paid',
#                  'allocation_line_ids.balance_after_payment')
#     def _compute_totals(self):
#         for rec in self:
#             rec.total_invoiced = sum(line.amount_total for line in rec.allocation_line_ids)
#             rec.total_allocated = sum(line.amount_paid for line in rec.allocation_line_ids)
#             rec.total_balance = sum(line.balance_after_payment for line in rec.allocation_line_ids)
#
#
# class PaymentAllocationDisplayLine(models.TransientModel):
#     """Transient model to display allocation lines in wizard"""
#     _name = 'payment.allocation.display.line'
#     _description = 'Payment Allocation Display Line'
#
#     wizard_id = fields.Many2one('payment.allocation.display.wizard', string='Wizard', required=True, ondelete='cascade')
#     invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
#     invoice_number = fields.Char(string='Invoice Number', readonly=True)
#     invoice_date = fields.Date(string='Invoice Date', readonly=True)
#     amount_total = fields.Monetary(string='Total Amount', currency_field='currency_id', readonly=True)
#     amount_due = fields.Monetary(string='Amount Due', currency_field='currency_id', readonly=True)
#     amount_paid = fields.Monetary(string='Amount Paid', currency_field='currency_id', readonly=True)
#     balance_after_payment = fields.Monetary(string='Balance Amount', currency_field='currency_id', readonly=True)
#     currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id', string='Currency', readonly=True)

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PaymentAllocationDisplayWizard(models.TransientModel):
    """Wizard to display payment allocation history"""
    _name = 'payment.allocation.display.wizard'
    _description = 'Payment Allocation Display'

    payment_id = fields.Many2one('account.payment', string='Payment', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', related='payment_id.partner_id', readonly=True)
    payment_date = fields.Date(string='Payment Date', related='payment_id.date', readonly=True)
    payment_amount = fields.Monetary(string='Payment Amount', related='payment_id.amount', readonly=True,
                                     currency_field='currency_id')
    payment_number = fields.Char(string='Payment Number', related='payment_id.name', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', related='payment_id.journal_id', readonly=True)
    currency_id = fields.Many2one('res.currency', related='payment_id.currency_id', readonly=True)
    payment_reference = fields.Char(string='Payment Reference', related='payment_id.payment_reference', readonly=True)

    allocation_line_ids = fields.One2many('payment.allocation.display.line', 'wizard_id', string='Invoice Allocations')

    # Summary fields
    total_invoiced = fields.Monetary(string='Total Invoiced', compute='_compute_totals', currency_field='currency_id')
    total_allocated = fields.Monetary(string='Total Allocated', compute='_compute_totals', currency_field='currency_id')
    total_balance = fields.Monetary(string='Total Balance', compute='_compute_totals', currency_field='currency_id')

    @api.depends('allocation_line_ids.amount_total', 'allocation_line_ids.amount_paid',
                 'allocation_line_ids.balance_after_payment')
    def _compute_totals(self):
        for rec in self:
            rec.total_invoiced = sum(line.amount_total for line in rec.allocation_line_ids)
            rec.total_allocated = sum(line.amount_paid for line in rec.allocation_line_ids)
            rec.total_balance = sum(line.balance_after_payment for line in rec.allocation_line_ids)


class PaymentAllocationDisplayLine(models.TransientModel):
    """Transient model to display allocation lines in wizard"""
    _name = 'payment.allocation.display.line'
    _description = 'Payment Allocation Display Line'

    wizard_id = fields.Many2one('payment.allocation.display.wizard', string='Wizard', required=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    invoice_number = fields.Char(string='Invoice Number', readonly=True)
    invoice_date = fields.Date(string='Invoice Date', readonly=True)
    amount_total = fields.Monetary(string='Total Amount', currency_field='currency_id', readonly=True)
    amount_due = fields.Monetary(string='Amount Due', currency_field='currency_id', readonly=True)
    amount_paid = fields.Monetary(string='Amount Paid', currency_field='currency_id', readonly=True)
    balance_after_payment = fields.Monetary(string='Balance Amount', currency_field='currency_id', readonly=True)
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id', string='Currency', readonly=True)