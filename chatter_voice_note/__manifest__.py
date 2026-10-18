# -*- coding: utf-8 -*-
{
    'name': 'Chatter Voice Note',
    'version': '18.0.1.0.0',
    'category': 'Productivity/Discuss',
    'summary': 'Record voice notes directly in the chatter (Log note / Send message)',
    'description': """
Chatter Voice Note
==================

Odoo-nun Discuss kanallarında mövcud olan səsli mesaj yazıcısını (mikrofon düyməsi)
istənilən modelin chatter-ində — həm **Log note**, həm də **Send message** rejimində — aktiv edir.

- Mikrofon düyməsi chatter composer-in düymələr sırasında (Log / Send düyməsinin solunda) görünür.
- Yazılan səs `.mp3` faylı kimi mesaja qoşma (attachment) olaraq əlavə olunur və
  chatter-də dalğa formalı səs pleyeri ilə göstərilir.
- Maksimum yazma müddəti sistem parametri ilə tənzimlənir
  (`chatter_voice_note.max_duration`, saniyə ilə; standart 300 = 5 dəqiqə).
  Odoo-nun öz limiti 60 saniyədir — bu modul onu genişləndirir.

Qeyd: brauzer mikrofona yalnız təhlükəsiz kontekstdə (HTTPS və ya localhost) icazə verir.
""",
    'author': 'Custom Development',
    'depends': ['mail', 'web'],
    'data': [
        'data/ir_config_parameter.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'chatter_voice_note/static/src/voice_note.scss',
            'chatter_voice_note/static/src/composer_patch.js',
            'chatter_voice_note/static/src/composer_patch.xml',
            'chatter_voice_note/static/src/voice_recorder_patch.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
