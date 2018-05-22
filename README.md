Passerelle connector to Liege Lisrue service
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

 - test service by clicking on the available links
   - the /testConnection/ endpoint try to establish a connection with IA AES
   - the /test_createItem/ endpoint try to create a new point in IA AES



Usage in w.c.s.
---------------

 - createItem
   - url sample with get method
     createItem?meetingConfigId=meeting-config-college&proposingGroupId=dirgen&title=Mon%20nouveau%20point&description=Ma%20nouvelle%20description&decision=Ma%20nouvelle%20decision

   - wcs workflow action "call webservice"
     URL : 
         http://local-passerelle.example.net/passerelle-imio-ia-aes/ia-aes-connecteur/createItem
     SEND POST DATA :      
         proposingGroupId : dirgen
         meetingConfigId : meeting-config-college
         description : ="{} {} {} {} {}".format("Réservation de la salle :",form_var_salle,"par", form_var_prenom, form_var_nom)
         title : My title
         decision : My decision

         extraAttrs : [{"key":"detailedDescription","value":"<p>{}</p>".format(form_var_user_description)}]
      OR
         detailedDescription : [form_var_user_description]
