# import time
# from odoo import api, models, fields, _
# from odoo.exceptions import UserError
# from odoo.tools import float_is_zero
# from datetime import datetime
# from dateutil.relativedelta import relativedelta
#
#
# class ReportAgedPartnerBalanceCustom(models.AbstractModel):
#     """
#     Inherited Aged Partner Balance Report with custom features
#     """
#     _inherit = 'report.accounting_pdf_reports.report_agedpartnerbalance'
#     _description = 'Custom Aged Partner Balance Report'
#
#     def _get_partner_move_lines(self, account_type, partner_ids,
#                                 date_from, target_move, period_length):
#         """
#         Override the parent method to add custom functionality
#
#         Example customizations:
#         1. Add additional partner fields (email, phone, etc.)
#         2. Filter by partner tags
#         3. Add custom aging logic
#         4. Include additional currency conversions
#         """
#
#         # Call the parent method to get base data
#         res, total, lines = super(ReportAgedPartnerBalanceCustom, self)._get_partner_move_lines(
#             account_type, partner_ids, date_from, target_move, period_length
#         )
#
#         # CUSTOMIZATION 1: Add additional partner information
#         for partner_data in res:
#             if partner_data.get('partner_id'):
#                 partner = self.env['res.partner'].browse(partner_data['partner_id'])
#                 # Add custom fields
#                 partner_data['email'] = partner.email or ''
#                 partner_data['phone'] = partner.phone or ''
#                 partner_data['vat'] = partner.vat or ''
#                 partner_data['ref'] = partner.ref or ''
#                 partner_data['city'] = partner.city or ''
#                 partner_data['country'] = partner.country_id.name if partner.country_id else ''
#
#                 # Add custom category or tags if needed
#                 partner_data['category_names'] = ', '.join(partner.category_id.mapped('name'))
#
#         # CUSTOMIZATION 2: Sort results by total amount (highest first)
#         # Uncomment if you want to sort by total debt
#         # res = sorted(res, key=lambda x: abs(x.get('total', 0)), reverse=True)
#
#         # CUSTOMIZATION 3: Filter out partners with zero balance
#         # Uncomment if you want to exclude zero balance partners
#         # res = [r for r in res if not float_is_zero(r.get('total', 0),
#         #        precision_rounding=self.env.user.company_id.currency_id.rounding)]
#
#         return res, total, lines
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         """
#         Override to add custom report values and context
#         """
#         # Call parent method
#         result = super(ReportAgedPartnerBalanceCustom, self)._get_report_values(docids, data)
#
#         # CUSTOMIZATION 4: Add additional report data
#         result['company_name'] = self.env.company.name
#         result['report_date'] = fields.Date.today()
#         result['user_name'] = self.env.user.name
#
#         # CUSTOMIZATION 5: Add custom totals or calculations
#         partner_lines = result.get('get_partner_lines', [])
#
#         # Calculate additional statistics
#         total_partners = len(partner_lines)
#         partners_with_overdue = sum(1 for p in partner_lines
#                                     if any(p.get(str(i), 0) != 0 for i in range(5)))
#
#         result['total_partners'] = total_partners
#         result['partners_with_overdue'] = partners_with_overdue
#
#         # CUSTOMIZATION 6: Add percentage calculations
#         directions = result.get('get_direction', [])
#         if directions and len(directions) > 5:
#             grand_total = directions[5]
#             if grand_total != 0:
#                 result['percentage_breakdown'] = {
#                     'not_due': (directions[6] / grand_total * 100) if grand_total else 0,
#                     'period_0': (directions[0] / grand_total * 100) if grand_total else 0,
#                     'period_1': (directions[1] / grand_total * 100) if grand_total else 0,
#                     'period_2': (directions[2] / grand_total * 100) if grand_total else 0,
#                     'period_3': (directions[3] / grand_total * 100) if grand_total else 0,
#                     'period_4': (directions[4] / grand_total * 100) if grand_total else 0,
#                 }
#
#         return result
#
#     def _get_aging_periods_custom(self, date_from, period_length):
#         """
#         Custom method for different aging period calculations
#         You can call this if you want completely custom periods
#         """
#         periods = {}
#         start = datetime.strptime(str(date_from), "%Y-%m-%d")
#
#         # Example: Custom period names and lengths
#         custom_periods = [
#             {'days': 30, 'name': '0-30 Days'},
#             {'days': 30, 'name': '31-60 Days'},
#             {'days': 30, 'name': '61-90 Days'},
#             {'days': 60, 'name': '91-150 Days'},
#             {'days': None, 'name': 'Over 150 Days'},
#         ]
#
#         for i, period_config in enumerate(custom_periods):
#             if period_config['days']:
#                 stop = start - relativedelta(days=period_config['days'])
#                 periods[str(i)] = {
#                     'name': period_config['name'],
#                     'stop': (start - relativedelta(days=1)).strftime('%Y-%m-%d'),
#                     'start': stop.strftime('%Y-%m-%d'),
#                 }
#                 start = stop
#             else:
#                 # Last period (all older items)
#                 periods[str(i)] = {
#                     'name': period_config['name'],
#                     'stop': (start - relativedelta(days=1)).strftime('%Y-%m-%d'),
#                     'start': False,
#                 }
#
#         return periods


import time
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime
from dateutil.relativedelta import relativedelta


class ReportAgedPartnerBalanceCustom(models.AbstractModel):
    """
    Inherited Aged Partner Balance Report with custom features
    """
    _inherit = 'report.accounting_pdf_reports.report_agedpartnerbalance'
    _description = 'Custom Aged Partner Balance Report'

    def _get_partner_move_lines(self, account_type, partner_ids,
                                date_from, target_move, period_length):
        """
        Override the parent method to add custom functionality
        """
        # Call the parent method to get base data
        res, total, lines = super(ReportAgedPartnerBalanceCustom, self)._get_partner_move_lines(
            account_type, partner_ids, date_from, target_move, period_length
        )

        # CUSTOMIZATION 1: Add additional partner information
        for partner_data in res:
            if partner_data.get('partner_id'):
                partner = self.env['res.partner'].browse(partner_data['partner_id'])
                # Add custom fields
                partner_data['email'] = partner.email or ''
                partner_data['phone'] = partner.phone or ''
                partner_data['vat'] = partner.vat or ''
                partner_data['ref'] = partner.ref or ''
                partner_data['city'] = partner.city or ''
                partner_data['country'] = partner.country_id.name if partner.country_id else ''
                partner_data['category_names'] = ', '.join(partner.category_id.mapped('name'))

        return res, total, lines

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Override to add custom report values and context
        """
        # Call parent method
        result = super(ReportAgedPartnerBalanceCustom, self)._get_report_values(docids, data)

        # Add custom report type identifier
        result['report_type'] = data.get('result_selection', 'customer') if data else 'customer'
        result['company_name'] = self.env.company.name
        result['report_date'] = fields.Date.today()
        result['user_name'] = self.env.user.name

        # Calculate additional statistics
        partner_lines = result.get('get_partner_lines', [])
        total_partners = len(partner_lines)
        partners_with_overdue = sum(1 for p in partner_lines
                                    if any(p.get(str(i), 0) != 0 for i in range(5)))

        result['total_partners'] = total_partners
        result['partners_with_overdue'] = partners_with_overdue

        # Add percentage calculations
        directions = result.get('get_direction', [])
        if directions and len(directions) > 5:
            grand_total = directions[5]
            if grand_total != 0:
                result['percentage_breakdown'] = {
                    'not_due': (directions[6] / grand_total * 100) if grand_total else 0,
                    'period_0': (directions[0] / grand_total * 100) if grand_total else 0,
                    'period_1': (directions[1] / grand_total * 100) if grand_total else 0,
                    'period_2': (directions[2] / grand_total * 100) if grand_total else 0,
                    'period_3': (directions[3] / grand_total * 100) if grand_total else 0,
                    'period_4': (directions[4] / grand_total * 100) if grand_total else 0,
                }

        return result