from odoo import models, fields, api


class PurchaseProductReportWizard(models.TransientModel):
    _name = 'purchase.product.report.wizard'
    _description = 'Purchase Product Report Wizard'

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
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        required=True
    )

    def action_show_report(self):
        """Open the report view with filtered data"""
        self.ensure_one()

        # Create the report records
        report_obj = self.env['purchase.product.report']

        # Search for purchase invoice lines matching criteria
        domain = [
            ('move_id.move_type', '=', 'in_invoice'),
            ('move_id.state', '=', 'posted'),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
            ('product_id', 'in', self.product_ids.ids),
        ]

        invoice_lines = self.env['account.move.line'].search(domain)

        # Clear existing report data
        report_obj.search([]).unlink()

        # Create report records
        for line in invoice_lines:
            if line.product_id:
                report_obj.create({
                    'invoice_date': line.move_id.invoice_date,
                    'invoice_number': line.move_id.name,
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'uom_id': line.product_uom_id.id,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal,
                })

        # Return action to open tree view
        return {
            'name': 'Purchase Product Report',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.product.report',
            'view_mode': 'tree',
            'target': 'current',
            'domain': [],
        }