# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    scheduled_date_formatted = fields.Char(
        string='Scheduled Date',
        compute='_compute_picking_formatted_dates',
        store=False,
    )

    date_done_formatted = fields.Char(
        string='Date Done',
        compute='_compute_picking_formatted_dates',
        store=False,
    )

    @api.depends('scheduled_date', 'date_done')
    def _compute_picking_formatted_dates(self):
        for picking in self:
            picking.scheduled_date_formatted = (
                picking.scheduled_date.strftime('%d/%m/%Y')
                if picking.scheduled_date else ''
            )
            picking.date_done_formatted = (
                picking.date_done.strftime('%d/%m/%Y')
                if picking.date_done else ''
            )