# from odoo import models, api
# import json
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     def _sync_analytic_to_receivable_payable(self):
#         """
#         Sync analytic distribution from invoice lines to receivable/payable lines
#         Uses direct SQL update to bypass ORM restrictions
#         """
#         for move in self:
#             # Only for invoices and bills
#             if move.move_type not in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
#                 continue
#
#             # Get analytic from product lines
#             product_lines = move.invoice_line_ids.filtered(
#                 lambda l: l.display_type == 'product' and l.analytic_distribution
#             )
#
#             if not product_lines:
#                 _logger.info(f"No product lines with analytic for move {move.name}")
#                 continue
#
#             # Get the analytic distribution from first product line
#             analytic_distribution = product_lines[0].analytic_distribution
#
#             # Convert to JSON string for SQL
#             if isinstance(analytic_distribution, dict):
#                 analytic_json = json.dumps(analytic_distribution)
#             else:
#                 analytic_json = analytic_distribution
#
#             _logger.info(f"Syncing analytic {analytic_json} to receivable/payable lines for {move.name}")
#
#             # Direct SQL update - bypasses all ORM restrictions
#             self.env.cr.execute("""
#                 UPDATE account_move_line aml
#                 SET analytic_distribution = %s::jsonb
#                 FROM account_account aa
#                 WHERE aml.account_id = aa.id
#                   AND aml.move_id = %s
#                   AND aa.account_type IN ('asset_receivable', 'liability_payable')
#             """, (analytic_json, move.id))
#
#             _logger.info(f"SQL updated {self.env.cr.rowcount} lines")
#
#             # Invalidate cache so Odoo reloads the values
#             move.line_ids.invalidate_recordset(['analytic_distribution'])
#
#             # Commit the transaction
#             self.env.cr.commit()
#
#     def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
#         """Override to sync analytic after recompute"""
#         res = super()._recompute_dynamic_lines(
#             recompute_all_taxes=recompute_all_taxes,
#             recompute_tax_base_amount=recompute_tax_base_amount
#         )
#
#         # Sync analytic after recompute
#         self._sync_analytic_to_receivable_payable()
#
#         return res
#
#     def action_post(self):
#         """Sync analytic before posting"""
#         self._sync_analytic_to_receivable_payable()
#         return super().action_post()
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         """Sync analytic after creation"""
#         moves = super().create(vals_list)
#         moves._sync_analytic_to_receivable_payable()
#         return moves
#
#     def write(self, vals):
#         """Sync analytic after any update"""
#         res = super().write(vals)
#
#         # If invoice lines or journal items changed, sync
#         if 'invoice_line_ids' in vals or 'line_ids' in vals:
#             self._sync_analytic_to_receivable_payable()
#
#         return res
#
#     def button_draft(self):
#         """Sync when reset to draft"""
#         res = super().button_draft()
#         self._sync_analytic_to_receivable_payable()
#         return res
#
#     def action_sync_analytic_manual(self):
#         """Manual button to force sync"""
#         self._sync_analytic_to_receivable_payable()
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': 'Success!',
#                 'message': 'Analytic distribution has been synced to Accounts Receivable/Payable lines',
#                 'type': 'success',
#                 'sticky': False,
#             }
#         }

from odoo import models, api
import json
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _sync_analytic_to_receivable_payable(self):
        """
        Sync analytic distribution from invoice lines to receivable/payable lines
        Uses direct SQL update to bypass ORM restrictions
        """
        for move in self:
            # Only for invoices and bills
            if move.move_type not in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
                continue

            # Get analytic from product lines
            product_lines = move.invoice_line_ids.filtered(
                lambda l: l.display_type == 'product' and l.analytic_distribution
            )

            if not product_lines:
                _logger.info(f"No product lines with analytic for move {move.name}")
                continue

            # Get the analytic distribution from first product line
            analytic_distribution = product_lines[0].analytic_distribution

            # Convert to JSON string for SQL
            if isinstance(analytic_distribution, dict):
                analytic_json = json.dumps(analytic_distribution)
            else:
                analytic_json = analytic_distribution

            _logger.info(f"Syncing analytic {analytic_json} to receivable/payable lines for {move.name}")

            # Direct SQL update - bypasses all ORM restrictions
            self.env.cr.execute("""
                UPDATE account_move_line aml
                SET analytic_distribution = %s::jsonb
                FROM account_account aa
                WHERE aml.account_id = aa.id
                  AND aml.move_id = %s
                  AND aa.account_type IN ('asset_receivable', 'liability_payable')
            """, (analytic_json, move.id))

            _logger.info(f"SQL updated {self.env.cr.rowcount} lines")

            # Invalidate cache so Odoo reloads the values
            move.line_ids.invalidate_recordset(['analytic_distribution'])

            # Commit the transaction
            self.env.cr.commit()

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        """Override to sync analytic after recompute"""
        res = super()._recompute_dynamic_lines(
            recompute_all_taxes=recompute_all_taxes,
            recompute_tax_base_amount=recompute_tax_base_amount
        )

        # Sync analytic after recompute
        self._sync_analytic_to_receivable_payable()

        return res

    def action_post(self):
        """Sync analytic before posting"""
        self._sync_analytic_to_receivable_payable()
        return super().action_post()

    @api.model_create_multi
    def create(self, vals_list):
        """Sync analytic after creation - with invalid field filtering"""
        # Get valid field names for account.move
        valid_fields = set(self._fields.keys())

        # Clean vals_list by removing invalid fields
        cleaned_vals_list = []
        for vals in vals_list:
            # Remove 'customer_reference' if present
            if 'customer_reference' in vals:
                _logger.warning(
                    f"Removing invalid field 'customer_reference' from invoice creation. Value was: {vals.get('customer_reference')}")
                # Map to correct field if needed
                if vals.get('customer_reference') and not vals.get('ref'):
                    vals['ref'] = vals['customer_reference']
                vals.pop('customer_reference')

            cleaned_vals_list.append(vals)

        moves = super().create(cleaned_vals_list)
        moves._sync_analytic_to_receivable_payable()
        return moves

    def write(self, vals):
        """Sync analytic after any update"""
        res = super().write(vals)

        # If invoice lines or journal items changed, sync
        if 'invoice_line_ids' in vals or 'line_ids' in vals:
            self._sync_analytic_to_receivable_payable()

        return res

    def button_draft(self):
        """Sync when reset to draft"""
        res = super().button_draft()
        self._sync_analytic_to_receivable_payable()
        return res

    def action_sync_analytic_manual(self):
        """Manual button to force sync"""
        self._sync_analytic_to_receivable_payable()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success!',
                'message': 'Analytic distribution has been synced to Accounts Receivable/Payable lines',
                'type': 'success',
                'sticky': False,
            }
        }