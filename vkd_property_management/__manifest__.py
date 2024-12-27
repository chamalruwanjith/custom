# -*- coding: utf-8 -*-

{
    'name': "Property Management",
    'version': '17.0.1.0.0',
    'category': '',

    'summary': """This module offers dynamic property configuration, unit reservations, real-time stock checks,
            and validations. It seamlessly integrates with Odoo’s inventory and sales systems while supporting
            multi-currency and multi-company operations for efficient real estate management.""",

    'description': """
        Property Management Module for Odoo is a comprehensive solution for managing the lifecycle of apartments,
        towers, floors, and units. It features dynamic property configuration, unit reservations with agent limits,
        and validations to ensure data accuracy. The module integrates seamlessly with Odoo’s inventory, sales,
        offering real-time stock checks and automated workflows. Additional features include multi-currency and
        multi-company support, making it an efficient and user-friendly solution for modern real estate businesses.
    """,

    'author': "VK Data ApS",
    'website': "https://vkdata.dk",

    'depends': ['base', 'mail', 'stock', 'sale', 'product', 'sales_team'],
    'data': [
        'security/property_management_security.xml',
        'security/ir.model.access.csv',
        'data/unit_reservation_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/mail_templates.xml',
        'views/property_management_menus.xml',
        'views/apartment_details_views.xml',
        'views/floor_details_views.xml',
        'views/unit_details_views.xml',
        'views/sale_agent_views.xml',
        'views/res_config_settings_views.xml',
        'views/unit_reservation_views.xml',
        'views/tower_details_views.xml',
        'views/res_currency_views.xml',
        'views/product_template_views.xml',
        'wizards/sale_customer_select_views.xml',
    ],
    'license': 'OPL-1',
    'application': True,
    'installable': True,
    'auto_install': False,

}
