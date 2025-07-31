{
    'name': "Lead Manage",
    'description': """
    
    """,

    'summary': """
                """,
    'author': "VK Data ApS",
    'website': "https://vkdata.dk",
    'category': 'CRM',
    'version': '17.0.1.0.0',

    'depends': ['base', 'crm', 'sms'],

    'data': [
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'views/crm_team_views.xml',
        'views/lead_allocate_views.xml',
        'views/res_users_views.xml',
        'report/crm_lead_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vkd_lead_manage/static/src/**/*',
            ('remove', 'vkd_lead_manage/static/src/**/*.dark.scss'),
        ],
        "web.assets_web_dark": [
            'vkd_lead_manage/static/src/**/*.dark.scss',
        ],
    },

    'license': 'OPL-1',
    'application': True,
    'installable': True,
    'auto_install': False,
}
