from odoo import fields, models, api


class AccountBankBookDetails(models.TransientModel):
    _name = 'account.bankbook.details'
    _description = 'Bank Book Details'

    wizard_id = fields.Many2one('account.bankbook.report', string='Wizard', ondelete='cascade')
    date_from = fields.Date(string='Date From', readonly=True)
    date_to = fields.Date(string='Date To', readonly=True)
    report_type = fields.Selection([
        ('combined', 'Combined Report'),
        ('separate', 'Separate by Analytic Account'),
    ], string='Report Type', readonly=True)
    account_ids = fields.One2many('account.bankbook.details.account', 'details_id', string='Bank Accounts')
    all_line_ids = fields.One2many('account.bankbook.details.line', 'details_id', string='All Transactions')
    total_debit = fields.Float(string='Total Debit', compute='_compute_totals', store=False)
    total_credit = fields.Float(string='Total Credit', compute='_compute_totals', store=False)
    total_balance = fields.Float(string='Total Balance', compute='_compute_totals', store=False)

    @api.depends('account_ids.subtotal_debit', 'account_ids.subtotal_credit')
    def _compute_totals(self):
        for record in self:
            record.total_debit = sum(record.account_ids.mapped('subtotal_debit'))
            record.total_credit = sum(record.account_ids.mapped('subtotal_credit'))
            # Balance = Total Debit - Total Credit (running balance sum is meaningless)
            record.total_balance = record.total_debit - record.total_credit


class AccountBankBookDetailsAccount(models.TransientModel):
    _name = 'account.bankbook.details.account'
    _description = 'Bank Book Details Account'
    _order = 'account_code'

    details_id = fields.Many2one('account.bankbook.details', string='Details', required=True, ondelete='cascade')
    account_code = fields.Char(string='Account Code', readonly=True)
    account_name = fields.Char(string='Account Name', readonly=True)
    line_ids = fields.One2many('account.bankbook.details.line', 'account_id', string='Transactions')
    subtotal_debit = fields.Float(string='Subtotal Debit', compute='_compute_subtotals', store=False)
    subtotal_credit = fields.Float(string='Subtotal Credit', compute='_compute_subtotals', store=False)
    subtotal_balance = fields.Float(string='Subtotal Balance', compute='_compute_subtotals', store=False)

    @api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.balance')
    def _compute_subtotals(self):
        for record in self:
            record.subtotal_debit = sum(record.line_ids.mapped('debit'))
            record.subtotal_credit = sum(record.line_ids.mapped('credit'))
            record.subtotal_balance = record.subtotal_debit - record.subtotal_credit


class AccountBankBookDetailsLine(models.TransientModel):
    _name = 'account.bankbook.details.line'
    _description = 'Bank Book Details Line'
    _order = 'account_code, date, id'

    account_id = fields.Many2one('account.bankbook.details.account', string='Account', required=True,
                                 ondelete='cascade')
    details_id = fields.Many2one('account.bankbook.details', string='Details', related='account_id.details_id',
                                 store=True, readonly=True)
    account_code = fields.Char(string='Account Code', related='account_id.account_code', store=True, readonly=True)
    account_name = fields.Char(string='Account Name', related='account_id.account_name', store=True, readonly=True)
    date = fields.Date(string='Date', readonly=True)
    reference = fields.Char(string='Reference', readonly=True)
    memo = fields.Char(string='Memo', readonly=True)  # NEW: memo_new from account.payment
    description = fields.Char(string='Description', readonly=True)
    journal_code = fields.Char(string='Journal', readonly=True)
    partner_name = fields.Char(string='Particulars', readonly=True)
    move_name = fields.Char(string='Entry', readonly=True)
    label = fields.Char(string='Label', readonly=True)
    debit = fields.Float(string='Debit', readonly=True)
    credit = fields.Float(string='Credit', readonly=True)
    balance = fields.Float(string='Balance', readonly=True)
    analytic_account_names = fields.Char(string='Analytic Accounts', readonly=True)
    move_id = fields.Integer(string='Move ID', readonly=True)  # Store the account.move id

    def action_view_payment(self):
        """Open the related payment"""
        self.ensure_one()

        if not self.move_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Payment Found',
                    'message': 'No related payment found for this transaction.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Get the account move
        move = self.env['account.move'].browse(self.move_id)

        if not move.exists():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Payment Not Found',
                    'message': 'The related payment no longer exists.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Check if this is a payment entry
        payment = self.env['account.payment'].search([('move_id', '=', move.id)], limit=1)

        if payment:
            # Open the payment form
            return {
                'name': 'Payment',
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'res_id': payment.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            # Not a payment - open the journal entry
            return {
                'name': 'Journal Entry',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': move.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def action_view_bill(self):
        """Open the related bill/invoice"""
        self.ensure_one()

        if not self.move_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Bill Found',
                    'message': 'No related bill or invoice found for this transaction.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Get the account move
        move = self.env['account.move'].browse(self.move_id)

        if not move.exists():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Bill Not Found',
                    'message': 'The related bill or invoice no longer exists.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Check if this is a payment entry
        payment = self.env['account.payment'].search([('move_id', '=', move.id)], limit=1)

        if payment:
            # This is a payment - find the related invoices/bills
            reconciled_invoices = payment.reconciled_bill_ids | payment.reconciled_invoice_ids

            if reconciled_invoices:
                if len(reconciled_invoices) == 1:
                    invoice = reconciled_invoices[0]
                    if invoice.move_type in ['out_invoice', 'out_receipt']:
                        view_name = 'Customer Invoice'
                    elif invoice.move_type == 'out_refund':
                        view_name = 'Customer Credit Note'
                    elif invoice.move_type in ['in_invoice', 'in_receipt']:
                        view_name = 'Vendor Bill'
                    elif invoice.move_type == 'in_refund':
                        view_name = 'Vendor Credit Note'
                    else:
                        view_name = 'Invoice'

                    return {
                        'name': view_name,
                        'type': 'ir.actions.act_window',
                        'res_model': 'account.move',
                        'res_id': invoice.id,
                        'view_mode': 'form',
                        'target': 'current',
                    }
                else:
                    return {
                        'name': 'Related Invoices/Bills',
                        'type': 'ir.actions.act_window',
                        'res_model': 'account.move',
                        'views': [(False, 'list'), (False, 'form')],
                        'view_mode': 'list,form',
                        'domain': [('id', 'in', reconciled_invoices.ids)],
                        'target': 'current',
                    }
            else:
                return {
                    'name': 'Payment',
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.payment',
                    'res_id': payment.id,
                    'view_mode': 'form',
                    'target': 'current',
                }

        # Not a payment - it's an invoice/bill or journal entry
        if move.move_type == 'entry':
            view_name = 'Journal Entry'
        elif move.move_type in ['out_invoice', 'out_receipt']:
            view_name = 'Customer Invoice'
        elif move.move_type == 'out_refund':
            view_name = 'Customer Credit Note'
        elif move.move_type in ['in_invoice', 'in_receipt']:
            view_name = 'Vendor Bill'
        elif move.move_type == 'in_refund':
            view_name = 'Vendor Credit Note'
        else:
            view_name = 'Journal Entry'

        return {
            'name': view_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }