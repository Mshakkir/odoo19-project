# -*- coding: utf-8 -*-
from odoo import models, api, fields
import re


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    remove_invoice_button = fields.Boolean(
        string='Remove Invoice Button',
        default=False,
        help='Check this to remove the View Invoice button from email template'
    )

    @api.model
    def _render_template(self, template_txt, model_name, res_ids,
                         post_process=False, engine='jinja2',
                         minimal_qcontext=False, add_context=None):
        """Override to remove invoice button from rendered content"""

        results = super()._render_template(
            template_txt, model_name, res_ids,
            post_process=post_process, engine=engine,
            minimal_qcontext=minimal_qcontext, add_context=add_context
        )

        if self.remove_invoice_button:
            results = self._remove_invoice_button_from_html(results)

        return results

    def _remove_invoice_button_from_html(self, html_content):
        """Remove the View Invoice button from HTML content"""

        if not html_content:
            return html_content

        if isinstance(html_content, dict):
            return {k: self._remove_button_pattern(v) for k, v in html_content.items()}

        if isinstance(html_content, list):
            return [self._remove_button_pattern(item) for item in html_content]

        return self._remove_button_pattern(html_content)

    def _remove_button_pattern(self, content):
        """Remove button patterns from HTML string"""

        if not isinstance(content, str):
            return content

        patterns = [
            r'<a[^>]*href=["\']([^"\']*mail/view[^"\']*)["\'][^>]*>.*?View Invoice.*?</a>',
            r'<button[^>]*>[\s]*View Invoice[\s]*</button>',
            r'<a[^>]*href=["\']([^"\']*portal[^"\']*)["\'][^>]*>[\s]*View Invoice[\s]*</a>',
            r'<a[^>]*class=["\']([^"\']*btn[^"\']*)["\'][^>]*>[\s]*View Invoice[\s]*</a>',
            r'<table[^>]*class=["\']o_portal_sign_up[^"\']*["\'][^>]*>.*?</table>',
            r'<(?:span|div)[^>]*class=["\'](?:[^"\']*)?(?:o_invoice_button|oe_button_group)[^"\']*["\'][^>]*>.*?</(?:span|div)>',
        ]

        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)

        content = re.sub(r'\n\s*\n', '\n', content)

        return content

    def generate_email(self, res_ids, fields_to_return=None):
        """Override to process email subject and body"""

        results = super().generate_email(res_ids, fields_to_return)

        if self.remove_invoice_button:
            for res_id, email_values in results.items():
                if 'body_html' in email_values:
                    email_values['body_html'] = self._remove_button_pattern(
                        email_values['body_html']
                    )

        return results