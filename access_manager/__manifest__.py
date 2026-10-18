{
    'name': 'Access Manager #Majidov',
    'version': '18.0.1.3.1',
    'summary': 'İstifadəçi əsaslı CRUD və record filter idarəetməsi',
    'description': """
Access Manager
==============
Bu modul hər istifadəçi üçün ayrıca:
  * Model səviyyəsində CRUD icazələri (oxu/yaz/yarat/sil)
  * Record səviyyəsində filtrlər (yalnız öz sənədləri / əlavə userlərin sənədləri)
təyin etməyə imkan verir.

Texniki yanaşma:
  * Qlobal record rule-lar (groups=False) → bütün qrupların üstündən keçir
  * User qruplarda qalır, menyular və standart funksionallıq itmir
""",
    'author': 'Custom',
    'category': 'Administration',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/access_config_views.xml',
        'views/access_role_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
