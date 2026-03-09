from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrderSendWizard(models.TransientModel):
    _name = 'sale.order.send.wizard'
    _description = 'Sale Order Send Wizard'

    order_id = fields.Many2one(
        'sale.order', string='Sale Order', required=True, ondelete='cascade'
    )

    # Email fields
    mail_partner_ids = fields.Many2many(
        'res.partner',
        string='To',
        compute='_compute_mail_partner_ids',
        store=True,
        readonly=False,
    )
    subject = fields.Char(
        string='Subject',
        compute='_compute_subject',
        store=True,
        readonly=False,
    )
    body = fields.Html(
        string='Body',
        compute='_compute_body',
        store=True,
        readonly=False,
        sanitize=False,
    )
    template_id = fields.Many2one(
        'mail.template',
        string='Use Template',
        domain="[('model', '=', 'sale.order')]",
        compute='_compute_template_id',
        store=True,
        readonly=False,
    )
    mail_attachments_widget = fields.Json(
        string='Attachments',
        compute='_compute_mail_attachments_widget',
        store=True,
        readonly=False,
    )

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends('order_id')
    def _compute_template_id(self):
        for wizard in self:
            template = wizard.order_id._find_mail_template()
            wizard.template_id = template

    @api.depends('order_id', 'template_id')
    def _compute_mail_partner_ids(self):
        for wizard in self:
            order = wizard.order_id
            partners = self.env['res.partner']
            if order.partner_id:
                partners |= order.partner_id
            wizard.mail_partner_ids = partners

    @api.depends('order_id', 'template_id')
    def _compute_subject(self):
        for wizard in self:
            order = wizard.order_id
            template = wizard.template_id
            if template:
                subject = template._render_field(
                    'subject', order.ids, compute_lang=True
                )[order.id]
                wizard.subject = subject
            else:
                doc_type = 'Quotation' if order.state in ('draft', 'sent') else 'Order'
                wizard.subject = f"{order.company_id.name} {doc_type} (Ref {order.name})"

    @api.depends('order_id', 'template_id')
    def _compute_body(self):
        for wizard in self:
            order = wizard.order_id
            template = wizard.template_id
            if template:
                body = template._render_field(
                    'body_html', order.ids, compute_lang=True,
                    options={'post_process': True}
                )[order.id]
                wizard.body = body
            else:
                wizard.body = False

    @api.depends('order_id', 'template_id')
    def _compute_mail_attachments_widget(self):
        for wizard in self:
            attachments = []
            order = wizard.order_id
            template = wizard.template_id

            # Generate PDF report attachment
            report = self.env.ref('sale.action_report_saleorder', raise_if_not_found=False)
            if report:
                try:
                    pdf_content, _ = report._render_qweb_pdf([order.id])
                    doc_type = 'Quotation' if order.state in ('draft', 'sent') else 'Order'
                    filename = f"{doc_type}_{order.name}.pdf".replace('/', '_')
                    attachments.append({
                        'name': filename,
                        'mimetype': 'application/pdf',
                        'placeholder': False,
                    })
                except Exception:
                    pass

            wizard.mail_attachments_widget = attachments or False

    # -------------------------------------------------------------------------
    # Onchange
    # -------------------------------------------------------------------------

    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Reload subject and body when template changes."""
        for wizard in self:
            order = wizard.order_id
            if wizard.template_id:
                subject = wizard.template_id._render_field(
                    'subject', order.ids, compute_lang=True
                )[order.id]
                body = wizard.template_id._render_field(
                    'body_html', order.ids, compute_lang=True,
                    options={'post_process': True}
                )[order.id]
                wizard.subject = subject
                wizard.body = body

    # -------------------------------------------------------------------------
    # Action
    # -------------------------------------------------------------------------

    def action_send(self):
        """Send the email and mark quotation as sent."""
        self.ensure_one()
        order = self.order_id

        # Validate analytic distribution
        order.filtered(
            lambda so: so.state in ('draft', 'sent')
        ).order_line._validate_analytic_distribution()

        # Generate PDF and attach it
        attachments = self.env['ir.attachment']
        report = self.env.ref('sale.action_report_saleorder', raise_if_not_found=False)
        if report:
            try:
                pdf_content, _ = report._render_qweb_pdf([order.id])
                doc_type = 'Quotation' if order.state in ('draft', 'sent') else 'Order'
                filename = f"{doc_type}_{order.name}.pdf".replace('/', '_')
                attachment = self.env['ir.attachment'].create({
                    'name': filename,
                    'type': 'binary',
                    'datas': pdf_content,
                    'res_model': 'sale.order',
                    'res_id': order.id,
                    'mimetype': 'application/pdf',
                })
                attachments |= attachment
            except Exception:
                pass

        # Send email via mail.thread
        mail_values = {
            'subject': self.subject,
            'body_html': self.body,
            'partner_ids': self.mail_partner_ids.ids,
            'attachment_ids': attachments.ids,
            'email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
        }

        template = self.template_id
        if template:
            template.send_mail(
                order.id,
                force_send=True,
                raise_exception=False,
                email_values={
                    'subject': self.subject,
                    'body_html': self.body,
                    'recipient_ids': [(4, pid) for pid in self.mail_partner_ids.ids],
                    'attachment_ids': attachments.ids,
                },
            )
        else:
            order.message_post(
                body=self.body,
                subject=self.subject,
                partner_ids=self.mail_partner_ids.ids,
                attachment_ids=attachments.ids,
                message_type='email',
                subtype_xmlid='mail.mt_comment',
            )

        # Mark as sent
        if order.state == 'draft':
            order.write({'state': 'sent'})

        return {'type': 'ir.actions.act_window_close'}

    def action_discard(self):
        return {'type': 'ir.actions.act_window_close'}
