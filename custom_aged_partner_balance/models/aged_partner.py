def action_show_details(self):
    """
    Open all move lines filtered by aged report settings.
    """
    self.ensure_one()

    # Prepare filter domain
    domain = [
        ('journal_id', 'in', self.journal_ids.ids),
        ('date', '<=', self.date_from),
    ]

    # Apply partner type
    if self.result_selection == 'customer':
        domain += [('account_id.account_type', '=', 'asset_receivable')]
    elif self.result_selection == 'supplier':
        domain += [('account_id.account_type', '=', 'liability_payable')]

    # Posted or All
    if self.target_move == 'posted':
        domain += [('parent_state', '=', 'posted')]

    action = {
        'name': "Aged Details",
        'type': 'ir.actions.act_window',
        'view_mode': 'tree,form',
        'res_model': 'account.move.line',
        'domain': domain,
        'context': {'search_default_group_by_partner': 1},
    }
    return action
