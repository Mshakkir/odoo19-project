# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Add the missing field to fix the error
    is_inter_warehouse_transfer = fields.Boolean(
        string='Inter-Warehouse Transfer',
        default=False,
        compute='_compute_is_inter_warehouse',
        store=True,
        help='Automatically detects if this is a transfer between different warehouses'
    )

    @api.depends('location_id', 'location_dest_id', 'location_id.warehouse_id', 'location_dest_id.warehouse_id')
    def _compute_is_inter_warehouse(self):
        """
        Automatically detect if this is an inter-warehouse transfer.
        Returns True if both source and destination are internal warehouse locations
        and they belong to different warehouses.
        """
        for picking in self:
            try:
                # Get warehouse for source location
                source_warehouse = picking.location_id.warehouse_id
                # Get warehouse for destination location
                dest_warehouse = picking.location_dest_id.warehouse_id

                # Check conditions for inter-warehouse transfer:
                # 1. Both locations must be internal (warehouse stock)
                # 2. Both must have warehouses assigned
                # 3. Warehouses must be different
                if (picking.location_id.usage == 'internal' and
                        picking.location_dest_id.usage == 'internal' and
                        source_warehouse and dest_warehouse and
                        source_warehouse.id != dest_warehouse.id):

                    picking.is_inter_warehouse_transfer = True
                    _logger.debug(
                        f"Picking {picking.name}: Inter-warehouse transfer detected "
                        f"from {source_warehouse.name} to {dest_warehouse.name}"
                    )
                else:
                    picking.is_inter_warehouse_transfer = False

            except Exception as e:
                # If any error occurs, default to False
                _logger.warning(
                    f"Error computing inter-warehouse status for picking {picking.name}: {str(e)}"
                )
                picking.is_inter_warehouse_transfer = False