#!/usr/bin/env python
# -*- coding: utf-8 -*-
# passerelle-imio-ia-aes - passerelle connector to IA AES IMIO PRODUCTS.
# Copyright (C) 2016  Entr'ouvert
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Decorateurs des endpoints:
# serializer_type='json-api' : Permet de serializer la reponse directement dans un data + format automatique pour un raise exception.

# Doc Entr'ouvert : authentificaiton pour utiliser les apis.
# https://doc-publik.entrouvert.com/tech/wcs/api-webservices/authentification/

#  Doc Entr'ouvert : Récupération de coordonnées
# https://doc-publik.entrouvert.com/tech/wcs/api-webservices/recuperation-des-donnees-d-un-formulaire/

#  Doc Entr'ouvert : Evolution du workflow
# https://doc-publik.entrouvert.com/tech/wcs/api-webservices/traitement-d-un-formulaire/

#TEST A FAIRE SUR :
#https://demo-formulaires.guichet-citoyen.be/tests-et-bac-a-sable/demo-cb-aes/1/jump/trigger/validate

#https://doc-publik.entrouvert.com/tech/connecteurs/developpement-d-un-connecteur/#Journalisation

import base64
import json
import magic
import suds
# e8f3c0686114ef12423c41b0eb99f939d455a2b3b470f3b509e0e3883dacc7e2
# ?email=info@immoassist.com&full=on&filter=all&algo=sha256&timestamp=2018-04-11T15:03:51Z&orig=immoassist&signature=rNG7271bs30MYvGYbYrjcNuJGHXfcc8eXocDZ4cv4Mo%3d
# https://demo-formulaires.guichet-citoyen.be/tests-et-bac-a-sable/demo-cb-aes/1/jump/trigger/validate
# ?algo=sha256&timestamp=2018-05-17T10:13:24Z&orig=aes&signature=ZmQxNTQzZDY0ZTM5YzU2N2FkZjFmYTEyOTdlZjBiOWU2ODhkZTVjYmNhODU2MmVjZTg0Yzk3YzRiYmViNWIzZQ==
from requests.exceptions import ConnectionError
from datetime import date, datetime
from django.db import models
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse, Http404

from passerelle.base.models import BaseResource
from passerelle.utils.api import endpoint
from passerelle.utils.jsonresponse import APIError

from xmlrpclib import ServerProxy

from suds.xsd.doctor import ImportDoctor, Import
from suds.transport.http import HttpAuthenticated

def get_client(model):
    try:
        return soap_get_client(model)
    except ConnectionError as e:
        raise APIError('i-ImioIaAes error: %s' % e)

def format_type(t):
    return {'id': unicode(t), 'text': unicode(t)}

def format_file(f):
    return {'status': f.status, 'id': f.nom, 'timestamp': f.timestamp}


class FileError(Exception):
    pass


class FileNotFoundError(Exception):
    http_status = 404

# https://192.168.252.14/inscriptions/newsletter/14/jump/trigger/validate

# http://local-formulaires.example.net/backoffice/management/demo-cb-aes/1/

# http://local-formulaires.example.net/travaux/demo-cb-aes/1/jump/trigger/validate

class IImioIaAes(BaseResource):
    server_url = models.CharField(max_length=128, blank=False,
            verbose_name=_('SERVER URL'),
            help_text=_('SERVER URL'))
    username = models.CharField(max_length=128, blank=True,
            verbose_name=_('Username'))
    password = models.CharField(max_length=128, blank=True,
            verbose_name=_('Password'))
    database_name = models.CharField(max_length=128, blank=False,
            verbose_name=_('Database name'))

    #keystore = models.FileField(upload_to='iparapheur', null=True, blank=True,
    #        verbose_name=_('Keystore'),
    #        help_text=_('Certificate and private key in PEM format'))

    category = _('Business Process Connectors')

    class Meta:
        verbose_name = _('i-ImioIaAes')

    @classmethod
    def get_verbose_name(cls):
        return cls._meta.verbose_name

    def get_aes_user_id(self):
        server = ServerProxy('{}/xmlrpc/2/common'.format(self.server_url))
        user_id = server.authenticate(self.database_name, self.username, self.password, {})
        return user_id

    def get_aes_server(self):
        server = ServerProxy('{}/xmlrpc/2/object'.format(self.server_url))
        return server

    @endpoint(serializer_type='json-api', perm='can_access')
    def tst_connexion(self, request, **kwargs):
        test = self.get_aes_server().execute_kw(
                self.database_name, self.get_aes_user_id(), self.password,
                'extraschool.parent','test', []
                )
        return test

    @endpoint(serializer_type='json-api', perm='can_access')
    def get_children(self, request, **kwargs):
        parent = {
            'nom':'aa',
            'prenom':'aaa',
            'email':request.GET['email']
            }
        children = self.get_aes_server().execute_kw(
                self.database_name, self.get_aes_user_id(), self.password,
                'extraschool.parent','get_children', [parent]
                )
        return children

    @endpoint(serializer_type='json-api', perm='can_access')
    def is_registered_parent(self, request, **kwargs):
        parent = {
            'nom':'aa',
            'prenom':'aaa',
            'email':request.GET['email']
            }
        is_registered_parent = self.get_aes_server().execute_kw(
                self.database_name, self.get_aes_user_id(), self.password,
                'extraschool.parent','is_registered_parent', [parent]
                )
        return is_registered_parent

    @endpoint(serializer_type='json-api', perm='can_access')
    def get_activities(self, request, **kwargs):
        child = {
            'id':request.GET['child_id']
            }
        activities = self.get_aes_server().execute_kw(
                self.database_name, self.get_aes_user_id(), self.password,
                'extraschool.child','get_activities', [child]
                )
        return activities

    @endpoint(serializer_type='json-api', perm='can_access')
    def get_activity_details(self, request, **kwargs):
        dt_begin = datetime.strptime(request.GET['begining_date_search'], '%d/%m/%Y')
        dt_end = datetime.strptime(request.GET['ending_date_search'], '%d/%m/%Y')
        activity = request.GET['activity_id']
        child_id  = request.GET['child_id']
        get_disponibilities = {
                'activity':activity,
                'child_id':child_id,
                'begining_date_search':dt_begin,
                'ending_date_search':dt_end
                }
        disponibilities = self.get_aes_server().execute_kw(
                self.database_name, self.get_aes_user_id(), self.password,
                'extraschool.activity','get_activity_details', [get_disponibilities]
                )
        return disponibilities
