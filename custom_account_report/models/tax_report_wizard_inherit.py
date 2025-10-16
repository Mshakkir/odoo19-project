from odoo import models, fields, api


class AccountTaxReportWizard(models.TransientModel):
    _inherit = 'account.tax.report.wizard'

    detail_line_ids = fields.One2many('tax.report.detail.line', 'wizard_id', string='Tax Summary Lines')

    def compute_tax_summary(self):
        self.ensure_one()
        TaxLine = self.env['tax.report.detail.line']
        self.detail_line_ids.unlink()

        # Get the same data that the PDF report uses
        report_data = self._get_tax_report_data()

        sequence = 10
        total_sales_base = 0.0
        total_sales_tax = 0.0
        total_purchase_base = 0.0
        total_purchase_tax = 0.0

        # Process Sales
        if 'sale_taxes' in report_data:
            for tax_data in report_data['sale_taxes']:
                # Get the move IDs for this tax
                move_ids = self._get_moves_for_tax(tax_data['tax_id'], 'sale')

                TaxLine.create({
                    'wizard_id': self.id,
                    'type': 'sale',
                    'tax_id': tax_data['tax_id'],
                    'tax_name': tax_data['tax_name'],
                    'base_amount': tax_data.get('base_amount', 0.0),
                    'tax_amount': tax_data.get('tax_amount', 0.0),
                    'move_ids': [(6, 0, move_ids)],
                    'is_summary_row': False,
                    'sequence': sequence,
                })
                total_sales_base += tax_data.get('base_amount', 0.0)
                total_sales_tax += tax_data.get('tax_amount', 0.0)
                sequence += 10

        # Add Total Sales Summary Row
        TaxLine.create({
            'wizard_id': self.id,
            'type': 'sale',
            'tax_name': 'Total Sales',
            'base_amount': total_sales_base,
            'tax_amount': total_sales_tax,
            'is_summary_row': True,
            'sequence': sequence,
        })
        sequence += 10

        # Process Purchases
        if 'purchase_taxes' in report_data:
            for tax_data in report_data['purchase_taxes']:
                # Get the move IDs for this tax
                move_ids = self._get_moves_for_tax(tax_data['tax_id'], 'purchase')

                TaxLine.create({
                    'wizard_id': self.id,
                    'type': 'purchase',
                    'tax_id': tax_data['tax_id'],
                    'tax_name': tax_data['tax_name'],
                    'base_amount': tax_data.get('base_amount', 0.0),
                    'tax_amount': tax_data.get('tax_amount', 0.0),
                    'move_ids': [(6, 0, move_ids)],
                    'is_summary_row': False,
                    'sequence': sequence,
                })
                total_purchase_base += tax_data.get('base_amount', 0.0)
                total_purchase_tax += tax_data.get('tax_amount', 0.0)
                sequence += 10

        # Add Total Purchases Summary Row
        TaxLine.create({
            'wizard_id': self.id,
            'type': 'purchase',
            'tax_name': 'Total Purchases',
            'base_amount': total_purchase_base,
            'tax_amount': total_purchase_tax,
            'is_summary_row': True,
            'sequence': sequence,
        })
        sequence += 10

        # Add Net VAT Due Summary Row
        net_vat_due = total_sales_tax - total_purchase_tax
        TaxLine.create({
            'wizard_id': self.id,
            'tax_name': 'Net VAT Due',
            'base_amount': 0.0,
            'tax_amount': net_vat_due,
            'is_summary_row': True,
            'sequence': sequence,
        })

    def _get_tax_report_data(self):
        """Get the same tax data that the PDF report uses"""
        self.ensure_one()

        # Use the existing check_report method's logic
        # This is the same method that generates the PDF
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.company_id.id,
        }

        # Get tax data using Odoo's tax report engine
        taxes_data = self._compute_taxes_data()

        return taxes_data

    def _compute_taxes_data(self):
        """Compute tax data the same way as the PDF report"""
        self.ensure_one()

        sale_taxes = []
        purchase_taxes = []

        domain = [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('parent_state', '=', 'posted'),
        ]

        # Get all tax lines from account.move.line
        tax_lines = self.env['account.move.line'].search(domain + [('tax_line_id', '!=', False)])

        # Group by tax
        tax_summary = {}
        for line in tax_lines:
            tax = line.tax_line_id
            if not tax:
                continue

            key = tax.id
            if key not in tax_summary:
                tax_summary[key] = {
                    'tax_id': tax.id,
                    'tax_name': tax.name,
                    'type': tax.type_tax_use,
                    'base_amount': 0.0,
                    'tax_amount': 0.0,
                }

            # Sum up base and tax amounts
            tax_summary[key]['base_amount'] += abs(line.tax_base_amount)
            tax_summary[key]['tax_amount'] += abs(line.balance) if line.debit > 0 else -abs(line.balance)

        # Separate into sale and purchase
        for tax_id, data in tax_summary.items():
            if data['type'] == 'sale':
                sale_taxes.append(data)
            elif data['type'] == 'purchase':
                purchase_taxes.append(data)

        return {
            'sale_taxes': sale_taxes,
            'purchase_taxes': purchase_taxes,
        }

    def _get_moves_for_tax(self, tax_id, tax_type):
        """Get all move IDs for a specific tax"""
        domain = [
            ('company_id', '=', self.company_id.id),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted'),
        ]

        if tax_type == 'sale':
            domain.append(('move_type', 'in', ['out_invoice', 'out_refund']))
        else:
            domain.append(('move_type', 'in', ['in_invoice', 'in_refund']))

        # Find moves that have this tax
        moves = self.env['account.move'].search(domain)
        move_ids = []

        for move in moves:
            # Check if any line has this tax
            if move.line_ids.filtered(lambda l: l.tax_line_id.id == tax_id):
                move_ids.append(move.id)

        return move_ids

    def open_tax_report_details(self):
        self.compute_tax_summary()
        return {
            'name': 'Tax Report Summary',
            'type': 'ir.actions.act_window',
            'res_model': 'tax.report.detail.line',
            'view_mode': 'list,form',
            'target': 'current',
            'context': {'default_wizard_id': self.id},
            'domain': [('wizard_id', '=', self.id)],
        }