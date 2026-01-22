# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # New fields
    quick_invoice_mode = fields.Boolean(
        string='Quick Invoice Mode',
        default=False,
        help='Indicates this order was created via Quick Invoice'
    )

    requires_approval = fields.Boolean(
        string='Requires Approval',
        compute='_compute_requires_approval',
        store=True,
    )

    stock_availability_status = fields.Selection([
        ('available', 'Fully Available'),
        ('partial', 'Partially Available'),
        ('none', 'Out of Stock'),
    ], string='Stock Status', compute='_compute_stock_availability')

    stock_warning_message = fields.Text(
        string='Stock Warning',
        compute='_compute_stock_availability',
    )

    # ============================================
    # Default Values for Quick Invoice
    # ============================================
    @api.model
    def default_get(self, fields_list):
        """Set default values for quick invoice mode"""
        res = super().default_get(fields_list)

        # If opening from quick invoice context
        if self.env.context.get('quick_invoice_view'):
            res['quick_invoice_mode'] = True

            # Set Walk-in Customer as default
            walkin = self.env['res.partner'].search([
                ('name', '=', 'Walk-in Customer')
            ], limit=1)

            if walkin:
                res['partner_id'] = walkin.id

        return res

    # ============================================
    # DEMERIT #1: Approval Workflow
    # ============================================
    @api.depends('amount_total')
    def _compute_requires_approval(self):
        """Check if order exceeds approval threshold"""
        ICP = self.env['ir.config_parameter'].sudo()
        approval_required = ICP.get_param(
            'quick_invoice_pro.approval_required',
            default='True'
        ) == 'True'
        threshold = float(ICP.get_param(
            'quick_invoice_pro.approval_threshold',
            default='500.0'
        ))

        for order in self:
            order.requires_approval = (
                    approval_required and
                    order.amount_total > threshold
            )

    def _check_approval_rights(self):
        """Check if user has approval rights"""
        if not self.env.user.has_group('quick_invoice_pro.group_quick_invoice_manager'):
            raise AccessError(_(
                'This order requires manager approval. '
                'Please contact your supervisor.'
            ))

    # ============================================
    # DEMERIT #2: Stock Availability Check
    # ============================================
    @api.depends('order_line.product_id', 'order_line.product_uom_qty')
    def _compute_stock_availability(self):
        """Real-time stock availability check"""
        for order in self:
            if not order.order_line:
                order.stock_availability_status = 'available'
                order.stock_warning_message = False
                continue

            warnings = []
            has_stockable = False
            all_available = True
            any_available = False

            for line in order.order_line:
                product = line.product_id

                # Skip services and consumables - FIXED FOR ODOO 19
                if product.type != 'product':
                    continue

                has_stockable = True
                available_qty = product.with_context(
                    warehouse=order.warehouse_id.id
                ).qty_available

                required_qty = line.product_uom_qty

                if available_qty <= 0:
                    all_available = False
                    warnings.append(
                        f"• {product.name}: OUT OF STOCK "
                        f"(Need: {required_qty:.0f}, Available: 0)"
                    )
                elif available_qty < required_qty:
                    all_available = False
                    any_available = True
                    warnings.append(
                        f"• {product.name}: PARTIAL STOCK "
                        f"(Need: {required_qty:.0f}, Available: {available_qty:.0f})"
                    )
                else:
                    any_available = True

            # Set status
            if not has_stockable:
                order.stock_availability_status = 'available'
                order.stock_warning_message = False
            elif all_available:
                order.stock_availability_status = 'available'
                order.stock_warning_message = False
            elif any_available:
                order.stock_availability_status = 'partial'
                order.stock_warning_message = '\n'.join(warnings)
            else:
                order.stock_availability_status = 'none'
                order.stock_warning_message = '\n'.join(warnings)

    def _validate_stock_before_invoice(self):
        """Validate stock based on configuration"""
        self.ensure_one()

        ICP = self.env['ir.config_parameter'].sudo()
        check_stock = ICP.get_param(
            'quick_invoice_pro.check_stock',
            default='True'
        ) == 'True'

        if not check_stock:
            return True

        partial_policy = ICP.get_param(
            'quick_invoice_pro.partial_delivery',
            default='warn'
        )

        if self.stock_availability_status == 'none':
            if partial_policy == 'block':
                raise UserError(_(
                    'Cannot create invoice: No stock available\n\n%s'
                ) % self.stock_warning_message)
            elif partial_policy == 'warn':
                return {
                    'warning': {
                        'title': _('Stock Warning'),
                        'message': self.stock_warning_message +
                                   _('\n\nDo you want to continue?')
                    }
                }

        elif self.stock_availability_status == 'partial':
            if partial_policy == 'block':
                raise UserError(_(
                    'Cannot create invoice: Insufficient stock\n\n%s'
                ) % self.stock_warning_message)
            elif partial_policy == 'warn':
                return {
                    'warning': {
                        'title': _('Partial Stock Available'),
                        'message': self.stock_warning_message +
                                   _('\n\nPartial delivery will be created.')
                    }
                }

        return True

    # ============================================
    # DEMERIT #3: Draft Invoice Option
    # ============================================
    def action_quick_invoice_draft(self):
        """Create invoice in draft state for review"""
        return self._create_quick_invoice(draft=True)

    def action_quick_invoice_posted(self):
        """Create and post invoice immediately"""
        return self._create_quick_invoice(draft=False)

    # ============================================
    # Main Quick Invoice Method
    # ============================================
    def _create_quick_invoice(self, draft=True):
        """
        Core method to create invoice with all validations
        Handles demerits #1, #2, #3
        """
        self.ensure_one()

        # Validation 1: Check if already invoiced
        if self.invoice_status == 'invoiced':
            raise UserError(_('This order is already fully invoiced.'))

        # Validation 2: Check approval requirement (Demerit #1)
        if self.requires_approval and self.state == 'draft':
            self._check_approval_rights()

        # Validation 3: Check stock availability (Demerit #2)
        stock_check = self._validate_stock_before_invoice()
        if isinstance(stock_check, dict) and 'warning' in stock_check:
            # Return warning to wizard
            return stock_check

        # Step 1: Confirm sale order if in draft
        if self.state == 'draft':
            self.action_confirm()

        # Step 2: Create invoice
        invoice_vals = self._prepare_invoice()
        invoice = self.env['account.move'].sudo().create(invoice_vals)

        # Step 3: Create invoice lines
        for line in self.order_line:
            if line.product_uom_qty > 0 or line.price_unit != 0:
                line._create_invoice_line(invoice)

        # Step 4: Compute taxes
        invoice._recompute_dynamic_lines()

        # Step 5: Post invoice if not draft mode (Demerit #3)
        if not draft:
            ICP = self.env['ir.config_parameter'].sudo()
            allow_draft = ICP.get_param(
                'quick_invoice_pro.allow_draft',
                default='True'
            ) == 'True'

            if not allow_draft:
                invoice.action_post()

        # Mark as quick invoice
        self.quick_invoice_mode = True

        # Step 6: Open payment wizard (Demerit #4)
        ICP = self.env['ir.config_parameter'].sudo()
        auto_payment = ICP.get_param(
            'quick_invoice_pro.auto_payment',
            default='True'
        ) == 'True'

        if auto_payment and not draft:
            return self._open_payment_wizard(invoice)

        # Return invoice form view
        return {
            'name': _('Quick Invoice Created'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_quick_invoice_mode': True,
            }
        }

    # ============================================
    # DEMERIT #4: Payment Integration
    # ============================================
    def _open_payment_wizard(self, invoice):
        """Open payment wizard after invoice creation"""
        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'quick.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': invoice.id,
                'default_amount': invoice.amount_total,
                'default_sale_order_id': self.id,
            }
        }

    # ============================================
    # DEMERIT #5: Quick Return
    # ============================================
    def action_quick_return(self):
        """Open quick return wizard"""
        self.ensure_one()

        if not self.invoice_ids:
            raise UserError(_('No invoices found to return.'))

        return {
            'name': _('Quick Return'),
            'type': 'ir.actions.act_window',
            'res_model': 'quick.return.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_invoice_ids': [(6, 0, self.invoice_ids.ids)],
            }
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    available_qty = fields.Float(
        string='Available Qty',
        compute='_compute_available_qty',
    )

    @api.depends('product_id', 'order_id.warehouse_id')
    def _compute_available_qty(self):
        """Show available stock on order line"""
        for line in self:
            # FIXED FOR ODOO 19 - Changed detailed_type to type
            if line.product_id.type == 'product':
                line.available_qty = line.product_id.with_context(
                    warehouse=line.order_id.warehouse_id.id
                ).qty_available
            else:
                line.available_qty = 0