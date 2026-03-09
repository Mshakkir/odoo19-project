from odoo import models, fields, api, _


class SaleOrderSendWizard(models.TransientModel):
    _name = 'sale.order.send.wizard'
    _description = 'Sale Order Send Wizard'

    order_id = fields.Many2one(
        'sale.order', string='Sale Order', required=True, ondelete='cascade'
    )
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
    # Required by html_mail widget
    can_edit_body = fields.Boolean(default=True)
    # Required by mail_composer_template_selector widget
    model = fields.Char(default='sale.order')
    res_ids = fields.Char(compute='_compute_res_ids')

    @api.depends('order_id')
    def _compute_res_ids(self):
        for wizard in self:
            wizard.res_ids = str(wizard.order_id.ids)

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
                try:
                    subject = template._render_field(
                        'subject', order.ids, compute_lang=True
                    )[order.id]
                    wizard.subject = subject
                except Exception:
                    doc_type = 'Quotation' if order.state in ('draft', 'sent') else 'Order'
                    wizard.subject = f"{order.company_id.name} {doc_type} (Ref {order.name})"
            else:
                doc_type = 'Quotation' if order.state in ('draft', 'sent') else 'Order'
                wizard.subject = f"{order.company_id.name} {doc_type} (Ref {order.name})"

    @api.depends('order_id', 'template_id')
    def _compute_body(self):
        for wizard in self:
            order = wizard.order_id
            template = wizard.template_id
            if template:
                try:
                    body = template._render_field(
                        'body_html', order.ids, compute_lang=True,
                        options={'post_process': True}
                    )[order.id]
                    wizard.body = body
                except Exception:
                    wizard.body = False
            else:
                wizard.body = False

    @api.onchange('template_id')
    def _onchange_template_id(self):
        for wizard in self:
            order = wizard.order_id
            if wizard.template_id:
                try:
                    wizard.subject = wizard.template_id._render_field(
                        'subject', order.ids, compute_lang=True
                    )[order.id]
                    wizard.body = wizard.template_id._render_field(
                        'body_html', order.ids, compute_lang=True,
                        options={'post_process': True}
                    )[order.id]
                except Exception:
                    pass

    def action_send(self):
        """Send the email and mark quotation as sent."""
        self.ensure_one()
        order = self.order_id

        order.filtered(
            lambda so: so.state in ('draft', 'sent')
        ).order_line._validate_analytic_distribution()

        # Generate PDF attachment
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

        # Send via template or message_post
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