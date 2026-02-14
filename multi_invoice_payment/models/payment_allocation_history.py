from odoo import models, fields, api


class PaymentAllocationHistory(models.Model):
    """Store invoice allocation details for each payment"""
    _name = 'payment.allocation.history'
    _description = 'Payment Allocation History'
    _order = 'invoice_date desc'

    payment_id = fields.Many2one('account.payment', string='Payment', required=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.move', string='Invoice', required=True, ondelete='restrict')
    invoice_number = fields.Char(string='Invoice Number', readonly=True)
    invoice_date = fields.Date(string='Invoice Date', readonly=True)
    amount_total = fields.Monetary(string='Invoice Total', currency_field='currency_id', readonly=True)
    amount_due = fields.Monetary(string='Amount Due', currency_field='currency_id', readonly=True)
    amount_paid = fields.Monetary(string='Amount Paid', currency_field='currency_id', readonly=True)
    balance_after_payment = fields.Monetary(string='Balance After Payment', currency_field='currency_id', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    memo = fields.Char(string='Memo', readonly=True)

    # Computed display fields
    partner_id = fields.Many2one('res.partner', related='payment_id.partner_id', string='Customer', readonly=True, store=True)
    payment_date = fields.Date(related='payment_id.date', string='Payment Date', readonly=True, store=True)
    payment_number = fields.Char(related='payment_id.name', string='Payment Number', readonly=True, store=True)