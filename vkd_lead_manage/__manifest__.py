{
    'name': "Lead Manage",
    'summary': "Manage lead allocation, shifts, and response-time reporting for CRM leads.",
    'description': """
Lead Manage

Extends Odoo CRM with tools to manage inbound lead workflows:
Lead Types – configurable type labels (e.g. NC, WB) attached to leads.
Shift Configuration – define named shifts with start/end hours and overnight support.
Lead Allocation – assign leads to agents (single or round-robin) per team and shift window; auto-computes shift times from the shift definition.
Response-Time Tracking – tracks attend time and response time (minutes) on each lead.
Excel Reports – generates a multi-sheet workbook covering lead detail, attendance summary, agent × date pivot, project/type/country/team breakdown, and agent lead-count pivot; filterable by date range and shift.
    """,
    'author': "VK Data ApS",
    'website': "https://vkdata.dk",
    'category': 'CRM',
    'version': '17.0.1.0.5',

    'depends': ['base', 'crm', 'sms'],

    'data': [
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'views/crm_team_views.xml',
        'views/lead_type_views.xml',
        'views/lead_shift_views.xml',
        'views/lead_allocate_views.xml',
        'views/res_users_views.xml',
        'views/crm_lead_log_views.xml',
        'report/crm_lead_report.xml',
        'wizard/lead_allocate_import_views.xml',
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
