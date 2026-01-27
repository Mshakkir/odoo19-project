from odoo import models, fields, api
from odoo.exceptions import UserError


class MultiSaleInvoiceWizard(models.TransientModel):
    _name = 'multi.sale.invoice.wizard'
    _description = 'Create Invoice from Multiple Sale Orders'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        readonly=True,
        help="Customer for the selected sale orders"
    )

    sale_order_line_ids = fields.One2many(
        'multi.sale.invoice.wizard.line',
        'wizard_id',
        string='Sale Orders'
    )

    invoice_date = fields.Date(
        string='Invoice Date',
        default=fields.Date.context_today,
        required=True
    )

    @api.model
    def default_get(self, fields_list):
        """Load sale orders from context"""
        res = super(MultiSaleInvoiceWizard, self).default_get(fields_list)

        # Get sale orders from context
        sale_order_ids = self.env.context.get('active_ids', [])
        sale_orders = self.env['sale.order'].browse(sale_order_ids)

        if not sale_orders:
            raise UserError("No sale orders selected!")

        # Check if all sale orders have the same customer
        partners = sale_orders.mapped('partner_id')
        if len(partners) > 1:
            raise UserError("All selected sale orders must have the same customer!")

        res['partner_id'] = partners[0].id

        # Create wizard lines
        lines = []
        for order in sale_orders:
            if order.invoice_status in ['to invoice', 'invoiced']:
                lines.append((0, 0, {
                    'sale_order_id': order.id,
                    'selected': True,
                    'order_date': order.date_order,
                    'amount_total': order.amount_total,
                    'invoice_status': order.invoice_status,
                }))

        res['sale_order_line_ids'] = lines

        return res

    def action_create_invoice(self):
        """Create combined invoice from selected sale orders"""
        self.ensure_one()

        # Get selected sale orders
        selected_orders = self.sale_order_line_ids.filtered(lambda l: l.selected).mapped('sale_order_id')

        if not selected_orders:
            raise UserError("Please select at least one sale order!")

        # Check if all orders have the same customer
        partners = selected_orders.mapped('partner_id')
        if len(partners) > 1:
            raise UserError("All selected sale orders must have the same customer!")

        # Create invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': partners[0].id,
            'invoice_date': self.invoice_date,
            'invoice_origin': ', '.join(selected_orders.mapped('name')),
            'invoice_line_ids': [],
        }

        # Collect all invoice lines from selected sale orders
        for order in selected_orders:
            for line in order.order_line:
                # Skip lines without products or display type lines
                if not line.product_id or line.display_type:
                    continue

                # Calculate quantity to invoice
                qty_to_invoice = line.product_uom_qty - line.qty_invoiced

                if qty_to_invoice > 0:
                    # Get account
                    account = line.product_id.property_account_income_id or \
                              line.product_id.categ_id.property_account_income_categ_id

                    invoice_line_vals = {
                        'product_id': line.product_id.id,
                        'name': f"[{order.name}] {line.name}",  # Add SO reference to line description
                        'quantity': qty_to_invoice,
                        'price_unit': line.price_unit,
                        'tax_ids': [(6, 0, line.tax_id.ids)],
                        'sale_line_ids': [(4, line.id)],
                    }

                    if account:
                        invoice_line_vals['account_id'] = account.id

                    invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

        if not invoice_vals['invoice_line_ids']:
            raise UserError("No lines to invoice found in the selected sale orders!")

        # Create the invoice
        invoice = self.env['account.move'].create(invoice_vals)

        # Return action to open the created invoice
        return {
            'name': 'Customer Invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }


class MultiSaleInvoiceWizardLine(models.TransientModel):
    _name = 'multi.sale.invoice.wizard.line'
    _description = 'Multi Sale Invoice Wizard Line'

    wizard_id = fields.Many2one(
        'multi.sale.invoice.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True
    )

    selected = fields.Boolean(
        string='Select',
        default=True
    )

    order_date = fields.Datetime(
        string='Order Date',
        related='sale_order_id.date_order',
        readonly=True
    )

    amount_total = fields.Monetary(
        string='Total',
        related='sale_order_id.amount_total',
        readonly=True
    )

    currency_id = fields.Many2one(
        string='Currency',
        related='sale_order_id.currency_id',
        readonly=True
    )

    invoice_status = fields.Selection(
        string='Invoice Status',
        related='sale_order_id.invoice_status',
        readonly=True
    )