from odoo import models, fields, api


class AccountTaxReportWizard(models.TransientModel):
    _inherit = 'account.tax.report.wizard'

    detail_line_ids = fields.One2many('tax.report.detail.line', 'wizard_id', string='Tax Summary Lines')

    def compute_tax_summary(self):
        self.ensure_one()
        TaxLine = self.env['tax.report.detail.line']
        self.detail_line_ids.unlink()

        sequence = 10
        total_sales_base = 0.0
        total_sales_tax = 0.0
        total_purchase_base = 0.0
        total_purchase_tax = 0.0

        # Domain for account.move.line
        domain = [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('parent_state', '=', 'posted'),
            ('tax_line_id', '!=', False),
        ]

        # Get all tax lines
        tax_lines = self.env['account.move.line'].search(domain)

        # Group by tax
        tax_summary = {}
        for line in tax_lines:
            tax = line.tax_line_id
            if not tax:
                continue

            tax_type = tax.type_tax_use
            if tax_type not in ['sale', 'purchase']:
                continue

            key = (tax.id, tax_type)
            if key not in tax_summary:
                tax_summary[key] = {
                    'tax_id': tax.id,
                    'tax_name': tax.name,
                    'type': tax_type,
                    'base_amount': 0.0,
                    'tax_amount': 0.0,
                    'moves': set(),
                    'sequence': sequence,
                }
                sequence += 10

            # Add base and tax amounts (use absolute values and check credit/debit)
            tax_summary[key]['base_amount'] += abs(line.tax_base_amount)

            # For tax amount: credit means incoming (sales), debit means outgoing (purchases)
            if tax_type == 'sale':
                # Sales tax is typically in credit
                tax_summary[key]['tax_amount'] += line.credit - line.debit
            else:  # purchase
                # Purchase tax is typically in debit
                tax_summary[key]['tax_amount'] += line.debit - line.credit

            # Track moves
            tax_summary[key]['moves'].add(line.move_id.id)

        # Create Sales tax lines
        for (tax_id, tax_type), vals in sorted(tax_summary.items(), key=lambda x: x[1]['sequence']):
            if tax_type == 'sale':
                TaxLine.create({
                    'wizard_id': self.id,
                    'type': tax_type,
                    'tax_id': tax_id,
                    'tax_name': vals['tax_name'],
                    'base_amount': vals['base_amount'],
                    'tax_amount': vals['tax_amount'],
                    'move_ids': [(6, 0, list(vals['moves']))],
                    'is_summary_row': False,
                    'sequence': vals['sequence'],
                })
                total_sales_base += vals['base_amount']
                total_sales_tax += vals['tax_amount']

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

        # Create Purchase tax lines
        for (tax_id, tax_type), vals in sorted(tax_summary.items(), key=lambda x: x[1]['sequence']):
            if tax_type == 'purchase':
                TaxLine.create({
                    'wizard_id': self.id,
                    'type': tax_type,
                    'tax_id': tax_id,
                    'tax_name': vals['tax_name'],
                    'base_amount': vals['base_amount'],
                    'tax_amount': vals['tax_amount'],
                    'move_ids': [(6, 0, list(vals['moves']))],
                    'is_summary_row': False,
                    'sequence': vals['sequence'],
                })
                total_purchase_base += vals['base_amount']
                total_purchase_tax += vals['tax_amount']

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
        # Net VAT Due = Total Sales Tax - Total Purchase Tax
        net_vat_due = total_sales_tax - total_purchase_tax
        TaxLine.create({
            'wizard_id': self.id,
            'tax_name': 'Net VAT Due',
            'base_amount': 0.0,
            'tax_amount': net_vat_due,
            'is_summary_row': True,
            'sequence': sequence,
        })

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