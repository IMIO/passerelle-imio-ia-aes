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
# serializer_type='json-api' : Permet de serializer la reponse directement dans un data + format automatique pour un raise exception.

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
import httplib
import io as BytesIO
import json
import logging
import random
import xmlrpclib
from decimal import Decimal
from xmlrpclib import ServerProxy

import requests

from datetime import datetime as dt
from django.db import models
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from passerelle import settings
from passerelle.base.models import BaseResource
from passerelle.utils.api import endpoint


def format_type(t):
    return {"id": unicode(t), "text": unicode(t)}


def format_file(f):
    return {"status": f.status, "id": f.nom, "timestamp": f.timestamp}


class FileError(Exception):
    pass


class FileNotFoundError(Exception):
    http_status = 404


# https://192.168.252.14/inscriptions/newsletter/14/jump/trigger/validate
# http://local-formulaires.example.net/backoffice/management/demo-cb-aes/1/
# http://local-formulaires.example.net/travaux/demo-cb-aes/1/jump/trigger/validate


class ProxiedTransport(xmlrpclib.Transport):
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
    def tst_connexion(self, request, **kwargs):
        test = None
        try:
            test = self.get_aes_server().execute_kw(
                self.database_name,
                self.get_aes_user_id(),
                self.password,
                "aes_api.aes_api",
                "hello_world",
                [],
            )
        except Exception:
            p = ProxiedTransport()
            p.set_proxy("10.9.200.215:9069")
            # server = xmlrpclib.ServerProxy('http://time.xmlrpc.com/RPC2', transport=p)
            server = ServerProxy(
                "{}/xmlrpc/2/object".format(self.server_url), transport=p
            )
            test = server.execute_kw(
                self.database_name,
                self.get_aes_user_id(),
                self.password,
                "aes_api.aes_api",
                "hello_world",
                [],
            )
            # print server.currentTime.getCurrentTime()
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
            occurences_load = json.loads(request.body)
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
            occurences_load = json.loads(request.body)
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
        description="Récupérer les enfants pour le parent connecté",
        parameters={
            "mail": {
                "description": "Adresse e-mail d'un parent AES/TS",
                "example_value": "demotsaes@imio.be",
            }
        },
    )
    def get_children(self, request, **kwargs):
        parent = {"nom": "aa", "prenom": "aaa", "email": request.GET["mail"]}
        try:
            children = self.get_aes_server().execute_kw(
                self.database_name,
                self.get_aes_user_id(),
                self.password,
                "aes_api.aes_api",
                "get_children",
                [parent],
            )
            # chidren["parent"] = request.GET["mail"]
            return children
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
        data = dict([(x, request.GET[x]) for x in request.GET.keys()])
        if request.body:
            parent = json.loads(request.body)
        registration_id = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "extraschool.parent",
            "create",
            [parent]
        )
        return registration_id

    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Vérifier qu'un parent existe bien dans AES",
        parameters={
            "email": {
                "description": "Adresse e-mail d'un parent AES/TS",
                "example_value": "demotsaes@imio.be",
            }
        },
    )
    def is_registered_parent(self, request, **kwargs):
        parent = {"email": request.GET["email"], "nrn": request.GET["nrn"]}
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
            occurences_load = json.loads(request.body)
        is_registration_child = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "add_registration_child",
            [occurences_load],
        )
        return is_registration_child

    # child_id, start_date, end_date):
    # {"data": [{"9": {"2020-02-24": ["Tir \u00e0 l'arc"],
    #                 "2020-02-25": ["Paintball", "Electricit\u00e9"],
    #                 "2020-02-26": ["Walibi", "Collage", "Octogone"],
    #
    @endpoint(
        serializer_type="json-api",
        perm="can_access",
        description="Recuperation des semaines de plaines et des activites de la plaine",
    )
    def get_plaines(self, request, **kwargs):
        occurences_load = None
        data = dict([(x, request.GET[x]) for x in request.GET.keys()])
        if request.body:
            occurences_load = json.loads(request.body)
        list_plaines_pp = self.get_aes_server().execute_kw(
            self.database_name,
            self.get_aes_user_id(),
            self.password,
            "aes_api.aes_api",
            "get_plaine",
            [occurences_load],
        )["data"]
        plaines = []
        for dic_sem_plaine in list_plaines_pp:
            for k, v in dic_sem_plaine.items():
                week = "S{}".format(k)
                for key, value in v.items():
                    jour = key
                    lst_activites = value
                    cpt_activite = 0
                    for activite in lst_activites:
                        select = {}
                        select["id"] = "_{}_{}_{}".format(week, jour, cpt_activite)
                        select["text"] = activite
                        plaines.append(select)
                        cpt_activite = cpt_activite + 1
        return {"data": sorted(plaines, key=lambda k: k["id"])}

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
        NameID = request.GET.get("NameID") or request.GET("NameID")
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
                "example_value": invoices.keys()[0],
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
                "example_value": invoices.keys()[0],
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
                "example_value": invoices.keys()[0],
            }
        },
    )
    def invoice_pay(self, request, invoice_id, NameID=None, **kwargs):
        response = json.loads(request.body)
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
