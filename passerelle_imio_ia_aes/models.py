#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
# serializer_type='json-api' : Permet de serializer la reponse directement dans un data +
# format automatique pour un raise exception.

# Doc Entr'ouvert : authentificaiton pour utiliser les apis.
# https://doc-publik.entrouvert.com/tech/wcs/api-webservices/authentification/

#  Doc Entr'ouvert : Récupération de coordonnées
# https://doc-publik.entrouvert.com/tech/wcs/api-webservices/recuperation-des-donnees-d-un-formulaire/

#  Doc Entr'ouvert : Evolution du workflow
# https://doc-publik.entrouvert.com/tech/wcs/api-webservices/traitement-d-un-formulaire/

# TEST A FAIRE SUR :
# https://demo-formulaires.guichet-citoyen.be/tests-et-bac-a-sable/demo-cb-aes/1/jump/trigger/validate

# https://doc-publik.entrouvert.com/tech/connecteurs/developpement-d-un-connecteur/#Journalisation
# e8f3c0686114ef12423c41b0eb99f939d455a2b3b470f3b509e0e3883dacc7e2
# ?email=info@immoassist.com&full=on&filter=all&algo=sha256&timestamp=2018-04-11T15:03:51Z&orig=immoassist&signature=rNG7271bs30MYvGYbYrjcNuJGHXfcc8eXocDZ4cv4Mo%3d
# https://demo-formulaires.guichet-citoyen.be/tests-et-bac-a-sable/demo-cb-aes/1/jump/trigger/validate
# ?algo=sha256&timestamp=2018-05-17T10:13:24Z&orig=aes&signature=ZmQxNTQzZDY0ZTM5YzU2N2FkZjFmYTEyOTdlZjBiOWU2ODhkZTVjYmNhODU2MmVjZTg0Yzk3YzRiYmViNWIzZQ==

# import ast
import base64
import datetime
try:
    import http.client
except ImportError:
    import httplib
import io as BytesIO
import logging
import random
import requests
import json
try:
    from urllib.parse import urlparse
    from urllib.parse import urljoin
except ImportError:
    import urlparse

import xmlrpc.client
from xmlrpc.client import ServerProxy


from datetime import datetime as dt
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.http import HttpResponse
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from passerelle.base.models import BaseResource
from passerelle.base.signature import sign_url
from passerelle.compat import json_loads
from passerelle.utils.api import endpoint


def format_type(t):
    return {"id": force_text(t), "text": force_text(t)}


def format_file(f):
    return {"status": f.status, "id": f.nom, "timestamp": f.timestamp}


class FileError(Exception):
    pass


class FileNotFoundError(Exception):
    http_status = 404


# https://192.168.252.14/inscriptions/newsletter/14/jump/trigger/validate
# http://local-formulaires.example.net/backoffice/management/demo-cb-aes/1/
# http://local-formulaires.example.net/travaux/demo-cb-aes/1/jump/trigger/validate


class ProxiedTransport(xmlrpc.client.Transport):
    def set_proxy(self, proxy):
        self.proxy = proxy

    def make_connection(self, host):
        self.realhost = host
        h = httplib.HTTPConnection(self.proxy)
        return h

    def send_request(self, connection, handler, request_body):
        connection.putrequest("POST", "http://%s%s" % (self.realhost, handler))

    def send_host(self, connection, host):
        connection.putheader("Host", self.realhost)


logger = logging.getLogger(__name__)


class IImioIaAes(BaseResource):
    server_url = models.CharField(
        max_length=128,
        blank=False,
        verbose_name=_("SERVER URL"),
        help_text=_("SERVER URL"),
    )
    username = models.CharField(max_length=128, blank=True, verbose_name=_("Username"))
    password = models.CharField(max_length=128, blank=True, verbose_name=_("Password"))
    database_name = models.CharField(
        max_length=128, blank=False, verbose_name=_("Database name")
    )

    category = _("Business Process Connectors")
    api_description = (
        "Ce connecteur propose les méthodes d'échanges avec le produit IA-AES."
    )

    class Meta:
        verbose_name = _("i-ImioIaAes")

    @classmethod
    def get_verbose_name(cls):
        return cls._meta.verbose_name

    def get_aes_user_id(self):
        server = ServerProxy("{}/xmlrpc/2/common".format(self.server_url))
        try:
            user_id = server.authenticate(
                self.database_name, self.username, self.password, {}
            )
        except Exception as e:
            self.logger.error(
                "get_aes_user_id : server.authenticate error : {}".format(str(e))
            )
            raise
        return user_id

    def get_aes_server(self):
        server = ServerProxy(
            "{}/xmlrpc/2/object".format(self.server_url), allow_none=True
        )
        return server

    def get_aes_report(self):
        report = ServerProxy("{}/xmlrpc/2/report".format(self.server_url))
        return report

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Tester la connexion avec AES",
    )
    def test_connexion(self, request):
        test = self.get_aes_server().execute_kw(
               self.database_name,
               self.get_aes_user_id(),
               self.password,
               "aes_api.aes_api",
               "hello_world",
               [],
        )
        return test

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Récupération de la fiche santé d'un enfant",
        parameters={
            "child_id": {
                "description": "Identifiant d'un enfant",
                "example_value": "786",
            }
        },
    )
    def get_child_health_sheet(self, request, **kwargs):
        if request is not None:
            child = {"id": request.GET["child_id"]}
        else:
            child = kwargs
        health_sheet = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "get_child_health_sheet",
            [child],
        )
        return {"data": health_sheet}

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Enregistrement d'un menu pour un enfant",
        methods=["post",],
        parameters={
            "meals": {
                "description": "Liste des repas et leurs dates",
                "example_value": [
                    "_03-07-2019_fruit",
                    "_04-07-2019_potage",
                    "_04-07-2019_repas",
                    "_02-07-2019_potage",
                    "_02-07-2019_repas",
                ],
            },
            "child_id": {
                "description": "Identifiant d'un enfant",
                "example_value": "786",
            },
            "form_id": {"description": "Num de demande", "exemple_value": "42"},
        },
    )
    def post_child_meal(self, request, *args, **kwargs):
        # data = dict([(x, request.GET[x]) for x in request.GET.keys()])
        if request.body:
            occurences_load = json_loads(request.body)
        is_add = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "post_child_meal",
            [occurences_load],
        )
        return is_add

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        methods=["post",],
        description="mise a jour fiche sante",
    )
    def post_child_health_sheet(self, request, *args, **kwargs):
        try:
            occurences_load = json_loads(request.body)
            fields = occurences_load.get("fields")
        except ValueError as e:
            raise ValueError(e.message)
        is_update = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "post_child_health_sheet",
            [fields],
        )
        return is_update

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="get implantation scholaire",
    )
    def get_schoolimplantation(self, request):
        schools = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "extraschool.schoolimplantation",
            "search_read",
            [[]],
            {"fields": ["name"]},
        )
        lst_schools = []
        for school in schools:
            d = school
            d["text"] = d.pop("name")
            lst_schools.append(d)
        return {"data": lst_schools}

    @endpoint(
        serializer_type="json-api", perm="can_access", description="get levels",
    )
    def get_levels(self, request):
        levels = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "extraschool.level",
            "search_read",
            [[]],
            {"fields": ["name"]},
        )
        lst_levels = []
        for level in levels:
            l = level
            l["text"] = l.pop("name")
            lst_levels.append(l)
        return {"data": lst_levels}

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="get child types (cpas, aucun)",
    )
    def get_child_types(self, request):
        childtypes = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "extraschool.childtype",
            "search_read",
            [[]],
            {"fields": ["name"]},
        )
        lst_childtypes = []
        for childtype in childtypes:
            c = childtype
            c["text"] = c.pop("name")
            lst_childtypes.append(c)
        return {"data": lst_childtypes}

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Récupérer les enfants pour le parent connecté",
        parameters={
            "email": {
                "description": "Adresse e-mail d'un parent AES/TS",
                "example_value": "demotsaes@imio.be",
            }
        },
    )
    def get_children(self, request, **kwargs):
        parent = {"email": request.GET["email"]}
        if parent["email"] == "":
            return False
        try:
            children = self.get_aes_server().execute_kw(
                self.database_name,
                self.get_aes_user_id(),
                self.password,
                "aes_api.aes_api",
                "get_children",
                [parent],
            )
            return children
        except Exception:
            return False


    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Récupérer les enfants pour le parent connecté, en interrogeant le RN du parentplutôt que son mail",
        parameters={
            "nrn": {
                "description": "Numéro de registre national d'un parent AES/TS",
                "example_value": "00000000097",
            }
        },
    )
    def get_children_by_parent_nrn(self, request, **kwargs):
        parent = {"nrn": request.GET["nrn"]}
        if parent["nrn"] == "":
            return "No nrn"
        try:
            children = self.get_aes_server().execute_kw(
                self.database_name,
                self.get_aes_user_id(),
                self.password,
                "aes_api.aes_api",
                "get_children",
                [parent],
            )
            return children
        except Exception:
            return False


    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Demander à AES si l'enfant existe en fonction de son numéro national. Renvoie True le cas échéant",
        parameters={
            "nrn": {
                "description": "Numéro de registre national d'un enfant",
                "example_value": "00000000097",
            }
        },
    )
    def is_child_registered(self, request, **kwargs):
        child = {"nrn": request.GET["nrn"]}
        if child["nrn"] == "":
            return "Error - No nrn given"
        try:
            is_child_registered = self.get_aes_server().execute_kw(
                self.database_name,
                self.get_aes_user_id(),
                self.password,
                "aes_api.aes_api",
                "get_children_by_rn",
                [child],
            )
            return is_child_registered
        except Exception:
            return False

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Récupérer les enfants avec leur liste d'activités",
        parameters={
            "mail": {
                "description": "Adresse e-mail d'un parent AES/TS",
                "example_value": "demotsaes@imio.be",
            }
        },
    )
    def get_chidren_with_activities(self, request, **kwargs):
        try:
            data = {}
            new_children = []
            children = self.get_children(request)
            for child in children.get("data"):
                child_activity = self.get_activities(None, id=child.get("id"))
                child.update(activities=child_activity.get("data"))
                new_children.append(child)
            data["data"] = new_children
            data["parent"] = request.GET["mail"]
            return data
        except Exception:
            return False

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        methods=["post"],
        description="Enregistre un nouveau parent",
    )
    def parent_registration(self, request, **kwargs):
        if request.body:
            parent = json_loads(request.body)
        registration_id = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "extraschool.parent",
            "create",
            [parent],
        )
        return registration_id

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Recupere l'id d'un parent dans aes",
    )
    def get_parent_id(self, request, email=None, nrn=None):
        if request.body:
            params = json_loads(request.body)
            data = {"email": params.get("email"), "nrn": params.get("nrn")}
        else:
            data = dict([(x, request.GET[x]) for x in request.GET.keys()])
        parent_id = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "get_parent_id",
            [data],
        )
        return parent_id

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        methods=["post"],
        description="Enregistre un nouvel enfant",
    )
    def child_registration(self, request, **kwargs):
        if request.body:
            params = json_loads(request.body)
        parent_id = self.get_parent_id(request)
        parentid = {u"parentid": force_text(parent_id.get("id"))}
        params.update(parentid)
        params = {
            key: value
            for (key, value) in params.items()
            if key
            in [
                "childtypeid",
                "firstname",
                "lastname",
                "schoolimplantation",
                "levelid",
                "parentid",
                "birthdate",
                "rn",
            ]
        }
        registration_id = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "extraschool.child",
            "create",
            [params],
        )
        return registration_id

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Vérifier qu'un parent existe bien dans AES",
        parameters={
            "email": {
                "description": "Adresse e-mail du parent",
                "example_value": "demotsaes@imio.be",
            },
            "nrn": {
                "description": "Numéro de registre national du parent",
                "example_value": "00000000097",
            },
        },
    )
    def is_registered_parent(self, request, **kwargs):
        import urllib

        idp_service = list(settings.KNOWN_SERVICES['authentic'].values())[0]
        api_url = sign_url(
                urljoin(
                    idp_service['url'],
                    'api/users/?email=%s&orig=%s' % (urllib.parse.quote_plus(request.GET["email"]), idp_service.get('orig'))),
                key=idp_service.get('secret'))
        r = self.requests.get(api_url)
        nrn = (
            r.json().get("results")[0].get("niss")
            if r is not None
            else request.GET["nrn"]
        )
        parent = {"email": request.GET["email"], "nrn": nrn}
        if parent["email"] == "":
            return False
        is_registered_parent = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "is_registered_parent",
            [parent],
        )
        return is_registered_parent

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Récupérer les activités pour un enfant donné",
        parameters={
            "child_id": {"description": "Identifiant d'un enfant", "example_value": "0"}
        },
    )
    def get_activities(self, request, **kwargs):
        try:
            if request is not None:
                child = {"id": request.GET["child_id"]}
            else:
                child = kwargs
            activities = self.get_aes_server().execute_kw(
                self.database_name,
                self.get_aes_user_id(),
                self.password,
                "aes_api.aes_api",
                "get_activities",
                [child],
            )
            return activities
        except ValueError as e:
            raise ParameterTypeError(e.message)


    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Récupérer les repas auxquels un enfant donné est inscrit",
        parameters={
            "child_id": {"description": "Identifiant d'un enfant", "example_value": "0"}
        },
    )
    def get_child_meals(self, request, **kwargs):
        try:
            if request is not None:
                child = {"id": request.GET["child_id"]}
            else:
                child = kwargs
            meals = self.get_aes_server().execute_kw(
                self.database_name,
                self.get_aes_user_id(),
                self.password,
                "aes_api.aes_api",
                "get_child_meals",
                [child],
            )

            # build a list of dict
            formated_meals = [{'id': meal, 'text': meal[1:11]} for meal in meals]

            # sort meals
            sorted_meals = sorted(formated_meals, key=lambda i: i['text'])

            # construct result
            result = {'data': sorted_meals}

            return result

        except ValueError as e:
            raise ParameterTypeError(e.message)


    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Récupérer les détails d'une activité dans une période donnée pour un enfant donné.",
        parameters={
            "activity_id": {
                "description": "Identifiant d'une activité",
                "example_value": "0",
            },
            "child_id": {
                "description": "Identifiant d'un enfant",
                "example_value": "0",
            },
            "begining_date_search": {
                "description": "Début de la période dans laquelle chercher les occurences de l'activité",
                "example_value": "27/11/2018",
            },
            "ending_date_search": {
                "description": "Fin de la période dans laquelle chercher les occurences de l'activité",
                "example_value": "31/12/2019",
            },
        },
    )
    def get_activity_details(self, request, **kwargs):
        dt_begin = dt.strptime(request.GET["begining_date_search"], "%d/%m/%Y")
        dt_end = dt.strptime(request.GET["ending_date_search"], "%d/%m/%Y")
        activity = request.GET["ws_activity_id"]
        child_id = request.GET["ws_child_id"]
        get_disponibilities = {
            "activity": activity,
            "child_id": child_id,
            "begining_date_search": dt_begin,
            "ending_date_search": dt_end,
        }
        disponibilities = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "get_activity_details",
            [get_disponibilities],
        )
        return disponibilities

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        methods=["post"],
        description="Enregistrement d'un enfant à une activité",
    )
    def add_registration_child(self, request, *args, **kwargs):
        data = dict([(x, request.GET[x]) for x in request.GET.keys()])
        if request.body:
            occurences_load = json_loads(request.body)
        is_registration_child = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "add_registration_child",
            [occurences_load],
        )
        return is_registration_child

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        methods=["post"],
        description="Enregistrement d'un enfant aux journees de plaines et aux sous-act",
        parameters={
            "child_id": {
                "description": "Identifiant d'un enfant",
                "example_value": "1",
            },
            "data": {
                "description": "Selected items",
                "example_value": "{'activities': [{'week': 22, 'activity_id': '86', 'year': '2021'}, {'week': 23, 'activity_id': '90', 'year': '2021'}], 'child_id': '1137', 'form_id': '9'}",
            },
        },
    )
    def add_registration_child_plaine(self, request, *args, **kwargs):

        input_activities = json.loads(request.body)
        aes_formated_activities = []

        for activity in input_activities["activities"]:
            splitted_id = activity["id"].split('_')
            aes_formated_activities.append({
                "year": splitted_id[0],
                "activity_id": splitted_id[2],
                "week": activity["week"]
            })

        data = {
            "activities": aes_formated_activities,
            "form_id": input_activities["form_id"],
            "child_id": input_activities["child_id"]
        }

        response = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "add_registration_child_plaine",
            [data]
        )
        return response

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="get week theme",
        parameters={
            "activity_id": {
                "description": "Identifiant d'une activite",
                "example_value": "3415",
            },
            "week_number": {
                "description": "numero de la semaine dans l'annee",
                "example_value": "28",
            },
        },
    )
    def get_week_theme(self, request, activity_id, week_number):
        debug = False
        if debug is True:
            return {"data": [{"name": "Theme Label"}]}
        if getattr(request, "body", None) is not None:
            params = json_loads(request.body)
            activity_id = params.get("activity_id")
            week_number = params.get("week_number")
        data = {"activity_id": activity_id, "week_number": week_number}
        theme = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "get_week_theme",
            [data],
        )
        return theme

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Plaines (brutes) retournées par aes",
        parameters={
            "child_id": {
                "description": "Identifiant d'un enfant",
                "example_value": "1",
            },
            "begining_date_search": {
                "description": "Début de la période dans laquelle chercher les occurences de l'activité",
                "example_value": "01/01/2020",
            },
            "ending_date_search": {
                "description": "Fin de la période dans laquelle chercher les occurences de l'activité",
                "example_value": "31/12/2020",
            },
        },
    )
    def get_raw_plaines(self, request, **kwargs):
        data = dict([(x, request.GET[x]) for x in request.GET.keys()])
        list_plaines_pp = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "get_plaine",
            [data],
        )
        return list_plaines_pp

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Plaines retournées par aes version 2, avec données structurées",
        parameters={
            "child_id": {
                "description": "Identifiant d'un enfant",
                "example_value": "1",
            },
            "begining_date_search": {
                "description": "Début de la période dans laquelle chercher les activités",
                "example_value": "01/01/2020",
            },
            "ending_date_search": {
                "description": "Fin de la période dans laquelle chercher les activités",
                "example_value": "31/12/2020",
            },
            "category_name": {
                "description": "Type d'activité à rechercher",
                "example_value": "Plaine"
            }
        },
    )
    def get_plaines_v2(self, request, **kwargs):
        data = dict([(x, request.GET[x]) for x in request.GET.keys()])
        try:
            response = self.get_aes_server().execute_kw(
                self.database_name,
                self.get_aes_user_id(),
                self.password,
                "aes_api.aes_api",
                "get_plaine_2",
                [data],
            )
        except Exception as e:
            response = str[data, str(e)]

        weeks = set()
        result = []

        for activity in response["data"]:
            if activity['week'] not in weeks:
                result.append({
                    'id': activity['week'],
                    'text': 'Semaine {}'.format(activity['week']),
                    'activities': [{
                        'id': '{}_{}_{}'.format(activity['year'], activity['week'], activity['activity_id']),
                        'text': activity['activity_name'],
                        'week': activity['week']
                    }],
                    'week': activity['week']
                })
                weeks.add(activity['week'])
            else:
                new_activity = {
                    'id': '{}_{}_{}'.format(activity['year'], activity['week'], activity['activity_id']),
                    'text': activity['activity_name'],
                    'week': activity['week']
                }
                [week['activities'].append(new_activity) for week in result if week['id'] == activity['week']]

        return result

    @endpoint(
        perm="can_access",
        description="Plaines et activités de la plaine prêtent pour multiselect wcs.",
        parameters={
            "child_id": {
                "description": "Identifiant d'un enfant",
                "example_value": "1",
            },
            "begining_date_search": {
                "description": "Début de la période dans laquelle chercher les occurences de l'activité",
                "example_value": "01/01/2020",
            },
            "ending_date_search": {
                "description": "Fin de la période dans laquelle chercher les occurences de l'activité",
                "example_value": "31/12/2020",
            },
        },
    )
    def get_plaines(self, request, **kwargs):
        list_plaines_pp = self.get_raw_plaines(request)["data"]
        plaines = []
        themes = []
        for dic_sem_plaine in list_plaines_pp:
            # k = semaine calendrier => 27, 28,...
            # v = {"2020-07-03_47": [], "2020-07-02_46": [], "2020-07-01_45": []}
            for k, v in dic_sem_plaine.items():
                week = k
                week_label = "S{}".format(k)
                theme_label = None
                # key = 2020-07-03_47 (date suivis du n occurence)
                # value = [{"4": "Kayak"}, {"5": "Poney"}] liste de sous-activite
                for key, value in v.items():
                    if key == "available":
                        pass
                    else:
                        if theme_label is None:
                            theme_label = (
                                self.get_week_theme(None, key.split("_")[1], week)
                                .get("data")[0]
                                .get("name")
                            )
                        jour = key
                        lst_activites = value
                        cpt_activite = 0
                        available = (
                            "available" if v.get("available") is True else "unaivalable"
                        )
                        if len(lst_activites) == 0:
                            select = {}
                            select["id"] = "_{}_{}_{}".format(
                                week_label, jour, available
                            )
                            select["text"] = "_{} : {}".format(
                                week_label, jour.split("_")[0].replace("-", "/")
                            )
                            plaines.append(select)
                        else:
                            for activite in lst_activites:
                                select = {}
                                for act_id, act_label in activite.items():
                                    select["id"] = "_{}_{}_{}_{}".format(
                                        week_label, jour, act_id, available
                                    )
                                    select["text"] = act_label
                                plaines.append(select)
                                cpt_activite = cpt_activite + 1
                themes.append({"week": week, "label": theme_label})
        # return {"data":sorted(plaines, key=lambda k:k["id"]),"themes":themes}
        return {"data": sorted(plaines, key=lambda k: k["id"]), "themes": themes}

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Plaines (rich) et activités de la plaine prêtent pour multiselect wcs.",
        parameters={
            "child_id": {
                "description": "Identifiant d'un enfant",
                "example_val" "ue": "0",
            },
            "begining_date_search": {
                "description": "Début de la période dans laquelle chercher les occurences de l'activité",
                "example_value": "01/01/2020",
            },
            "ending_date_search": {
                "description": "Fin de la période dans laquelle chercher les occurences de l'activité",
                "example_value": "31/12/2020",
            },
        },
    )
    def get_rich_plaines(self, request, **kwargs):
        list_plaines_pp = self.get_raw_plaines(request)["data"]
        plaines = []
        for dic_sem_plaine in list_plaines_pp:
            for k, v in dic_sem_plaine.items():
                week = "Semaine {}".format(k)
                for key, value in v.items():
                    jour = key
                    lst_activites = value
                    cpt_activite = 0
                    for activite in lst_activites:
                        select = {}
                        for act_id, act_label in activite.items():
                            select["id"] = "_{}_{}_{}".format(week, jour, act_id)
                            select["text"] = "{} : Actvitites ({})".format(
                                week, act_label
                            )
                        plaines.append(select)
                        cpt_activite = cpt_activite + 1
        return {"data": sorted(plaines, key=lambda k: k["id"])}

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        methods=["post",],
        description="validate form",
    )
    def validate_form(self, request):
        if request.body:
            data = json_loads(request.body)
        self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "validate_form",
            [data],
        )
        return True

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        methods=["post",],
        description="Envoi les demandes clôturées à AES pour un parent pour une période donnée",
    )
    def close_plaines_reservation(self, request):
        if request.body:
            data = json_loads(request.body)
        pay = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "close_plaine_reservation",
            [data],
        )
        return pay

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        methods=["post",],
        description="Libération des places en cas de non paiement dans un délais de n jours.",
    )
    def free_up_places(self, request):
        if request.body:
            data = json_loads(request.body)
        self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "free_up_places",
            [data],
        )
        return True

    @endpoint(
        serializer_type="json-api",
        methods=["post",],
        perm="can_access",
        description="Signal que le paiement a ete effectue",
    )
    def pay_prepaid(self, request, amount=None, parent_id=None, form_id=None):
        if request.body:
            params = json_loads(request.body)
        else:
            params = dict([(x, request.GET[x]) for x in request.GET.keys()])
        data = {
            "amount": float(str(params.get("amount")).replace(",", ".")),
            "parent_id": int(params.get("parent_id")),
            "form_id": params.get("form_id"),
        }
        response = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "pay_prepaid",
            [data],
        )
        return response

    # generate a serie of stub invoices
    invoices = {}
    for i in range(15):
        now = timezone.now()
        id_ = "%d%04d" % (now.year, i + 1)
        invoices[id_] = {
            "id": id_,
            "display_id": id_,
            "total_amount": Decimal(random.randint(100, 10000)) / 100,
            "has_pdf": bool(i % 3),
            "created": (
                now - datetime.timedelta(days=20) + datetime.timedelta(days=i)
            ).date(),
            "label": "Label %s" % id_,
            "pay_limit_date": (
                now + datetime.timedelta(days=2 + random.randint(0, 10))
            ).date(),
            "online_payment": bool(i % 2),
            "paid": False,
        }
        if i < 5:
            invoices[id_]["payment_date"] = invoices[id_][
                "created"
            ] + datetime.timedelta(days=1 + random.randint(0, 3))
            invoices[id_]["online_payment"] = False
            invoices[id_]["paid"] = True
        elif invoices[id_]["online_payment"] is False:
            invoices[id_]["no_online_payment_reason"] = random.choice(
                ["autobilling", "litigation"]
            )

        invoices[id_]["amount"] = invoices[id_]["total_amount"]

    def get_invoices(self, request, **kwargs):
        # request authentic API.
        # Pour que combo, via passerelle, puisse envoyer l'adresse e-mail à aes de la personne connectée (authentic).
        r = requests.get(
            "{}/api/users/{}".format(settings.AUTHENTIC_URL, request.GET.get("NameID")),
            auth=(settings.AES_LOGIN, settings.AES_PASSWORD),
        )
        connected_user_email = r.json().get("email")
        parent = {"email": connected_user_email}
        invoices_datas = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "get_invoices",
            [parent],
        )
        datas = invoices_datas.get("invoices")
        for data in datas:
            if data["total_amount"] is None:
                data["total_amount"] = Decimal("0")
            data["amount"] = data["total_amount"]
            data["created"] = dt.strptime(data["created"], "%Y-%m-%d %H:%M:%S").date()
            data["pay_limit_date"] = dt.strptime(
                data["pay_limit_date"], "%Y-%m-%d"
            ).date()
        return datas

    def get_invoice(self, request, invoice_id):
        invoices = self.get_invoices(request)
        return [invoice for invoice in invoices if invoice.get("id") == invoice_id][0]

    @endpoint(
        name="invoices",
        pattern="^history/$",
        description=_("Get list of paid invoices"),
        example_pattern="history/",
    )
    def invoices_history(self, request, NameID=None, **kwargs):
        datas = self.get_invoices(request)
        return {"data": [x for x in datas if x.get("payment_date")]}

    @endpoint(
        name="invoices",
        description=_("Get list of unpaid invoices"),
        parameters={
            "NameID": {
                "description": "auth NameID",
                "example_value": "b663530a0c0446a796782b9ea2d38c0c",
            }
        },
    )
    def invoices_list(self, request, NameID=None, **kwargs):
        datas = self.get_invoices(request)
        return {"data": [x for x in datas if not x.get("payment_date")]}

    @endpoint(
        name="invoice",
        pattern="^(?P<invoice_id>\w+)/?$",
        description=_("Get invoice details"),
        example_pattern="{invoice_id}/",
        parameters={
            "invoice_id": {
                "description": _("Invoice identifier"),
                "example_value": list(invoices)[0],
            }
        },
    )
    def invoice(self, request, invoice_id, NameID=None, **kwargs):
        return {"data": self.get_invoice(request, invoice_id)}

    @endpoint(
        name="invoice",
        pattern="^(?P<invoice_id>\w+)/pdf/?$",
        description=_("Get invoice as a PDF file"),
        example_pattern="{invoice_id}/pdf/",
        parameters={
            "invoice_id": {
                "description": _("Invoice identifier"),
                "example_value": list(invoices)[0],
            }
        },
    )
    def invoice_pdf(self, request, invoice_id, NameID=None, **kwargs):
        aes_invoice_id = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "extraschool.invoice",
            "search",
            [[("id", "=", invoice_id[3:])]],
        )
        pdf = self.get_aes_report().render_report(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "extraschool.invoice_report_layout",
            aes_invoice_id,
        )
        b64content = pdf.get("result")

        buffer = BytesIO.BytesIO()
        content = base64.b64decode(b64content)
        buffer.write(content)

        response = HttpResponse(buffer.getvalue(), content_type="application/pdf",)
        # inline to load pdf in browser / attachment to download pdf as a file.
        response["Content-Disposition"] = 'attachment; filename="{}.pdf"'.format(
            invoice_id
        )
        return response

    @endpoint(
        name="invoice",
        perm="can_access",
        methods=["post"],
        pattern="^(?P<invoice_id>\w+)/pay/?$",
        description=_("Pay invoice"),
        example_pattern="{invoice_id}/pay/",
        parameters={
            "invoice_id": {
                "description": _("Invoice identifier"),
                "example_value": list(invoices)[0],
            }
        },
    )
    def invoice_pay(self, request, invoice_id, NameID=None, **kwargs):
        response = json_loads(request.body)
        # ast.literal_eval(request.body)
        response["id"] = invoice_id
        aes_resp = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "make_payment",
            [response],
        )
        return {"data": None}
