{
    'name': "Facebook Leads Integration",
    'summary': """
        Sync Facebook Leads with Odoo CRM""",

    'description': """
                    This module integrates Facebook Lead Ads with Odoo CRM, allowing to automatically sync leads generated 
                    through Facebook directly into Odoo CRM. It streamlines the process of capturing and managing leads, 
                    ensuring that valuable sales opportunities are not missed and are quickly available to the sales team.
                 """,
    'author': "VK Data ApS",
    'website': "https://vkdata.dk",

    'category': 'CRM',
    'version': '17.0.3.0.2',
    'license': 'OPL-1',
    'depends': ['crm', 'vkd_lead_manage', 'vkd_property_management'],

    'data': [
        'data/ir_cron_data.xml',
        'data/crm.facebook.form.mapping.csv',
        'security/ir.model.access.csv',
        'security/crm_facebook_leads_security.xml',
        'views/crm_lead_views.xml',
        'views/crm_facebook_page_views.xml',
        'views/crm_facebook_form_views.xml',
        'views/crm_facebook_form_mapping_views.xml',
        'views/res_config_settings_views.xml',
    ],
}
