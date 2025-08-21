{
    'name': 'FaceBook Leads Notifications',
    'version': '17.0.1.0.0',
    'summary': 'FaceBook Leads Notifications',
    'description': 'FaceBook Leads Notifications',
    'category': 'CRM',
    'author': "VK Data ApS",
    'website': "https://vkdata.dk",
    'depends': ['crm',
                'mail_mobile',
                'web_mobile',],
    'data': [
        'views/discuss_channel_views.xml',
        'data/mail_templates.xml',
    ],
    'installable': True,
    'auto_install': False
}
