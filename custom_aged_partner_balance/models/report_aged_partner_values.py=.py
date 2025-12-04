from odoo import api, models


class ReportAgedPartnerBalance(models.AbstractModel):
    """
    Inherit the abstract report model to add custom calculations
    for partners_with_overdue and percentage_breakdown
    """
    _inherit = 'report.accounting_pdf_reports.report_agedpartnerbalance'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Override to add partners_with_overdue and total_partners counts
        """
        # Get the original report values from parent
        result = super()._get_report_values(docids, data)

        # Get partner lines from the report
        partner_lines = result.get('get_partner_lines', [])

        # Calculate partners with overdue
        partners_with_overdue = 0
        total_partners = len(partner_lines)

        for partner in partner_lines:
            # Check if partner has any overdue amounts (periods 0-4)
            # A partner has overdue if ANY of the aging periods (0-4) have non-zero amounts
            has_overdue = False
            for period_key in ['0', '1', '2', '3', '4']:
                if partner.get(period_key, 0.0) != 0.0:
                    has_overdue = True
                    break

            if has_overdue:
                partners_with_overdue += 1

        # Add calculated values to result
        result['partners_with_overdue'] = partners_with_overdue
        result['total_partners'] = total_partners

        # Calculate percentage breakdown for aging analysis
        direction = result.get('get_direction', [])
        if direction and len(direction) > 5:
            total = direction[5]  # Total amount at index 5

            percentage_breakdown = {}
            if total and total != 0:
                # Not due (index 6)
                percentage_breakdown['not_due'] = (direction[6] / total * 100) if len(direction) > 6 else 0
                # Periods 0-4 (indices 0-4)
                for i in range(5):
                    percentage_breakdown[f'period_{i}'] = (direction[i] / total * 100) if direction[i] else 0
            else:
                # If total is 0, all percentages are 0
                percentage_breakdown = {
                    'not_due': 0,
                    'period_0': 0,
                    'period_1': 0,
                    'period_2': 0,
                    'period_3': 0,
                    'period_4': 0,
                }

            result['percentage_breakdown'] = percentage_breakdown
        else:
            result['percentage_breakdown'] = {
                'not_due': 0,
                'period_0': 0,
                'period_1': 0,
                'period_2': 0,
                'period_3': 0,
                'period_4': 0,
            }

        return result