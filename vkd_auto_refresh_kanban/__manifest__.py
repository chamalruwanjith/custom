# -*- coding: utf-8 -*-
{
    'name': "Automatic Kanban Refresher",
    'summary': "Automatically refreshes Kanban views",
    'description': """
        This module enables automatic refreshing of Kanban views on feed, ensuring that data is always up-to-date without manual intervention.
    """,
    'author': 'VK DATA ApS',
    'website': 'https://vkdata.dk/',
    'version': '17.0.1.0.1',
    'license': 'OPL-1',
    'depends': ["web", 'crm'],
    'assets': {
        'web.assets_backend': [
            "vkd_auto_refresh_kanban/static/src/js/crm_kanban_view.js",
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
