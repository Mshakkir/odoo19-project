# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class QuickReturnLine(models.TransientModel):
    """Define this FIRST so it exists when QuickReturnWizard references it"""
    _name = 'quick.return.line'
    _description = 'Quick Return Line'

    wizard_id = fields.Many2one(
        'quick.return.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        readonly=True,
    )

    ordered_qty = fields.Float(
        string='Ordered Quantity',
        readonly=True,
    )

    return_qty = fields.Float(
        string='Return Quantity',
        required=True,
    )

    price_unit = fields.Float(
        string='Unit Price',
        readonly=True,
    )

    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True,
    )

    @api.depends('return_qty', 'price_unit')
    def _compute_subtotal(self):
        """Calculate subtotal for return line"""
        for line in self:
            line.subtotal = line.return_qty * line.price_unit


class QuickReturnWizard(models.TransientModel):
    _name = 'quick.return.wizard'
    _description = 'Quick Return/Refund Wizard'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Original Sale Order',
        required=True,
        readonly=True,
    )

    invoice_ids = fields.Many2many(
        'account.move',
        string='Invoices to Return',
        domain="[('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]",
    )

    return_type = fields.Selection([
        ('full', 'Full Return'),
        ('partial', 'Partial Return'),
    ], string='Return Type', default='full', required=True)

    return_line_ids = fields.One2many(
        'quick.return.line',
        'wizard_id',
        string='Return Lines',
    )

    reason = fields.Text(
        string='Return Reason',
        required=True,
    )

    create_credit_note = fields.Boolean(
        string='Create Credit Note',
        default=True,
    )

    reverse_delivery = fields.Boolean(
        string='Reverse Delivery (Create Return Picking)',
        default=True,
    )

    refund_method = fields.Selection([
        ('refund', 'Create credit note'),
        ('cancel', 'Cancel invoice'),
        ('modify', 'Modify invoice'),
    ], string='Refund Method', default='refund', required=True)

    @api.onchange('sale_order_id', 'return_type')
    def _onchange_sale_order(self):
        """Populate return lines from sale order"""
        if self.sale_order_id:
            lines = []
            for line in self.sale_order_id.order_line:
                if line.product_uom_qty > 0:
                    lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'ordered_qty': line.product_uom_qty,
                        'return_qty': line.product_uom_qty if self.return_type == 'full' else 0,
                        'price_unit': line.price_unit,
                    }))
            self.return_line_ids = lines

    def action_process_return(self):
        """Process the return/refund"""
        self.ensure_one()

        if not self.return_line_ids:
            raise UserError(_('Please add products to return.'))

        # Validate return quantities
        for line in self.return_line_ids:
            if line.return_qty > line.ordered_qty:
                raise UserError(_(
                    'Return quantity for %s cannot exceed ordered quantity.'
                ) % line.product_id.name)

        # Step 1: Create credit note
        if self.create_credit_note and self.invoice_ids:
            credit_note = self._create_credit_note()
        else:
            credit_note = None

        # Step 2: Create return picking
        if self.reverse_delivery:
            return_picking = self._create_return_picking()
        else:
            return_picking = None

        # Step 3: Show success message
        message = _('Return processed successfully!\n\n')

        if credit_note:
            message += _('Credit Note: %s\n') % credit_note.name

        if return_picking:
            message += _('Return Delivery: %s\n') % return_picking.name

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Return Processed'),
                'message': message,
                'type': 'success',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'res_id': credit_note.id if credit_note else False,
                    'view_mode': 'form',
                } if credit_note else {
                    'type': 'ir.actions.act_window',
                    'res_model': 'sale.order',
                    'res_id': self.sale_order_id.id,
                    'view_mode': 'form',
                }
            }
        }

    def _create_credit_note(self):
        """Create credit note for returned items"""
        invoice = self.invoice_ids[0]

        # Use Odoo's standard reverse move method
        move_reversal = self.env['account.move.reversal'].with_context(
            active_model='account.move',
            active_ids=invoice.ids,
        ).create({
            'date': fields.Date.today(),
            'reason': self.reason,
            'refund_method': self.refund_method,
            'journal_id': invoice.journal_id.id,
        })

        reversal = move_reversal.reverse_moves()
        credit_note = self.env['account.move'].browse(reversal['res_id'])

        # Adjust quantities for partial returns
        if self.return_type == 'partial':
            for line in credit_note.invoice_line_ids:
                return_line = self.return_line_ids.filtered(
                    lambda l: l.product_id == line.product_id
                )
                if return_line:
                    line.quantity = return_line[0].return_qty

            credit_note._recompute_dynamic_lines()

        return credit_note

    def _create_return_picking(self):
        """Create return picking (reverse delivery)"""
        pickings = self.sale_order_id.picking_ids.filtered(
            lambda p: p.state == 'done' and p.picking_type_code == 'outgoing'
        )

        if not pickings:
            return None

        picking = pickings[0]

        # Create return picking wizard
        return_wizard = self.env['stock.return.picking'].with_context(
            active_id=picking.id,
            active_model='stock.picking',
        ).create({
            'picking_id': picking.id,
        })

        # Adjust return quantities
        if self.return_type == 'partial':
            for line in return_wizard.product_return_moves:
                return_line = self.return_line_ids.filtered(
                    lambda l: l.product_id == line.product_id
                )
                if return_line:
                    line.quantity = return_line[0].return_qty

        # Create return
        result = return_wizard.create_returns()
        return_picking = self.env['stock.picking'].browse(result['res_id'])

        return return_picking