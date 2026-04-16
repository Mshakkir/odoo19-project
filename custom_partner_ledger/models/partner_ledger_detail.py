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

    # These store SAR-equivalent amounts (company currency) — used for Balance column only
    debit = fields.Monetary(string='Debit', readonly=True, currency_field='display_currency_id')
    credit = fields.Monetary(string='Credit', readonly=True, currency_field='display_currency_id')
    balance = fields.Monetary(string='Balance', readonly=True, currency_field='company_currency_id')

    # Original foreign currency info
    amount_currency = fields.Monetary(string='Amount Currency', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', readonly=True)

    # The currency used to display debit/credit: foreign currency if applicable, else company currency
    display_currency_id = fields.Many2one(
        'res.currency', string='Display Currency', readonly=True,
        help="Foreign currency for this line (if any), otherwise company currency."
    )

    reconcile_id = fields.Many2one('account.full.reconcile', string='Reconcile', readonly=True)
    move_state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
    ], string='Status', readonly=True)

    is_opening_balance = fields.Boolean(string='Is Opening Balance', readonly=True)
    invoice_date_due = fields.Date(string='Due Date', readonly=True)
    po_number = fields.Char(string='PO Number', readonly=True)

    manual_currency_exchange_rate = fields.Float(
        string='Exchange Rate', digits=(12, 6), readonly=True, default=1.0,
    )

    final_balance = fields.Monetary(
        string='Final Balance', readonly=True,
        currency_field='company_currency_id',
        compute='_compute_final_balance', store=False,
    )

    @api.depends('partner_id', 'balance')
    def _compute_final_balance(self):
        records_by_partner = {}
        for record in self:
            records_by_partner.setdefault(record.partner_id, []).append(record)
        for record in self:
            last = records_by_partner.get(record.partner_id, [])
            record.final_balance = record.balance if last and record == last[-1] else 0.0

    def action_view_invoice(self):
        self.ensure_one()
        if not self.move_id or self.is_opening_balance:
            return False
        return {
            'name': _('Invoice/Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_journal_entry(self):
        self.ensure_one()
        if not self.move_id or self.is_opening_balance:
            return False
        if self.move_id.move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
            return self.action_view_invoice()
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
        self.search([]).unlink()

        date_from = wizard_data.get('date_from')
        date_to = wizard_data.get('date_to')
        partner_ids = wizard_data.get('partner_ids', [])
        journal_ids = wizard_data.get('journal_ids', [])
        target_move = wizard_data.get('target_move', 'posted')
        result_selection = wizard_data.get('result_selection', 'customer')
        reconciled = wizard_data.get('reconciled', False)
        amount_currency = wizard_data.get('amount_currency', False)

        if result_selection == 'supplier':
            account_type = ['liability_payable']
        elif result_selection == 'customer':
            account_type = ['asset_receivable']
        else:
            account_type = ['liability_payable', 'asset_receivable']

        accounts = self.env['account.account'].search([('account_type', 'in', account_type)])
        account_ids = accounts.ids
        move_state = ['posted'] if target_move == 'posted' else ['draft', 'posted']

        domain = [
            ('account_id', 'in', account_ids),
            ('move_id.state', 'in', move_state),
        ]
        if partner_ids:
            domain.append(('partner_id', 'in', partner_ids))
        else:
            domain.append(('partner_id', '!=', False))
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        if journal_ids:
            domain.append(('journal_id', 'in', journal_ids))
        if not reconciled:
            domain.append(('full_reconcile_id', '=', False))

        move_lines = self.env['account.move.line'].search(domain, order='partner_id, date, id')
        company_currency = self.env.company.currency_id
        detail_records = []

        for partner in move_lines.mapped('partner_id'):
            partner_lines = move_lines.filtered(lambda l: l.partner_id == partner)

            opening_balance = 0
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
                        # Opening balance is always in company currency
                        'debit': opening_balance if opening_balance > 0 else 0,
                        'credit': abs(opening_balance) if opening_balance < 0 else 0,
                        'company_currency_id': company_currency.id,
                        'display_currency_id': company_currency.id,
                        'is_opening_balance': True,
                        'invoice_date_due': False,
                        'po_number': '',
                        'manual_currency_exchange_rate': 1.0,
                    })

            running_balance = opening_balance
            for line in partner_lines:
                # Detect foreign currency
                is_foreign = (
                    line.currency_id
                    and line.currency_id != company_currency
                    and line.amount_currency
                )

                if is_foreign:
                    # Use the raw foreign currency amount for debit/credit display
                    raw = abs(line.amount_currency)
                    debit_val = raw if line.amount_currency > 0 else 0.0
                    credit_val = raw if line.amount_currency < 0 else 0.0
                    display_currency = line.currency_id
                else:
                    debit_val = line.debit
                    credit_val = line.credit
                    display_currency = company_currency

                # Running balance stays in company currency (SAR) for consistency
                running_balance += line.debit - line.credit

                vals = {
                    'partner_id': partner.id,
                    'date': line.date,
                    'move_id': line.move_id.id,
                    'journal_id': line.journal_id.id,
                    'account_id': line.account_id.id,
                    'name': line.name or line.move_id.name,
                    'ref': line.move_id.ref or line.ref,
                    'debit': debit_val,
                    'credit': credit_val,
                    'balance': running_balance,
                    'company_currency_id': company_currency.id,
                    'display_currency_id': display_currency.id,
                    'reconcile_id': line.full_reconcile_id.id if line.full_reconcile_id else False,
                    'move_state': line.move_id.state,
                    'is_opening_balance': False,
                    'invoice_date_due': line.move_id.invoice_date_due or False,
                    'po_number': line.move_id.client_order_ref or '',
                    'manual_currency_exchange_rate': 1.0,
                }

                if line.currency_id and line.currency_id != company_currency:
                    vals.update({
                        'amount_currency': line.amount_currency,
                        'currency_id': line.currency_id.id,
                    })

                detail_records.append(vals)

        if detail_records:
            self.create(detail_records)
        return True

    def _calculate_opening_balance(self, partner, date_from, account_ids, move_state, reconciled, journal_ids):
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
        return sum(lines.mapped('debit')) - sum(lines.mapped('credit'))














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
#
#     # These store SAR-equivalent amounts (converted via manual rate when applicable)
#     debit = fields.Monetary(string='Debit', readonly=True, currency_field='company_currency_id')
#     credit = fields.Monetary(string='Credit', readonly=True, currency_field='company_currency_id')
#     balance = fields.Monetary(string='Balance', readonly=True, currency_field='company_currency_id')
#
#     # Original foreign currency info (for reference, hidden in view)
#     amount_currency = fields.Monetary(string='Amount Currency', readonly=True, currency_field='currency_id')
#     currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
#     company_currency_id = fields.Many2one('res.currency', string='Company Currency', readonly=True)
#
#     reconcile_id = fields.Many2one('account.full.reconcile', string='Reconcile', readonly=True)
#     move_state = fields.Selection([
#         ('draft', 'Draft'),
#         ('posted', 'Posted'),
#     ], string='Status', readonly=True)
#
#     is_opening_balance = fields.Boolean(string='Is Opening Balance', readonly=True)
#     invoice_date_due = fields.Date(string='Due Date', readonly=True)
#     po_number = fields.Char(string='PO Number', readonly=True)
#
#     # Store the rate used (for info / PDF display)
#     manual_currency_exchange_rate = fields.Float(
#         string='Exchange Rate', digits=(12, 6), readonly=True, default=1.0,
#     )
#
#     final_balance = fields.Monetary(
#         string='Final Balance', readonly=True,
#         currency_field='company_currency_id',
#         compute='_compute_final_balance', store=False,
#     )
#
#     @api.depends('partner_id', 'balance')
#     def _compute_final_balance(self):
#         records_by_partner = {}
#         for record in self:
#             records_by_partner.setdefault(record.partner_id, []).append(record)
#         for record in self:
#             last = records_by_partner.get(record.partner_id, [])
#             record.final_balance = record.balance if last and record == last[-1] else 0.0
#
#     def action_view_invoice(self):
#         self.ensure_one()
#         if not self.move_id or self.is_opening_balance:
#             return False
#         return {
#             'name': _('Invoice/Bill'),
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'res_id': self.move_id.id,
#             'view_mode': 'form',
#             'target': 'current',
#         }
#
#     def action_view_journal_entry(self):
#         self.ensure_one()
#         if not self.move_id or self.is_opening_balance:
#             return False
#         if self.move_id.move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
#             return self.action_view_invoice()
#         return {
#             'name': _('Journal Entry'),
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'res_id': self.move_id.id,
#             'view_mode': 'form',
#             'views': [(False, 'form')],
#             'target': 'current',
#         }
#
#     @api.model
#     def get_partner_ledger_details(self, wizard_data):
#         self.search([]).unlink()
#
#         date_from = wizard_data.get('date_from')
#         date_to = wizard_data.get('date_to')
#         partner_ids = wizard_data.get('partner_ids', [])
#         journal_ids = wizard_data.get('journal_ids', [])
#         target_move = wizard_data.get('target_move', 'posted')
#         result_selection = wizard_data.get('result_selection', 'customer')
#         reconciled = wizard_data.get('reconciled', False)
#         amount_currency = wizard_data.get('amount_currency', False)
#
#         if result_selection == 'supplier':
#             account_type = ['liability_payable']
#         elif result_selection == 'customer':
#             account_type = ['asset_receivable']
#         else:
#             account_type = ['liability_payable', 'asset_receivable']
#
#         accounts = self.env['account.account'].search([('account_type', 'in', account_type)])
#         account_ids = accounts.ids
#         move_state = ['posted'] if target_move == 'posted' else ['draft', 'posted']
#
#         domain = [
#             ('account_id', 'in', account_ids),
#             ('move_id.state', 'in', move_state),
#         ]
#         if partner_ids:
#             domain.append(('partner_id', 'in', partner_ids))
#         else:
#             domain.append(('partner_id', '!=', False))
#         if date_from:
#             domain.append(('date', '>=', date_from))
#         if date_to:
#             domain.append(('date', '<=', date_to))
#         if journal_ids:
#             domain.append(('journal_id', 'in', journal_ids))
#         if not reconciled:
#             domain.append(('full_reconcile_id', '=', False))
#
#         move_lines = self.env['account.move.line'].search(domain, order='partner_id, date, id')
#         company_currency = self.env.company.currency_id
#         detail_records = []
#
#         for partner in move_lines.mapped('partner_id'):
#             partner_lines = move_lines.filtered(lambda l: l.partner_id == partner)
#
#             opening_balance = 0
#             if date_from:
#                 opening_balance = self._calculate_opening_balance(
#                     partner, date_from, account_ids, move_state, reconciled, journal_ids
#                 )
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
#                         'invoice_date_due': False,
#                         'po_number': '',
#                         'manual_currency_exchange_rate': 1.0,
#                     })
#
#             running_balance = opening_balance
#             for line in partner_lines:
#                 # Get manual exchange rate from linked payment
#                 manual_rate = 1.0
#                 payment = self.env['account.payment'].search(
#                     [('move_id', '=', line.move_id.id)], limit=1
#                 )
#                 if payment and hasattr(payment, 'manual_currency_exchange_rate') \
#                         and payment.manual_currency_exchange_rate:
#                     manual_rate = payment.manual_currency_exchange_rate
#
#                 is_foreign = (
#                     line.currency_id
#                     and line.currency_id != company_currency
#                     and manual_rate != 1.0
#                     and line.amount_currency
#                 )
#
#                 if is_foreign:
#                     # Convert using manual rate: 1 foreign = manual_rate SAR
#                     raw_amount = abs(line.amount_currency)
#                     converted = raw_amount * manual_rate
#                     debit_val = converted if line.amount_currency > 0 else 0.0
#                     credit_val = converted if line.amount_currency < 0 else 0.0
#                 else:
#                     debit_val = line.debit
#                     credit_val = line.credit
#
#                 running_balance += debit_val - credit_val
#
#                 vals = {
#                     'partner_id': partner.id,
#                     'date': line.date,
#                     'move_id': line.move_id.id,
#                     'journal_id': line.journal_id.id,
#                     'account_id': line.account_id.id,
#                     'name': line.name or line.move_id.name,
#                     'ref': line.move_id.ref or line.ref,
#                     'debit': debit_val,
#                     'credit': credit_val,
#                     'balance': running_balance,
#                     'company_currency_id': company_currency.id,
#                     'reconcile_id': line.full_reconcile_id.id if line.full_reconcile_id else False,
#                     'move_state': line.move_id.state,
#                     'is_opening_balance': False,
#                     'invoice_date_due': line.move_id.invoice_date_due or False,
#                     'po_number': line.move_id.client_order_ref or '',
#                     'manual_currency_exchange_rate': manual_rate,
#                 }
#
#                 if amount_currency and line.currency_id and line.currency_id != company_currency:
#                     vals.update({
#                         'amount_currency': line.amount_currency,
#                         'currency_id': line.currency_id.id,
#                     })
#
#                 detail_records.append(vals)
#
#         if detail_records:
#             self.create(detail_records)
#         return True
#
#     def _calculate_opening_balance(self, partner, date_from, account_ids, move_state, reconciled, journal_ids):
#         domain = [
#             ('partner_id', '=', partner.id),
#             ('account_id', 'in', account_ids),
#             ('date', '<', date_from),
#             ('move_id.state', 'in', move_state),
#         ]
#         if journal_ids:
#             domain.append(('journal_id', 'in', journal_ids))
#         if not reconciled:
#             domain.append(('full_reconcile_id', '=', False))
#         lines = self.env['account.move.line'].search(domain)
#         return sum(lines.mapped('debit')) - sum(lines.mapped('credit'))