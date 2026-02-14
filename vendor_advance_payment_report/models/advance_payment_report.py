# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AdvancePaymentReport(models.TransientModel):
    _name = 'advance.payment.report'
    _description = 'Advance Payment Report'
    _order = 'date desc, receipt_number desc'

    date = fields.Date(string='Date', required=True)
    receipt_number = fields.Char(string='Receipt Number', required=True)
    journal_name = fields.Char(string='Journal', required=True)
    payment_method = fields.Char(string='Payment Method', required=True)
    vendor_name = fields.Char(string='Vendor Name', required=True)
    amount = fields.Float(string='Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency')
    payment_id = fields.Many2one('account.payment', string='Payment', required=True)

    def action_open_payment(self):
        """Open the payment record"""
        self.ensure_one()
        return {
            'name': 'Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }









# # -*- coding: utf-8 -*-
#
# from odoo import models, fields, api
#
#
# class AdvancePaymentReport(models.TransientModel):
#     _name = 'advance.payment.report'
#     _description = 'Advance Payment Report'
#     _order = 'date desc, receipt_number desc'
#
#     date = fields.Date(string='Date', required=True)
#     receipt_number = fields.Char(string='Receipt Number', required=True)
#     journal_name = fields.Char(string='Journal', required=True)
#     payment_method = fields.Char(string='Payment Method', required=True)
#     vendor_name = fields.Char(string='Vendor Name', required=True)
#     amount = fields.Float(string='Amount', required=True)
#     currency_id = fields.Many2one('res.currency', string='Currency')