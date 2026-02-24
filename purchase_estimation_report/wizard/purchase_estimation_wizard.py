from datetime import datetime, time
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseEstimationWizard(models.TransientModel):
    _name = 'purchase.estimation.wizard'
    _description = 'Purchase Estimation Balance Register Wizard'

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        domain=[('supplier_rank', '>', 0)],
        help='Leave empty to include all vendors.',
    )
    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.context_today,
    )
    line_ids = fields.One2many(
        'purchase.estimation.line',
        'wizard_id',
        string='Lines',
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_orders(self):
        domain = [
            ('state', 'in', ['draft', 'sent', 'to approve', 'purchase', 'done']),
            ('date_order', '>=', datetime.combine(self.date_from, time.min)),
            ('date_order', '<=', datetime.combine(self.date_to, time.max)),
        ]
        if self.vendor_id:
            domain.append(('partner_id', '=', self.vendor_id.id))
        return self.env['purchase.order'].search(domain, order='date_order asc')

    def _build_lines(self, orders):
        vals = []
        for order in orders:
            partner = order.partner_id
            address_parts = [
                partner.street or '',
                partner.city or '',
                partner.state_id.name if partner.state_id else '',
                partner.country_id.name if partner.country_id else '',
            ]
            address = ', '.join(p for p in address_parts if p)

            # Safe narration — try common field names
            narration = ''
            for fname in ('notes', 'description', 'narration'):
                if fname in order._fields:
                    narration = order[fname] or ''
                    break

            vals.append({
                'wizard_id': self.id,
                'vno': order.name,
                'date': order.date_order.date() if order.date_order else False,
                'customer': partner.name,
                'address': address,
                'cell_no': partner.phone or '',
                'narration': narration,
                'net_amount': order.amount_total,
                'confirm_date': order.date_approve.date() if order.date_approve else False,
                'required_date': order.date_planned.date() if order.date_planned else False,
            })
        return vals

    # ------------------------------------------------------------------
    # Button actions
    # ------------------------------------------------------------------

    def action_show_details(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_('Date From must be earlier than or equal to Date To.'))

        # Clear old lines and rebuild
        self.line_ids.unlink()
        orders = self._get_orders()
        self.env['purchase.estimation.line'].create(self._build_lines(orders))

        # Open full-page list view (target='current' replaces current page like image 2)
        return {
            'name': _('Purchase Estimation Balance Register'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.estimation.line',
            'view_mode': 'list',
            'views': [(self.env.ref(
                'purchase_estimation_report.view_purchase_estimation_line_list'
            ).id, 'list')],
            'domain': [('wizard_id', '=', self.id)],
            'target': 'current',
            'context': {
                'date_from': str(self.date_from),
                'date_to': str(self.date_to),
                'vendor_name': self.vendor_id.name if self.vendor_id else _('All Vendors'),
                'create': False,
                'edit': False,
                'delete': False,
            },
        }

    def action_print_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_('Date From must be earlier than or equal to Date To.'))

        orders = self._get_orders()
        if not orders:
            raise UserError(_('No records found for the selected criteria.'))

        # Store lines on wizard so QWeb can read via docs
        self.line_ids.unlink()
        self.env['purchase.estimation.line'].create(self._build_lines(orders))

        return self.env.ref(
            'purchase_estimation_report.action_report_purchase_estimation'
        ).report_action(self)

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}