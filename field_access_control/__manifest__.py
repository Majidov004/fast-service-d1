{
    'name': 'Field Access Control #Majidov',
    'version': '18.0.1.0.2',
    'summary': 'User əsaslı sahə giriş nəzarəti (gizlət, readonly, məcburi, maska)',
    'description': """
Field Access Control
====================
Hər istifadəçi üçün fərdi sənəd yaradılır və həmin sənəddə:
- Hansı modelin hansı sahəsi
- Hansı şərt altında
- Necə davranacağı (gizli, readonly, məcburi, maska)
tənzimlənir.
    """,
    'author': 'Custom',
    'category': 'Technical',
    'depends': ['base', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/field_access_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
