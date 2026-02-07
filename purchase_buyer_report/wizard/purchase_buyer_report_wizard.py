from odoo import models, fields, api


class PurchaseBuyerReportWizard(models.TransientModel):
    _name = 'purchase.buyer.report.wizard'
    _description = 'Purchase Buyer Report Wizard'

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.context_today
    )
    buyer_ids = fields.Many2many(
        'res.users',
        string='Buyers',
        required=True
    )

    def action_show_report(self):
        """Open the report view with filtered data"""
        self.ensure_one()

        # Create the report records
        report_obj = self.env['purchase.buyer.report']

        # Clear existing report data first
        report_obj.search([]).unlink()

        # Get purchase orders created by selected buyers
        purchase_orders = self.env['purchase.order'].search([
            ('user_id', 'in', self.buyer_ids.ids),
        ])

        if not purchase_orders:
            # No purchase orders found for selected buyers
            return {
                'name': 'Purchase Buyer Report',
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.buyer.report',
                'view_mode': 'list',
                'view_id': self.env.ref('purchase_buyer_report.view_purchase_buyer_report_list').id,
                'target': 'current',
                'domain': [],
            }

        # Get all invoice lines related to these purchase orders
        invoice_line_ids = []

        for po in purchase_orders:
            # Get invoices from purchase order
            for invoice in po.invoice_ids:
                # Check if invoice matches our criteria
                if (invoice.move_type == 'in_invoice' and
                        invoice.state == 'posted' and
                        invoice.invoice_date and
                        invoice.invoice_date >= self.date_from and
                        invoice.invoice_date <= self.date_to):

                    # Process invoice lines
                    for line in invoice.invoice_line_ids:
                        if line.product_id:  # Only lines with products
                            report_obj.create({
                                'invoice_date': invoice.invoice_date,
                                'invoice_number': invoice.name,
                                'vendor_id': invoice.partner_id.id,
                                'product_id': line.product_id.id,
                                'quantity': line.quantity,
                                'uom_id': line.product_uom_id.id,
                                'price_unit': line.price_unit,
                                'net_amount': line.price_total,  # Includes tax
                            })

        # Return action to open list view
        return {
            'name': 'Purchase Buyer Report',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.buyer.report',
            'view_mode': 'list',
            'view_id': self.env.ref('purchase_buyer_report.view_purchase_buyer_report_list').id,
            'target': 'current',
            'domain': [],
        }
#
#
#
#
#
#
#
#
#
#
#
#
#
# from odoo import models, fields, api
#
#
# class PurchaseBuyerReportWizard(models.TransientModel):
#     _name = 'purchase.buyer.report.wizard'
#     _description = 'Purchase Buyer Report Wizard'
#
#     date_from = fields.Date(
#         string='Date From',
#         required=True,
#         default=fields.Date.context_today
#     )
#     date_to = fields.Date(
#         string='Date To',
#         required=True,
#         default=fields.Date.context_today
#     )
#     buyer_ids = fields.Many2many(
#         'res.users',
#         string='Buyers',
#         required=True
#     )
#
#     def action_show_report(self):
#         """Open the report view with filtered data"""
#         self.ensure_one()
#
#         # Create the report records
#         report_obj = self.env['purchase.buyer.report']
#
#         # Search for purchase invoice lines matching criteria
#         # Get purchase orders by buyers first
#         purchase_orders = self.env['purchase.order'].search([
#             ('user_id', 'in', self.buyer_ids.ids),
#         ])
#
#         # Get invoice names from purchase orders
#         invoice_origins = purchase_orders.mapped('name')
#
#         # Search for posted invoices linked to these purchase orders
#         domain = [
#             ('move_type', '=', 'in_invoice'),
#             ('state', '=', 'posted'),
#             ('invoice_date', '>=', self.date_from),
#             ('invoice_date', '<=', self.date_to),
#             ('invoice_origin', 'in', invoice_origins),
#         ]
#
#         invoices = self.env['account.move'].search(domain)
#
#         # Clear existing report data
#         report_obj.search([]).unlink()
#
#         # Create report records from invoice lines
#         for invoice in invoices:
#             for line in invoice.invoice_line_ids:
#                 if line.product_id:  # Only lines with products
#                     report_obj.create({
#                         'invoice_date': invoice.invoice_date,
#                         'invoice_number': invoice.name,
#                         'vendor_id': invoice.partner_id.id,
#                         'product_id': line.product_id.id,
#                         'quantity': line.quantity,
#                         'uom_id': line.product_uom_id.id,
#                         'price_unit': line.price_unit,
#                         'net_amount': line.price_total,  # Includes tax
#                     })
#
#         # Return action to open list view
#         return {
#             'name': 'Purchase Buyer Report',
#             'type': 'ir.actions.act_window',
#             'res_model': 'purchase.buyer.report',
#             'view_mode': 'list',
#             'view_id': self.env.ref('purchase_buyer_report.view_purchase_buyer_report_list').id,
#             'target': 'current',
#             'domain': [],
#         }