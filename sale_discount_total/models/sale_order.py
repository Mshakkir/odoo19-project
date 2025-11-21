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


class SaleOrder(models.Model):
    """Inherit 'sale.order' model and add fields needed"""
    _inherit = "sale.order"

    state = fields.Selection(selection_add=[
        ('waiting', 'Waiting Approval'),
    ], ondelete={'waiting': 'set default'}, string='Status',
        readonly=True, copy=False, index=True, default='draft',
        help="Status of quotation.")

    discount_type = fields.Selection(
        [('percent', 'Percentage'), ('amount', 'Amount')],
        string='Discount type',
        default='percent', help="Type of discount.")
    discount_rate = fields.Float('Discount Rate', digits=(16, 2),
                                 help="Give the discount rate.")
    amount_discount = fields.Monetary(string='Discount', store=True,
                                      compute='_compute_amount_all_custom',
                                      readonly=True,
                                      help="Give the amount to be discounted.")
    margin_test = fields.Float(string="Margin", compute='_compute_margin_test')

    @api.depends('order_line.price_subtotal', 'order_line.discount',
                 'order_line.product_uom_qty', 'order_line.price_unit')
    def _compute_amount_all_custom(self):
        """Compute the discount amount"""
        for order in self:
            amount_discount = 0.0
            for line in order.order_line:
                if line.display_type not in ('line_section', 'line_note'):
                    amount_discount += (line.product_uom_qty * line.price_unit * line.discount) / 100
            order.amount_discount = amount_discount

    @api.depends('order_line.margin', 'amount_untaxed', 'amount_total')
    def _compute_margin_test(self):
        """Compute margin if sale_margin is installed"""
        if self.env['ir.module.module'].sudo().search(
                [('name', '=', 'sale_margin'), ('state', '=', 'installed')]):
            for record in self:
                # Check if margin field exists
                if hasattr(record, 'margin'):
                    record.margin_test = record.margin
                else:
                    record.margin_test = 0.0
        else:
            for record in self:
                record.margin_test = 0.0

    def action_confirm(self):
        """This function super action_confirm method"""
        for order in self:
            discount_avg = 0.0
            no_line = 0
            if order.company_id.so_double_validation == 'two_step':
                for line in order.order_line:
                    if line.display_type not in ('line_section', 'line_note'):
                        no_line += 1
                        discount_avg += line.discount

                if no_line > 0:
                    discount_avg = discount_avg / no_line

                if (order.company_id.so_double_validation_limit and
                        discount_avg > order.company_id.so_double_validation_limit):
                    order.state = 'waiting'
                    return True

        return super(SaleOrder, self).action_confirm()

    def action_approve(self):
        """This super the class and calls the action_confirm method on clicking
         approve button"""
        return super(SaleOrder, self).action_confirm()

    def _can_be_confirmed(self):
        """This function _can_be_confirmed adds waiting state"""
        self.ensure_one()
        return self.state in {'draft', 'sent', 'waiting'}

    @api.onchange('discount_type', 'discount_rate', 'order_line')
    def supply_rate(self):
        """This function calculates supply rates based on change of
        discount_type, discount_rate and order_line"""
        for order in self:
            if order.discount_type == 'percent':
                for line in order.order_line:
                    if line.display_type not in ('line_section', 'line_note'):
                        line.discount = order.discount_rate
            else:
                total = 0.0
                for line in order.order_line:
                    if line.display_type not in ('line_section', 'line_note'):
                        total += round((line.product_uom_qty * line.price_unit))

                if order.discount_rate != 0 and total > 0:
                    discount = (order.discount_rate / total) * 100
                else:
                    discount = 0.0

                for line in order.order_line:
                    if line.display_type not in ('line_section', 'line_note'):
                        line.discount = discount
                        new_sub_price = (line.price_unit * (discount / 100))
                        line.total_discount = line.price_unit - new_sub_price

    def _prepare_invoice(self):
        """Super sale order class and update with fields"""
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'discount_type': self.discount_type,
            'discount_rate': self.discount_rate,
        })
        return invoice_vals

    def button_dummy(self):
        """The button_dummy method is intended to perform some action related
        to the supply rate and always return True"""
        self.supply_rate()
        return True