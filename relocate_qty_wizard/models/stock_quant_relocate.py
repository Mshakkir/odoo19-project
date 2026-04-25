# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockQuantRelocate(models.TransientModel):
    _inherit = 'stock.quant.relocate'

    line_ids = fields.One2many(
        'stock.quant.relocate.line', 'wizard_id', string='Products'
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        # Extract quant ids from context (set by the Relocate button)
        quant_ids = self.env.context.get('active_ids') or []
        if not quant_ids:
            # fallback: parse from defaults['quant_ids'] ORM commands
            raw = defaults.get('quant_ids') or []
            for cmd in raw:
                if isinstance(cmd, (list, tuple)) and len(cmd) >= 3:
                    quant_ids = cmd[2]
                    break
        quants = self.env['stock.quant'].browse(quant_ids)
        lines = []
        for quant in quants:
            lines.append((0, 0, {
                'quant_id': quant.id,
                'qty': quant.quantity,
            }))
        defaults['line_ids'] = lines
        return defaults

    def action_relocate_quants(self):
        """
        Override to relocate using adjusted quantities from line_ids.

        Key issue: super() merges/deletes quants internally, so we must
        snapshot all needed data BEFORE calling super().
        """
        self.ensure_one()

        lines_with_quant = self.line_ids.filtered(lambda l: l.quant_id)
        if not lines_with_quant:
            return super().action_relocate_quants()

        # ── Snapshot all data before super() deletes/merges quants ──────────
        line_data = []
        for line in lines_with_quant:
            quant = line.quant_id
            if line.qty <= 0:
                raise UserError(
                    _('Quantity must be greater than zero for "%s".')
                    % quant.product_id.display_name
                )
            if line.qty > quant.quantity:
                raise UserError(_(
                    'Qty to relocate (%(qty)s) exceeds on-hand (%(avail)s) for "%(product)s".',
                    qty=line.qty,
                    avail=quant.quantity,
                    product=quant.product_id.display_name,
                ))
            line_data.append({
                'product_id': quant.product_id,
                'location_id': quant.location_id,
                'lot_id': quant.lot_id or None,
                'package_id': quant.package_id or None,
                'owner_id': quant.owner_id or None,
                'full_qty': quant.quantity,
                'move_qty': line.qty,
                'remainder': quant.quantity - line.qty,
            })

        # ── Temporarily reduce quants to requested qty so super() moves
        #    exactly the right amount ─────────────────────────────────────────
        for i, line in enumerate(lines_with_quant):
            if line_data[i]['remainder'] > 0:
                line.quant_id.sudo().write({'quantity': line_data[i]['move_qty']})

        try:
            result = super().action_relocate_quants()
        except Exception:
            # Restore on failure (quants may still exist)
            for i, line in enumerate(lines_with_quant):
                try:
                    line.quant_id.sudo().write({'quantity': line_data[i]['full_qty']})
                except Exception:
                    pass
            raise

        # ── Restore remainder to source location using snapshotted data ──────
        StockQuant = self.env['stock.quant']
        for data in line_data:
            if data['remainder'] > 0:
                StockQuant._update_available_quantity(
                    data['product_id'],
                    data['location_id'],
                    data['remainder'],
                    lot_id=data['lot_id'] or None,
                    package_id=data['package_id'] or None,
                    owner_id=data['owner_id'] or None,
                )

        return result
