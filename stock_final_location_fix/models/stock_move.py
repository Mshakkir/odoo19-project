from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        """
        Override _action_done to force location_dest_id to location_final_id
        when location_final_id is set on the stock move.
        This ensures the Final Location field is actually respected during validation.
        """
        for move in self:
            if move.location_final_id and move.location_final_id != move.location_dest_id:
                _logger.info(
                    "Stock Final Location Fix: Overriding destination for move %s "
                    "from '%s' to Final Location '%s'",
                    move.name,
                    move.location_dest_id.complete_name,
                    move.location_final_id.complete_name,
                )
                move.location_dest_id = move.location_final_id

                # Also update move lines (detailed operations) to match
                move.move_line_ids.write({
                    'location_dest_id': move.location_final_id.id,
                })

        return super()._action_done(cancel_backorder=cancel_backorder)