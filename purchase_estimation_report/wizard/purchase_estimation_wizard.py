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

    def _get_rfq_lines(self):
        """Return purchase.order (RFQ/estimations) records filtered by wizard params."""
        domain = [
            ('state', 'in', ['draft', 'sent', 'to approve', 'purchase', 'done']),
            ('date_order', '>=', fields.Datetime.to_datetime(self.date_from)),
            ('date_order', '<=', datetime.combine(self.date_to, time.max)),
        ]
        if self.vendor_id:
            domain.append(('partner_id', '=', self.vendor_id.id))
        return self.env['purchase.order'].search(domain, order='date_order asc')

    def _build_line_vals(self, orders):
        """Convert purchase orders to list-of-dict for report lines."""
        vals = []
        for order in orders:
            partner = order.partner_id
            address_parts = filter(None, [
                partner.street,
                partner.city,
                partner.state_id.name if partner.state_id else '',
                partner.country_id.name if partner.country_id else '',
            ])
            address = ', '.join(address_parts)

            vals.append({
                'wizard_id': self.id,
                'vno': order.name,
                'date': order.date_order.date() if order.date_order else False,
                'customer': partner.name,
                'address': address,
                'cell_no': partner.phone or partner.mobile or '',
                'narration': order.notes or '',
                'net_amount': order.amount_total,
                'confirm_date': order.date_approve.date() if order.date_approve else False,
                'required_date': order.date_planned.date() if order.date_planned else False,
            })
        return vals

    # ------------------------------------------------------------------
    # Button actions
    # ------------------------------------------------------------------

    def action_show_details(self):
        """Populate lines and open list view in a new window."""
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_('Date From must be earlier than or equal to Date To.'))

        # Clear old lines
        self.line_ids.unlink()

        orders = self._get_rfq_lines()
        line_vals = self._build_line_vals(orders)
        self.env['purchase.estimation.line'].create(line_vals)

        return {
            'name': _('Purchase Estimation Balance Register'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.estimation.line',
            'view_mode': 'list',
            'views': [(self.env.ref(
                'purchase_estimation_report.view_purchase_estimation_line_list'
            ).id, 'list')],
            'domain': [('wizard_id', '=', self.id)],
            'target': 'new',
            'context': {
                'wizard_id': self.id,
                'date_from': str(self.date_from),
                'date_to': str(self.date_to),
                'vendor_name': self.vendor_id.name if self.vendor_id else _('All Vendors'),
            },
        }

    def action_print_report(self):
        """Generate PDF report."""
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_('Date From must be earlier than or equal to Date To.'))

        orders = self._get_rfq_lines()
        if not orders:
            raise UserError(_('No records found for the selected criteria.'))

        data = {
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),
            'vendor_name': self.vendor_id.name if self.vendor_id else _('All Vendors'),
            'lines': self._build_line_vals(orders),
        }
        # Remove wizard_id key — not serialisable in report context
        for line in data['lines']:
            line.pop('wizard_id', None)

        return self.env.ref(
            'purchase_estimation_report.action_report_purchase_estimation'
        ).report_action(self, data=data)

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}