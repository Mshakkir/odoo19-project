# -*- coding: utf-8 -*-
from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('analytic_distribution')
    def _onchange_analytic_distribution_set_purchase_warehouse(self):
        """Auto-set warehouse on vendor bill when analytic account is selected"""
        if self.analytic_distribution and self.move_id and self.move_id.move_type == 'in_invoice':
            # Get first analytic account from distribution
            analytic_dict = self.analytic_distribution
            if analytic_dict:
                try:
                    analytic_id = int(list(analytic_dict.keys())[0])
                    analytic_account = self.env['account.analytic.account'].browse(analytic_id)

                    if analytic_account:
                        _logger.info(f"Analytic account selected: {analytic_account.name}")

                        # Search for warehouse with matching name
                        warehouse = self.env['stock.warehouse'].search([
                            ('name', 'ilike', analytic_account.name),
                            ('company_id', '=', self.move_id.company_id.id)
                        ], limit=1)

                        if warehouse and not self.move_id.purchase_warehouse_id:
                            self.move_id.purchase_warehouse_id = warehouse
                            _logger.info(
                                f"Auto-set warehouse to {warehouse.name} from analytic account {analytic_account.name}")
                        elif not warehouse:
                            _logger.warning(f"No warehouse found matching analytic account: {analytic_account.name}")

                except Exception as e:
                    _logger.warning(f"Error auto-setting warehouse from analytic: {str(e)}")
                    pass