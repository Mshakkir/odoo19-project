{
    "name": "Date Filter on Customer Portal",
    "version": "19.0.1.0.0",
    "sequence": 1,
    "category": "Portal",
    "description": "Add Date Filter in My Order page of Customer Portal",
    "summary": "Add Date Filter in My Order page of Customer Portal",
    "author": "Taube Digital",
    "website": "https://www.taube-digital.com",
    "company": "Taube Digital",
    "depends": ["sale", "portal"],
    "images": [
        "./static/description/date_filter_screenshot.png",
        "./static/description/icon.png"
    ],
    "data": [
        "views/sale_portal_template.xml",
    ],
    # No JavaScript assets needed!
    "support": "",
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
    "application": False,
}