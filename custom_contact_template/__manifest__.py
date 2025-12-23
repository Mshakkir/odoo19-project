{
    "name": "Custom Contact Page",
    "version": "1.0.0",
    "category": "Website",
    "summary": "Custom Contact Us page",
    "depends": ["website"],
    "data": [
        "views/contact_template.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "custom_contact_template/static/src/css/contactstyle.css",
        ],
    },
    "installable": True,
    "license": "LGPL-3",
}
