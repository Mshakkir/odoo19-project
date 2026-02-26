# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.tools import html_escape
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
                         minimal_qcontext=False):
        """Override to remove invoice button from rendered content"""

        # Call parent method to get rendered content
        results = super()._render_template(
            template_txt, model_name, res_ids,
            post_process=post_process, engine=engine,
            minimal_qcontext=minimal_qcontext
        )

        # Remove invoice button if enabled
        if self.remove_invoice_button:
            results = self._remove_invoice_button_from_html(results)

        return results

    def _remove_invoice_button_from_html(self, html_content):
        """Remove the View Invoice button from HTML content"""

        if not html_content:
            return html_content

        # If it's a dictionary (for multiple results), process each value
        if isinstance(html_content, dict):
            return {k: self._remove_button_pattern(v) for k, v in html_content.items()}

        # If it's a string or list, process accordingly
        if isinstance(html_content, list):
            return [self._remove_button_pattern(item) for item in html_content]

        return self._remove_button_pattern(html_content)

    def _remove_button_pattern(self, content):
        """Remove button patterns from HTML string"""

        if not isinstance(content, str):
            return content

        # Remove View Invoice button - various patterns
        patterns = [
            # Pattern 1: Standard button with href containing 'mail/view'
            r'<a[^>]*href=["\']([^"\']*mail/view[^"\']*)["\'][^>]*>.*?View Invoice.*?</a>',

            # Pattern 2: Button element with View Invoice text
            r'<button[^>]*>[\s]*View Invoice[\s]*</button>',

            # Pattern 3: Link with portal access
            r'<a[^>]*href=["\']([^"\']*portal[^"\']*)["\'][^>]*>[\s]*View Invoice[\s]*</a>',

            # Pattern 4: Bootstrap button class
            r'<a[^>]*class=["\']([^"\']*btn[^"\']*)["\'][^>]*>[\s]*View Invoice[\s]*</a>',

            # Pattern 5: Odoo specific button markup
            r'<table[^>]*class=["\']o_portal_sign_up[^"\']*["\'][^>]*>.*?</table>',

            # Pattern 6: Span or div containing button
            r'<(?:span|div)[^>]*class=["\'](?:[^"\']*)?(?:o_invoice_button|oe_button_group)[^"\']*["\'][^>]*>.*?</(?:span|div)>',
        ]

        # Apply all patterns with DOTALL flag for multiline matching
        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)

        # Clean up extra whitespace that might be left behind
        content = re.sub(r'\n\s*\n', '\n', content)

        return content

    def generate_email(self, res_ids, fields_to_return=None):
        """Override to process email subject and body"""

        results = super().generate_email(res_ids, fields_to_return)

        # Remove button from email body if needed
        if self.remove_invoice_button:
            for res_id, email_values in results.items():
                if 'body_html' in email_values:
                    email_values['body_html'] = self._remove_button_pattern(
                        email_values['body_html']
                    )

        return results