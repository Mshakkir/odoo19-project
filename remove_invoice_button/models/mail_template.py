# -*- coding: utf-8 -*-
from odoo import models, fields
import re


class MailTemplate(models.Model):
    """Mail Template with invoice button removal feature"""

    _inherit = 'mail.template'

    remove_invoice_button = fields.Boolean(
        string='Remove Invoice Button',
        default=False,
        help='Check this to remove the View Invoice button from email template'
    )

    def generate_email(self, res_ids, fields_to_return=None):
        """
        Override generate_email to remove invoice button from email body.

        This is the CORRECT method to override for modifying email content.
        It's called AFTER the template is rendered, so we get the final HTML.
        """

        # Call parent to get generated emails
        results = super().generate_email(res_ids, fields_to_return)

        # If feature is disabled, return as-is
        if not self.remove_invoice_button:
            return results

        # Process each generated email
        for res_id, email_values in results.items():
            if 'body_html' in email_values and email_values['body_html']:
                # Remove button patterns from HTML
                email_values['body_html'] = self._remove_button_pattern(
                    email_values['body_html']
                )

        return results

    def _remove_button_pattern(self, content):
        """
        Remove "View Invoice" button patterns from HTML string.

        Handles multiple button formats:
        - Standard HTML links with mail/view href
        - Portal access links
        - Bootstrap styled buttons
        - Odoo specific button markup
        """

        if not isinstance(content, str):
            return content

        # Regex patterns to match various button formats
        patterns = [
            # Pattern 1: Standard link with 'mail/view' in href
            r'<a[^>]*href=["\']([^"\']*mail/view[^"\']*)["\'][^>]*>.*?View Invoice.*?</a>',

            # Pattern 2: HTML button element
            r'<button[^>]*>[\s]*View Invoice[\s]*</button>',

            # Pattern 3: Portal access link
            r'<a[^>]*href=["\']([^"\']*portal[^"\']*)["\'][^>]*>[\s]*View Invoice[\s]*</a>',

            # Pattern 4: Bootstrap button with btn class
            r'<a[^>]*class=["\']([^"\']*btn[^"\']*)["\'][^>]*>[\s]*View Invoice[\s]*</a>',

            # Pattern 5: Odoo portal sign-up table
            r'<table[^>]*class=["\']o_portal_sign_up[^"\']*["\'][^>]*>.*?</table>',

            # Pattern 6: Div or span with button class
            r'<(?:span|div)[^>]*class=["\'](?:[^"\']*)?(?:o_invoice_button|oe_button_group)[^"\']*["\'][^>]*>.*?</(?:span|div)>',
        ]

        # Apply each pattern to remove matching elements
        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)

        # Clean up excess whitespace left behind
        content = re.sub(r'\n\s*\n', '\n', content)

        return content