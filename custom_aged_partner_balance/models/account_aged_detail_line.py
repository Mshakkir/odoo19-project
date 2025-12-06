from odoo import models, api


class AccountAgedTrialBalance(models.TransientModel):
    _inherit = 'account.aged.trial.balance'

    def action_show_details(self):
        """Show detailed aged balance lines"""
        self.ensure_one()

        # Get aged balance data
        lines_data = self._get_aged_balance_lines()

        # Create transient records
        detail_lines = self.env['account.aged.detail.line']
        for line_data in lines_data:
            detail_lines |= detail_lines.create(line_data)

        # Return action to show the details
        return {
            'name': 'Aged Balance Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.aged.detail.line',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('custom_aged_partner_balance.view_aged_detail_tree').id, 'tree'),
                      (self.env.ref('custom_aged_partner_balance.view_aged_detail_form').id, 'form')],
            'domain': [('id', 'in', detail_lines.ids)],
            'target': 'current',
        }

    def _get_aged_balance_lines(self):
        """Get aged balance data for partners"""
        self.ensure_one()

        # You'll need to implement the logic to calculate aged balances
        # This is a placeholder - adjust based on your actual calculation logic
        lines = []

        # Get partners based on result_selection
        domain = []
        if self.result_selection == 'customer':
            domain = [('customer_rank', '>', 0)]
        elif self.result_selection == 'supplier':
            domain = [('supplier_rank', '>', 0)]

        if self.partner_ids:
            domain.append(('id', 'in', self.partner_ids.ids))

        partners = self.env['res.partner'].search(domain)

        for partner in partners:
            # Calculate aged balances for each partner
            # This is where you'd implement your aging logic
            line_data = {
                'partner_id': partner.id,
                'partner_name': partner.name,
                'trust': partner.trust,
                'email': partner.email,
                'phone': partner.phone,
                'vat': partner.vat,
                'currency_id': self.company_id.currency_id.id,
                'company_id': self.company_id.id,
                # You need to calculate these values based on your logic
                'not_due': 0.0,
                'period_0': 0.0,
                'period_1': 0.0,
                'period_2': 0.0,
                'period_3': 0.0,
                'period_4': 0.0,
                'total': 0.0,
            }
            lines.append(line_data)

        return lines