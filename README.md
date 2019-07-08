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

