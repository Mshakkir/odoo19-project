# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Sreerag PM(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class AccountMove(models.Model):
    """This class inherits "account.move" model and adds discount_type,
    discount_rate, amount_discount
     """
    _inherit = "account.move"

    discount_type = fields.Selection(
        [('percent', 'Percentage'), ('amount', 'Amount')],
        string='Discount type',
        default='percent', help="Type of discount.")
    discount_rate = fields.Float('Discount Rate', digits=(16, 2),
                                 help="Give the discount rate.")
    amount_discount = fields.Monetary(string='Discount', store=True,
                                      compute='_compute_amount_discount', readonly=True,
                                      help="Give the amount to be discounted.")

    @api.depends('invoice_line_ids.discount', 'invoice_line_ids.price_subtotal',
                 'invoice_line_ids.quantity', 'invoice_line_ids.price_unit')
    def _compute_amount_discount(self):
        """Compute the discount amount"""
        for move in self:
            if move.is_invoice(include_receipts=True):
                discount_total = 0.0
                for line in move.invoice_line_ids:
                    if line.display_type not in ('line_section', 'line_note'):
                        total_price = line.price_unit * line.quantity
                        discount_amount = total_price * (line.discount / 100.0)
                        discount_total += discount_amount
                move.amount_discount = discount_total
            else:
                move.amount_discount = 0.0

    @api.onchange('discount_type', 'discount_rate', 'invoice_line_ids')
    def _supply_rate(self):
        """This function calculates supply rates based on change of
        discount_type, discount_rate and invoice_line_ids"""
        for inv in self:
            if inv.discount_type == 'percent':
                for line in inv.invoice_line_ids:
                    if line.display_type not in ('line_section', 'line_note'):
                        line.discount = inv.discount_rate
            else:
                total = 0.0
                for line in inv.invoice_line_ids:
                    if line.display_type not in ('line_section', 'line_note'):
                        total += (line.quantity * line.price_unit)
                if inv.discount_rate != 0 and total > 0:
                    discount = (inv.discount_rate / total) * 100
                else:
                    discount = 0.0
                for line in inv.invoice_line_ids:
                    if line.display_type not in ('line_section', 'line_note'):
                        line.discount = discount

    def button_dummy(self):
        """The button_dummy method is intended to perform some action related
        to the supply rate and always return True"""
        self._supply_rate()
        return True


class AccountMoveLine(models.Model):
    """This class inherits "account.move.line" model and adds discount field"""
    _inherit = "account.move.line"

    discount = fields.Float(string='Discount (%)', digits=(16, 20), default=0.0,
                            help="Give the discount needed")