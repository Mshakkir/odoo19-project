# from odoo import fields, models, api, _
#
#
# class AccountPartnerLedger(models.TransientModel):
#     _name = "account.report.partner.ledger"
#     _inherit = "account.common.partner.report"
#     _description = "Account Partner Ledger"
#
#     amount_currency = fields.Boolean("With Currency",
#                                      help="It adds the currency column on "
#                                           "report if the currency differs from "
#                                           "the company currency.")
#     reconciled = fields.Boolean('Reconciled Entries')
#
#     def _get_report_data(self, data):
#         data = self.pre_print_report(data)
#         data['form'].update({'reconciled': self.reconciled,
#                              'amount_currency': self.amount_currency})
#         return data
#
#     def _print_report(self, data):
#         data = self._get_report_data(data)
#         return self.env.ref('accounting_pdf_reports.action_report_partnerledger').with_context(landscape=True).\
#             report_action(self, data=data)

#i get the same reconciliation items excluded then i change the code and also change the custom module wizard code
from odoo import fields, models, api, _


class AccountPartnerLedger(models.TransientModel):
    _name = "account.report.partner.ledger"
    _inherit = "account.common.partner.report"
    _description = "Account Partner Ledger"

    amount_currency = fields.Boolean(
        "With Currency",
        help="It adds the currency column on report if the currency differs from the company currency."
    )

    reconciled = fields.Selection([
        ('all', 'All Entries'),
        ('reconciled', 'Reconciled Entries Only'),
        ('unreconciled', 'Unreconciled Entries Only')
    ],
        string='Reconciliation Filter',
        default='all',
        help="Filter entries by reconciliation status:\n"
             "- All Entries: Show both reconciled and unreconciled\n"
             "- Reconciled Only: Show only entries that have been reconciled\n"
             "- Unreconciled Only: Show only entries that have NOT been reconciled"
    )

    def _get_report_data(self, data):
        data = self.pre_print_report(data)
        data['form'].update({
            'reconciled': self.reconciled,
            'amount_currency': self.amount_currency
        })
        return data

    def _print_report(self, data):
        data = self._get_report_data(data)
        return self.env.ref('accounting_pdf_reports.action_report_partnerledger').with_context(landscape=True). \
            report_action(self, data=data)