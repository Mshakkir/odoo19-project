# from odoo import models, fields, api
# from odoo.exceptions import UserError
#
#
# class StockPicking(models.Model):
#     _inherit = 'stock.picking'
#
#     partner_total_invoiced = fields.Monetary(
#         string='Total Invoiced/Billed',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Total invoiced or billed for this partner'
#     )
#
#     partner_total_paid = fields.Monetary(
#         string='Amount Paid',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Total amount paid'
#     )
#
#     partner_balance_due = fields.Monetary(
#         string='Balance Due',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Remaining balance'
#     )
#
#     currency_id = fields.Many2one(
#         'res.currency',
#         string='Currency',
#         compute='_compute_currency',
#         store=False
#     )
#
#     @api.depends('company_id')
#     def _compute_currency(self):
#         """Get company currency"""
#         for picking in self:
#             picking.currency_id = picking.company_id.currency_id or self.env.company.currency_id
#
#     @api.depends('partner_id', 'picking_type_id')
#     def _compute_partner_balance(self):
#         """Calculate partner financial summary based on picking type"""
#         for picking in self:
#             if picking.partner_id and picking.picking_type_id:
#                 try:
#                     # Delivery orders (customer)
#                     if picking.picking_type_id.code == 'outgoing':
#                         invoices = self.env['account.move'].search([
#                             ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
#                             ('move_type', 'in', ['out_invoice', 'out_refund']),
#                             ('state', '=', 'posted')
#                         ])
#
#                         total_invoiced = sum(invoices.filtered(
#                             lambda inv: inv.move_type == 'out_invoice'
#                         ).mapped('amount_total'))
#
#                         total_refunded = sum(invoices.filtered(
#                             lambda inv: inv.move_type == 'out_refund'
#                         ).mapped('amount_total'))
#
#                         total_residual = sum(invoices.mapped('amount_residual'))
#
#                         picking.partner_total_invoiced = total_invoiced - total_refunded
#                         picking.partner_balance_due = total_residual
#                         picking.partner_total_paid = picking.partner_total_invoiced - picking.partner_balance_due
#
#                     # Receipts (vendor)
#                     elif picking.picking_type_id.code == 'incoming':
#                         bills = self.env['account.move'].search([
#                             ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
#                             ('move_type', 'in', ['in_invoice', 'in_refund']),
#                             ('state', '=', 'posted')
#                         ])
#
#                         total_billed = sum(bills.filtered(
#                             lambda bill: bill.move_type == 'in_invoice'
#                         ).mapped('amount_total'))
#
#                         total_refunded = sum(bills.filtered(
#                             lambda bill: bill.move_type == 'in_refund'
#                         ).mapped('amount_total'))
#
#                         total_residual = sum(bills.mapped('amount_residual'))
#
#                         picking.partner_total_invoiced = total_billed - total_refunded
#                         picking.partner_balance_due = total_residual
#                         picking.partner_total_paid = picking.partner_total_invoiced - picking.partner_balance_due
#                     else:
#                         picking.partner_total_invoiced = 0.0
#                         picking.partner_total_paid = 0.0
#                         picking.partner_balance_due = 0.0
#
#                 except Exception:
#                     picking.partner_total_invoiced = 0.0
#                     picking.partner_total_paid = 0.0
#                     picking.partner_balance_due = 0.0
#             else:
#                 picking.partner_total_invoiced = 0.0
#                 picking.partner_total_paid = 0.0
#                 picking.partner_balance_due = 0.0
#
#     def action_view_partner_invoices(self):
#         """Open partner invoices/bills based on picking type"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("No partner selected.")
#
#         if self.picking_type_id.code == 'outgoing':
#             # Customer invoices
#             return {
#                 'name': f'Invoices - {self.partner_id.name}',
#                 'type': 'ir.actions.act_window',
#                 'res_model': 'account.move',
#                 'view_mode': 'list,form',
#                 'views': [(False, 'list'), (False, 'form')],
#                 'domain': [
#                     ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                     ('move_type', 'in', ['out_invoice', 'out_refund']),
#                     ('state', '=', 'posted')
#                 ],
#                 'context': {'create': False},
#             }
#         else:
#             # Vendor bills
#             return {
#                 'name': f'Bills - {self.partner_id.name}',
#                 'type': 'ir.actions.act_window',
#                 'res_model': 'account.move',
#                 'view_mode': 'list,form',
#                 'views': [(False, 'list'), (False, 'form')],
#                 'domain': [
#                     ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                     ('move_type', 'in', ['in_invoice', 'in_refund']),
#                     ('state', '=', 'posted')
#                 ],
#                 'context': {'create': False},
#             }
#
#     def action_view_partner_payments(self):
#         """Open partner payments based on picking type"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("No partner selected.")
#
#         all_payments = self.env['account.payment'].search([
#             ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#         ])
#
#         payment_type = 'inbound' if self.picking_type_id.code == 'outgoing' else 'outbound'
#
#         if not all_payments:
#             return {
#                 'name': f'Paid Invoices - {self.partner_id.name}',
#                 'type': 'ir.actions.act_window',
#                 'res_model': 'account.move',
#                 'view_mode': 'list,form',
#                 'views': [(False, 'list'), (False, 'form')],
#                 'domain': [
#                     ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                     ('payment_state', 'in', ['paid', 'in_payment', 'partial']),
#                     ('state', '=', 'posted'),
#                 ],
#                 'context': {'create': False},
#             }
#
#         return {
#             'name': f'Payments - {self.partner_id.name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.payment',
#             'view_mode': 'list,form',
#             'views': [(False, 'list'), (False, 'form')],
#             'domain': [
#                 ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                 ('payment_type', '=', payment_type),
#             ],
#             'context': {
#                 'create': False,
#                 'default_partner_id': self.partner_id.id,
#                 'default_payment_type': payment_type,
#             },
#         }

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    partner_total_invoiced = fields.Monetary(
        string='Total Invoiced/Billed',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total invoiced or billed for this partner'
    )

    partner_total_paid = fields.Monetary(
        string='Amount Paid',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total amount paid'
    )

    partner_balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Remaining balance'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency',
        store=False
    )

    @api.depends('company_id')
    def _compute_currency(self):
        """Get company currency"""
        for picking in self:
            try:
                if picking.company_id and picking.company_id.currency_id:
                    picking.currency_id = picking.company_id.currency_id
                    _logger.info(f"CURRENCY: Picking {picking.name} - Currency set to {picking.currency_id.name}")
                else:
                    picking.currency_id = self.env.company.currency_id
                    _logger.info(
                        f"CURRENCY: Picking {picking.name} - Using default company currency {picking.currency_id.name if picking.currency_id else 'NONE'}")
            except Exception as e:
                _logger.error(f"CURRENCY ERROR for picking {picking.name}: {str(e)}", exc_info=True)
                picking.currency_id = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)

    @api.depends('partner_id', 'picking_type_id')
    def _compute_partner_balance(self):
        """Calculate partner financial summary based on picking type"""
        _logger.info("=" * 80)
        _logger.info("STOCK PICKING: Starting _compute_partner_balance")
        _logger.info("=" * 80)

        # Check if account.move model exists
        if 'account.move' not in self.env:
            _logger.error("CRITICAL: account.move model NOT FOUND in environment!")
            _logger.error("Available models: %s", list(self.env.keys())[:20])
            for picking in self:
                picking.partner_total_invoiced = 0.0
                picking.partner_total_paid = 0.0
                picking.partner_balance_due = 0.0
            return
        else:
            _logger.info("✓ account.move model is available")

        for picking in self:
            _logger.info("-" * 80)
            _logger.info(f"Processing Picking: {picking.name}")
            _logger.info(f"  Partner: {picking.partner_id.name if picking.partner_id else 'NO PARTNER'}")
            _logger.info(f"  Picking Type: {picking.picking_type_id.name if picking.picking_type_id else 'NO TYPE'}")
            _logger.info(
                f"  Picking Type Code: {picking.picking_type_id.code if picking.picking_type_id else 'NO CODE'}")

            # Reset all fields first
            picking.partner_total_invoiced = 0.0
            picking.partner_total_paid = 0.0
            picking.partner_balance_due = 0.0

            if not picking.partner_id:
                _logger.warning(f"  ⚠ Skipping - No partner assigned")
                continue

            if not picking.picking_type_id:
                _logger.warning(f"  ⚠ Skipping - No picking type assigned")
                continue

            try:
                # Delivery orders (customer)
                if picking.picking_type_id.code == 'outgoing':
                    _logger.info(f"  → Processing as OUTGOING (Customer Delivery)")

                    invoices = self.env['account.move'].search([
                        ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                        ('move_type', 'in', ['out_invoice', 'out_refund']),
                        ('state', '=', 'posted')
                    ])

                    _logger.info(f"  → Found {len(invoices)} customer invoices/refunds")

                    if len(invoices) == 0:
                        _logger.warning(f"  ⚠ NO INVOICES FOUND for partner {picking.partner_id.name}")
                        _logger.info(f"  → Search criteria:")
                        _logger.info(f"     - Partner ID: {picking.partner_id.id}")
                        _logger.info(f"     - Commercial Partner ID: {picking.partner_id.commercial_partner_id.id}")
                        _logger.info(f"     - Move types: ['out_invoice', 'out_refund']")
                        _logger.info(f"     - State: posted")

                        # Check if ANY invoices exist for this partner
                        any_invoices = self.env['account.move'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                        ])
                        _logger.info(f"  → Total account.move records for partner: {len(any_invoices)}")

                        if any_invoices:
                            for inv in any_invoices[:5]:  # Show first 5
                                _logger.info(f"     - Invoice: {inv.name}, Type: {inv.move_type}, State: {inv.state}")

                    out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
                    out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')

                    _logger.info(f"  → Breakdown: {len(out_invoices)} invoices, {len(out_refunds)} refunds")

                    total_invoiced = sum(out_invoices.mapped('amount_total'))
                    total_refunded = sum(out_refunds.mapped('amount_total'))

                    invoice_residual = sum(out_invoices.mapped('amount_residual'))
                    refund_residual = sum(out_refunds.mapped('amount_residual'))

                    _logger.info(f"  → Calculations:")
                    _logger.info(f"     - Total Invoiced: {total_invoiced}")
                    _logger.info(f"     - Total Refunded: {total_refunded}")
                    _logger.info(f"     - Invoice Residual: {invoice_residual}")
                    _logger.info(f"     - Refund Residual: {refund_residual}")

                    picking.partner_total_invoiced = total_invoiced - total_refunded
                    picking.partner_balance_due = invoice_residual - refund_residual
                    picking.partner_total_paid = picking.partner_total_invoiced - picking.partner_balance_due

                    _logger.info(f"  → FINAL VALUES:")
                    _logger.info(f"     - Total Invoiced: {picking.partner_total_invoiced}")
                    _logger.info(f"     - Total Paid: {picking.partner_total_paid}")
                    _logger.info(f"     - Balance Due: {picking.partner_balance_due}")

                # Receipts (vendor)
                elif picking.picking_type_id.code == 'incoming':
                    _logger.info(f"  → Processing as INCOMING (Vendor Receipt)")

                    bills = self.env['account.move'].search([
                        ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                        ('move_type', 'in', ['in_invoice', 'in_refund']),
                        ('state', '=', 'posted')
                    ])

                    _logger.info(f"  → Found {len(bills)} vendor bills/refunds")

                    if len(bills) == 0:
                        _logger.warning(f"  ⚠ NO BILLS FOUND for vendor {picking.partner_id.name}")
                        _logger.info(f"  → Search criteria:")
                        _logger.info(f"     - Partner ID: {picking.partner_id.id}")
                        _logger.info(f"     - Commercial Partner ID: {picking.partner_id.commercial_partner_id.id}")
                        _logger.info(f"     - Move types: ['in_invoice', 'in_refund']")
                        _logger.info(f"     - State: posted")

                        # Check if ANY bills exist for this partner
                        any_bills = self.env['account.move'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                        ])
                        _logger.info(f"  → Total account.move records for partner: {len(any_bills)}")

                        if any_bills:
                            for bill in any_bills[:5]:  # Show first 5
                                _logger.info(f"     - Bill: {bill.name}, Type: {bill.move_type}, State: {bill.state}")

                    in_invoices = bills.filtered(lambda bill: bill.move_type == 'in_invoice')
                    in_refunds = bills.filtered(lambda bill: bill.move_type == 'in_refund')

                    _logger.info(f"  → Breakdown: {len(in_invoices)} bills, {len(in_refunds)} refunds")

                    total_billed = sum(in_invoices.mapped('amount_total'))
                    total_refunded = sum(in_refunds.mapped('amount_total'))

                    bill_residual = sum(in_invoices.mapped('amount_residual'))
                    refund_residual = sum(in_refunds.mapped('amount_residual'))

                    _logger.info(f"  → Calculations:")
                    _logger.info(f"     - Total Billed: {total_billed}")
                    _logger.info(f"     - Total Refunded: {total_refunded}")
                    _logger.info(f"     - Bill Residual: {bill_residual}")
                    _logger.info(f"     - Refund Residual: {refund_residual}")

                    picking.partner_total_invoiced = total_billed - total_refunded
                    picking.partner_balance_due = bill_residual - refund_residual
                    picking.partner_total_paid = picking.partner_total_invoiced - picking.partner_balance_due

                    _logger.info(f"  → FINAL VALUES:")
                    _logger.info(f"     - Total Billed: {picking.partner_total_invoiced}")
                    _logger.info(f"     - Total Paid: {picking.partner_total_paid}")
                    _logger.info(f"     - Balance Due: {picking.partner_balance_due}")
                else:
                    _logger.warning(f"  ⚠ Unknown picking type code: {picking.picking_type_id.code}")
                    picking.partner_total_invoiced = 0.0
                    picking.partner_total_paid = 0.0
                    picking.partner_balance_due = 0.0

            except Exception as e:
                _logger.error(f"  ✗ ERROR computing balance for {picking.partner_id.name}: {str(e)}", exc_info=True)
                picking.partner_total_invoiced = 0.0
                picking.partner_total_paid = 0.0
                picking.partner_balance_due = 0.0

        _logger.info("=" * 80)
        _logger.info("STOCK PICKING: Finished _compute_partner_balance")
        _logger.info("=" * 80)

    def action_view_partner_invoices(self):
        """Open partner invoices/bills based on picking type"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        if self.picking_type_id.code == 'outgoing':
            # Customer invoices
            return {
                'name': f'Invoices - {self.partner_id.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [
                    ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                    ('state', '=', 'posted')
                ],
                'context': {'create': False},
            }
        else:
            # Vendor bills
            return {
                'name': f'Bills - {self.partner_id.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [
                    ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                    ('move_type', 'in', ['in_invoice', 'in_refund']),
                    ('state', '=', 'posted')
                ],
                'context': {'create': False},
            }

    def action_view_partner_payments(self):
        """Open partner payments based on picking type"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        all_payments = self.env['account.payment'].search([
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
        ])

        payment_type = 'inbound' if self.picking_type_id.code == 'outgoing' else 'outbound'

        if not all_payments:
            return {
                'name': f'Paid Invoices - {self.partner_id.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [
                    ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                    ('payment_state', 'in', ['paid', 'in_payment', 'partial']),
                    ('state', '=', 'posted'),
                ],
                'context': {'create': False},
            }

        return {
            'name': f'Payments - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('payment_type', '=', payment_type),
            ],
            'context': {
                'create': False,
                'default_partner_id': self.partner_id.id,
                'default_payment_type': payment_type,
            },
        }