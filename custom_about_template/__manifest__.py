{
    "name": "custom About Us Page",
    "version": "1.0.0",
    "category": "Website",
    "summary": "Custom About Us page for Airmixs website",
    "description": """
Custom designed About Us page for Airmixs website.
Includes hero section, mission & vision, company story,
offerings, values, industries served, and CTA section.
""",
    "author": "Airmixs",
    "website": "https://www.airmixs.com",
    "depends": [
        "website",
    ],
    "data": [
        "views/about_template.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "custom_about_template/static/src/css/aboutstyle.css",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
