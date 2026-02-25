from odoo import models, fields


class PurchaseEstimationLine(models.TransientModel):
    """Transient model to hold report result lines for display in list view."""
    _name = 'purchase.estimation.line'
    _description = 'Purchase Estimation Balance Register Line'

    wizard_id = fields.Many2one(
        'purchase.estimation.wizard',
        string='Wizard',
        ondelete='cascade',
    )
    vno = fields.Char(string='Vno')
    date = fields.Char(string='Date')
    customer = fields.Char(string='Vendor')
    address = fields.Char(string='Address')
    cell_no = fields.Char(string='Cell No')
    narration = fields.Char(string='Narration')
    net_amount = fields.Float(string='Net Amount', digits=(16, 2))
    confirm_date = fields.Char(string='Confirm Date')
    required_date = fields.Char(string='Required Date')