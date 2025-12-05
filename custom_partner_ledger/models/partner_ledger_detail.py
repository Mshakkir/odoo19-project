# # -*- coding: utf-8 -*-
# from odoo import api, fields, models, _
#
#
# class PartnerLedgerDetail(models.TransientModel):
#     _name = 'partner.ledger.detail'
#     _description = 'Partner Ledger Detail View'
#     _order = 'partner_id, date, id'
#
#     partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
#     date = fields.Date(string='Date', readonly=True)
#     move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)
#     journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
#     account_id = fields.Many2one('account.account', string='Account', readonly=True)
#     name = fields.Char(string='Label', readonly=True)
#     ref = fields.Char(string='Reference', readonly=True)
#     debit = fields.Monetary(string='Debit', readonly=True, currency_field='company_currency_id')
#     credit = fields.Monetary(string='Credit', readonly=True, currency_field='company_currency_id')
#     balance = fields.Monetary(string='Balance', readonly=True, currency_field='company_currency_id')
#     amount_currency = fields.Monetary(string='Amount Currency', readonly=True, currency_field='currency_id')
#     currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
#     company_currency_id = fields.Many2one('res.currency', string='Company Currency', readonly=True)
#     reconcile_id = fields.Many2one('account.full.reconcile', string='Reconcile', readonly=True)
#     move_state = fields.Selection([
#         ('draft', 'Draft'),
#         ('posted', 'Posted'),
#     ], string='Status', readonly=True)
#
#     # For opening balance line
#     is_opening_balance = fields.Boolean(string='Is Opening Balance', readonly=True)
#
#     @api.model
#     def get_partner_ledger_details(self, wizard_data):
#         """
#         Generate partner ledger detail records based on wizard filters
#         """
#         # Clear existing records for this user
#         self.search([]).unlink()
#
#         # Get data from wizard
#         date_from = wizard_data.get('date_from')
#         date_to = wizard_data.get('date_to')
#         partner_ids = wizard_data.get('partner_ids', [])
#         journal_ids = wizard_data.get('journal_ids', [])
#         target_move = wizard_data.get('target_move', 'posted')
#         result_selection = wizard_data.get('result_selection', 'customer')
#         reconciled = wizard_data.get('reconciled', False)
#         amount_currency = wizard_data.get('amount_currency', False)
#
#         # Determine account types
#         if result_selection == 'supplier':
#             account_type = ['liability_payable']
#         elif result_selection == 'customer':
#             account_type = ['asset_receivable']
#         else:
#             account_type = ['liability_payable', 'asset_receivable']
#
#         # Get accounts
#         accounts = self.env['account.account'].search([('account_type', 'in', account_type)])
#         account_ids = accounts.ids
#
#         # Get move states
#         if target_move == 'posted':
#             move_state = ['posted']
#         else:
#             move_state = ['draft', 'posted']
#
#         # Build domain for move lines
#         domain = [
#             ('account_id', 'in', account_ids),
#             ('move_id.state', 'in', move_state),
#         ]
#
#         # Add partner filter
#         if partner_ids:
#             domain.append(('partner_id', 'in', partner_ids))
#         else:
#             domain.append(('partner_id', '!=', False))
#
#         # Add date filters
#         if date_from:
#             domain.append(('date', '>=', date_from))
#
#         if date_to:
#             domain.append(('date', '<=', date_to))
#
#         # Add journal filter
#         if journal_ids:
#             domain.append(('journal_id', 'in', journal_ids))
#
#         # Add reconcile filter
#         if not reconciled:
#             domain.append(('full_reconcile_id', '=', False))
#
#         # Get move lines
#         move_lines = self.env['account.move.line'].search(domain, order='partner_id, date, id')
#
#         # Create detail records
#         detail_records = []
#         partners = move_lines.mapped('partner_id')
#         company_currency = self.env.company.currency_id
#
#         for partner in partners:
#             partner_lines = move_lines.filtered(lambda l: l.partner_id == partner)
#
#             # Calculate opening balance if date_from is set
#             if date_from:
#                 opening_balance = self._calculate_opening_balance(
#                     partner, date_from, account_ids, move_state, reconciled, journal_ids
#                 )
#
#                 if opening_balance != 0:
#                     detail_records.append({
#                         'partner_id': partner.id,
#                         'date': date_from,
#                         'name': 'Opening Balance',
#                         'balance': opening_balance,
#                         'debit': opening_balance if opening_balance > 0 else 0,
#                         'credit': abs(opening_balance) if opening_balance < 0 else 0,
#                         'company_currency_id': company_currency.id,
#                         'is_opening_balance': True,
#                     })
#
#             # Add all move lines for this partner
#             running_balance = opening_balance if date_from else 0
#             for line in partner_lines:
#                 running_balance += line.debit - line.credit
#
#                 vals = {
#                     'partner_id': partner.id,
#                     'date': line.date,
#                     'move_id': line.move_id.id,
#                     'journal_id': line.journal_id.id,
#                     'account_id': line.account_id.id,
#                     'name': line.name or line.move_id.name,
#                     'ref': line.move_id.ref or line.ref,
#                     'debit': line.debit,
#                     'credit': line.credit,
#                     'balance': running_balance,
#                     'company_currency_id': company_currency.id,
#                     'reconcile_id': line.full_reconcile_id.id if line.full_reconcile_id else False,
#                     'move_state': line.move_id.state,
#                     'is_opening_balance': False,
#                 }
#
#                 # Add currency information if needed
#                 if amount_currency and line.currency_id != company_currency:
#                     vals.update({
#                         'amount_currency': line.amount_currency,
#                         'currency_id': line.currency_id.id,
#                     })
#
#                 detail_records.append(vals)
#
#         # Create records
#         if detail_records:
#             self.create(detail_records)
#
#         return True
#
#     def _calculate_opening_balance(self, partner, date_from, account_ids, move_state, reconciled, journal_ids):
#         """
#         Calculate opening balance for a partner before date_from
#         """
#         domain = [
#             ('partner_id', '=', partner.id),
#             ('account_id', 'in', account_ids),
#             ('date', '<', date_from),
#             ('move_id.state', 'in', move_state),
#         ]
#
#         if journal_ids:
#             domain.append(('journal_id', 'in', journal_ids))
#
#         if not reconciled:
#             domain.append(('full_reconcile_id', '=', False))
#
#         lines = self.env['account.move.line'].search(domain)
#
#         total_debit = sum(lines.mapped('debit'))
#         total_credit = sum(lines.mapped('credit'))
#
#         return total_debit - total_credit
#


# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PartnerLedgerDetail(models.TransientModel):
    _name = 'partner.ledger.detail'
    _description = 'Partner Ledger Detail View'
    _order = 'partner_id, date, id'

    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    name = fields.Char(string='Label', readonly=True)
    ref = fields.Char(string='Reference', readonly=True)
    debit = fields.Monetary(string='Debit', readonly=True, currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', readonly=True, currency_field='company_currency_id')
    balance = fields.Monetary(string='Balance', readonly=True, currency_field='company_currency_id')
    amount_currency = fields.Monetary(string='Amount Currency', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', readonly=True)
    reconcile_id = fields.Many2one('account.full.reconcile', string='Reconcile', readonly=True)
    move_state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
    ], string='Status', readonly=True)

    # For opening balance line
    is_opening_balance = fields.Boolean(string='Is Opening Balance', readonly=True)

    def action_view_invoice(self):
        """
        Open the invoice/bill form view
        """
        self.ensure_one()

        if not self.move_id or self.is_opening_balance:
            return False

        return {
            'name': _('Invoice/Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'view_id': False,
            'target': 'current',
        }

    def action_view_journal_entry(self):
        """
        Open the journal entry form view
        """
        self.ensure_one()

        if not self.move_id or self.is_opening_balance:
            return False

        # Determine the correct view based on move type
        if self.move_id.move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
            # For invoices, open in invoice view
            return self.action_view_invoice()
        else:
            # For journal entries, open in journal entry view
            return {
                'name': _('Journal Entry'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': self.move_id.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'current',
            }

    @api.model
    def get_partner_ledger_details(self, wizard_data):
        """
        Generate partner ledger detail records based on wizard filters
        """
        # Clear existing records for this user
        self.search([]).unlink()

        # Get data from wizard
        date_from = wizard_data.get('date_from')
        date_to = wizard_data.get('date_to')
        partner_ids = wizard_data.get('partner_ids', [])
        journal_ids = wizard_data.get('journal_ids', [])
        target_move = wizard_data.get('target_move', 'posted')
        result_selection = wizard_data.get('result_selection', 'customer')
        reconciled = wizard_data.get('reconciled', False)
        amount_currency = wizard_data.get('amount_currency', False)

        # Determine account types
        if result_selection == 'supplier':
            account_type = ['liability_payable']
        elif result_selection == 'customer':
            account_type = ['asset_receivable']
        else:
            account_type = ['liability_payable', 'asset_receivable']

        # Get accounts
        accounts = self.env['account.account'].search([('account_type', 'in', account_type)])
        account_ids = accounts.ids

        # Get move states
        if target_move == 'posted':
            move_state = ['posted']
        else:
            move_state = ['draft', 'posted']

        # Build domain for move lines
        domain = [
            ('account_id', 'in', account_ids),
            ('move_id.state', 'in', move_state),
        ]

        # Add partner filter
        if partner_ids:
            domain.append(('partner_id', 'in', partner_ids))
        else:
            domain.append(('partner_id', '!=', False))

        # Add date filters
        if date_from:
            domain.append(('date', '>=', date_from))

        if date_to:
            domain.append(('date', '<=', date_to))

        # Add journal filter
        if journal_ids:
            domain.append(('journal_id', 'in', journal_ids))

        # Add reconcile filter
        if not reconciled:
            domain.append(('full_reconcile_id', '=', False))

        # Get move lines
        move_lines = self.env['account.move.line'].search(domain, order='partner_id, date, id')

        # Create detail records
        detail_records = []
        partners = move_lines.mapped('partner_id')
        company_currency = self.env.company.currency_id

        for partner in partners:
            partner_lines = move_lines.filtered(lambda l: l.partner_id == partner)

            # Calculate opening balance if date_from is set
            if date_from:
                opening_balance = self._calculate_opening_balance(
                    partner, date_from, account_ids, move_state, reconciled, journal_ids
                )

                if opening_balance != 0:
                    detail_records.append({
                        'partner_id': partner.id,
                        'date': date_from,
                        'name': 'Opening Balance',
                        'balance': opening_balance,
                        'debit': opening_balance if opening_balance > 0 else 0,
                        'credit': abs(opening_balance) if opening_balance < 0 else 0,
                        'company_currency_id': company_currency.id,
                        'is_opening_balance': True,
                    })

            # Add all move lines for this partner
            running_balance = opening_balance if date_from else 0
            for line in partner_lines:
                running_balance += line.debit - line.credit

                vals = {
                    'partner_id': partner.id,
                    'date': line.date,
                    'move_id': line.move_id.id,
                    'journal_id': line.journal_id.id,
                    'account_id': line.account_id.id,
                    'name': line.name or line.move_id.name,
                    'ref': line.move_id.ref or line.ref,
                    'debit': line.debit,
                    'credit': line.credit,
                    'balance': running_balance,
                    'company_currency_id': company_currency.id,
                    'reconcile_id': line.full_reconcile_id.id if line.full_reconcile_id else False,
                    'move_state': line.move_id.state,
                    'is_opening_balance': False,
                }

                # Add currency information if needed
                if amount_currency and line.currency_id != company_currency:
                    vals.update({
                        'amount_currency': line.amount_currency,
                        'currency_id': line.currency_id.id,
                    })

                detail_records.append(vals)

        # Create records
        if detail_records:
            self.create(detail_records)

        return True

    def _calculate_opening_balance(self, partner, date_from, account_ids, move_state, reconciled, journal_ids):
        """
        Calculate opening balance for a partner before date_from
        """
        domain = [
            ('partner_id', '=', partner.id),
            ('account_id', 'in', account_ids),
            ('date', '<', date_from),
            ('move_id.state', 'in', move_state),
        ]

        if journal_ids:
            domain.append(('journal_id', 'in', journal_ids))

        if not reconciled:
            domain.append(('full_reconcile_id', '=', False))

        lines = self.env['account.move.line'].search(domain)

        total_debit = sum(lines.mapped('debit'))
        total_credit = sum(lines.mapped('credit'))

        return total_debit - total_credit