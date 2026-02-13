from odoo import models, fields, api


class PaymentAllocationHistory(models.Model):
    """Store bill allocation details for each vendor payment"""
    _name = 'payment.allocation.history'
    _description = 'Payment Allocation History'
    _order = 'bill_date desc'

    payment_id = fields.Many2one('account.payment', string='Payment', required=True, ondelete='cascade')
    invoice_vendor_bill_id = fields.Many2one('account.move', string='Bill', required=True, ondelete='restrict')
    bill_number = fields.Char(string='Bill Number', readonly=True)
    bill_date = fields.Date(string='Bill Date', readonly=True)
    amount_total = fields.Monetary(string='Bill Total', currency_field='currency_id', readonly=True)
    amount_due = fields.Monetary(string='Amount Due', currency_field='currency_id', readonly=True)
    amount_paid = fields.Monetary(string='Amount Paid', currency_field='currency_id', readonly=True)
    balance_after_payment = fields.Monetary(string='Balance After Payment', currency_field='currency_id', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    # Computed display fields
    partner_id = fields.Many2one('res.partner', related='payment_id.partner_id', string='Vendor', readonly=True, store=True)
    payment_date = fields.Date(related='payment_id.date', string='Payment Date', readonly=True, store=True)
    payment_number = fields.Char(related='payment_id.name', string='Payment Number', readonly=True, store=True)