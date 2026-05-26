Passerelle connector to communicate with AES
============================================

Installation
------------

 - add to Passerelle installed apps settings:
   INSTALLED_APPS += ('passerelle_imio_ia_aes',)

 - enable module:
   PASSERELLE_APP_PASSERELLE_IMIO_IA_AES_ENABLED = True


Usage
-----

 - create and configure new connector
   - Title/description: whatever you want
   - Certificate check: uncheck if the service has no valid certificate

 - be carefull : To use some method with AES, they are two environment variables : 
                 settings.AUTHENTIC_URL, settings.AES_LOGIN, settings.AES_PASSWORD
                 Register in passerelle settings.


Usage in w.c.s.
---------------


Tests
-----

Lancer les tests unitaires :

    DJANGO_SETTINGS_MODULE=passerelle.settings PASSERELLE_SETTINGS_FILE=tests/settings.py pytest tests/

(adapter le chemin de `pytest` selon l'environnement virtuel utilisé,
par exemple `~/envs/publik-env-py3/bin/pytest`)

À ce jour la suite ne teste qu'une fonction utilitaire pure
(`compute_amount_with_balance`) qui n'a aucune dépendance Django :
en pratique `pytest tests/` sans les variables d'environnement suffit.
La forme complète ci-dessus est néanmoins conservée parce qu'elle suit
la convention Passerelle (cf. https://doc-publik.entrouvert.com/dev/developpement-d-un-connecteur/#Tests-unitaires)
et qu'elle sera requise dès qu'un test touchera au framework (modèles
Django, endpoints HTTP via `django-webtest`, accès base de données…).
