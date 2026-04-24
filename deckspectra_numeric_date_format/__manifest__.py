# -*- coding: utf-8 -*-
# Part of DeckSpectra Technologies LLP. See LICENSE file for full copyright and licensing details.

{
    'name': 'Numeric Date Format',
    'version': '19.0.0.0',
    'category': 'Tools',
    'license': 'LGPL-3',
    'summary': 'This module improves UI consistency in Odoo by standardizing date fields across Form and List views. It replaces default shorthand styles with a uniform numerical format (such as DD/MM/YYYY or MM/DD/YYYY).',
    'description': """A technical utility module designed to override the default Odoo 19 date representation. This module automates the transition from "Day Month" (e.g., 16 Jan) to a full "Day/Month/Year" numerical format.""",
    'author': 'DeckSpectra Technologies LLP',
    'website': 'https://www.deckspectra.com',
    'depends': ['base','web'],
    'assets': {
        'web.assets_backend': [
            'deckspectra_numeric_date_format/static/src/js/date_format_override.js',
        ],
    },
    'images': ["static/description/Banner.gif"],
    'application': True,
    'installable': True,
}
