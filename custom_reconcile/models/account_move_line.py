# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    """
    Extends account.move.line with custom reconciliation helpers.
    """
    _inherit = 'account.move.line'

    # ─── Custom Reconcile Fields ──────────────────────────────────────────────
    custom_reconcile_model_id = fields.Many2one(
        'custom.reconcile.model',
        string='Reconcile Rule Used',
        copy=False
    )
    is_custom_reconciled = fields.Boolean(
        string='Manually Reconciled via Custom Module',
        default=False, copy=False
    )

    def action_open_custom_reconcile_wizard(self):
        """
        Opens the manual reconciliation wizard for selected journal items.
        Select multiple debit/credit lines and launch this action.
        """
        if len(self) < 2:
            raise UserError(_('Please select at least 2 journal items to reconcile.'))

        # Validate all lines belong to the same partner
        partners = self.mapped('partner_id')
        if len(partners) > 1:
            raise UserError(_('All selected lines must belong to the same partner.'))

        # Validate debit/credit mix
        debits = self.filtered(lambda l: l.debit > 0)
        credits = self.filtered(lambda l: l.credit > 0)
        if not debits or not credits:
            raise UserError(_(
                'You must select at least one debit line and one credit line to reconcile.'
            ))

        # Validate accounts are reconcilable
        non_reconcilable = self.filtered(
            lambda l: not l.account_id.reconcile
        )
        if non_reconcilable:
            accounts = ', '.join(non_reconcilable.mapped('account_id.code'))
            raise UserError(_(
                'The following accounts are not configured for reconciliation: %s\n'
                'Please enable "Allow Reconciliation" on these accounts.'
            ) % accounts)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Reconcile Journal Items'),
            'res_model': 'custom.reconcile.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_ids': self.ids,
                'default_partner_id': partners[0].id if partners else False,
            },
        }

    @api.model
    def get_reconcile_candidates(self, partner_id, account_type, company_id=None):
        """
        Returns outstanding move lines for a given partner and account type.
        Used in the reconciliation wizard to populate candidate lines.

        :param partner_id: res.partner id
        :param account_type: 'asset_receivable' or 'liability_payable'
        :param company_id: optional company filter
        """
        domain = [
            ('partner_id', '=', partner_id),
            ('account_id.account_type', '=', account_type),
            ('reconciled', '=', False),
            ('move_id.state', '=', 'posted'),
            ('parent_state', '=', 'posted'),
        ]
        if company_id:
            domain.append(('company_id', '=', company_id))

        lines = self.search(domain, order='date asc')
        return lines.read([
            'id', 'name', 'ref', 'date', 'debit', 'credit',
            'amount_residual', 'currency_id', 'partner_id',
            'move_id', 'account_id',
        ])

    @api.model
    def custom_reconcile_lines(self, line_ids, writeoff_account_id=None,
                                writeoff_journal_id=None, writeoff_label=None):
        """
        Core reconciliation logic. Reconciles provided line IDs.
        Optionally creates a write-off entry for any remaining difference.

        :param line_ids: list of account.move.line IDs
        :param writeoff_account_id: account.account ID for write-off
        :param writeoff_journal_id: account.journal ID for write-off entry
        :param writeoff_label: label for the write-off journal item
        """
        lines = self.browse(line_ids)

        if not lines:
            raise UserError(_('No lines to reconcile.'))

        # Validate all lines have reconcile-enabled accounts
        for line in lines:
            if not line.account_id.reconcile:
                raise UserError(_(
                    'Account "%s" does not allow reconciliation. '
                    'Please enable it in the account settings.'
                ) % line.account_id.display_name)

        total_debit = sum(lines.mapped('debit'))
        total_credit = sum(lines.mapped('credit'))
        difference = total_debit - total_credit

        # If difference exists and write-off provided, create write-off entry
        if abs(difference) > 0.001 and writeoff_account_id:
            writeoff_account = self.env['account.account'].browse(writeoff_account_id)
            writeoff_journal = self.env['account.journal'].browse(writeoff_journal_id) \
                if writeoff_journal_id else lines[0].journal_id

            writeoff_vals = {
                'move_type': 'entry',
                'journal_id': writeoff_journal.id,
                'date': max(lines.mapped('date')),
                'ref': writeoff_label or _('Write-off'),
                'line_ids': [],
            }

            partner_id = lines[0].partner_id.id if lines[0].partner_id else False

            if difference > 0:
                # More debit than credit → write off to credit side
                writeoff_vals['line_ids'] = [
                    (0, 0, {
                        'account_id': lines[0].account_id.id,
                        'partner_id': partner_id,
                        'debit': 0.0,
                        'credit': abs(difference),
                        'name': writeoff_label or _('Write-off'),
                    }),
                    (0, 0, {
                        'account_id': writeoff_account.id,
                        'partner_id': partner_id,
                        'debit': abs(difference),
                        'credit': 0.0,
                        'name': writeoff_label or _('Write-off'),
                    }),
                ]
            else:
                # More credit than debit → write off to debit side
                writeoff_vals['line_ids'] = [
                    (0, 0, {
                        'account_id': lines[0].account_id.id,
                        'partner_id': partner_id,
                        'debit': abs(difference),
                        'credit': 0.0,
                        'name': writeoff_label or _('Write-off'),
                    }),
                    (0, 0, {
                        'account_id': writeoff_account.id,
                        'partner_id': partner_id,
                        'debit': 0.0,
                        'credit': abs(difference),
                        'name': writeoff_label or _('Write-off'),
                    }),
                ]

            writeoff_move = self.env['account.move'].create(writeoff_vals)
            writeoff_move.action_post()

            # Include writeoff lines in reconciliation
            writeoff_line = writeoff_move.line_ids.filtered(
                lambda l: l.account_id.id == lines[0].account_id.id
            )
            lines |= writeoff_line

        # Perform reconciliation
        lines.reconcile()

        # Mark as custom reconciled
        lines.write({'is_custom_reconciled': True})

        return {'success': True, 'reconciled_count': len(lines)}