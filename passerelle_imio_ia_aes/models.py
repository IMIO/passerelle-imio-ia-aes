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


from builtins import str


import logging
import requests
from django.db import models
from django.conf import settings
from django.http import Http404
from django.http import HttpResponse
from django.urls import path, reverse
from datetime import datetime
from passerelle.base.models import BaseResource
from passerelle.base.signature import sign_url
from passerelle.compat import json_loads
from passerelle.utils.api import endpoint
from passerelle.utils.jsonresponse import APIError
from requests.exceptions import ConnectionError


logger = logging.getLogger(__name__)


class ApimsAesConnector(BaseResource):
    """
    Connector Apims AES
    """

    server_url = models.CharField(
        max_length=128,
        blank=False,
        verbose_name="URL du serveur",
        help_text="URL du serveur",
    )
    username = models.CharField(max_length=128, blank=True, verbose_name="Utilisateur")
    password = models.CharField(max_length=128, blank=True, verbose_name="Mot de passe")
    aes_instance = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Instance d'AES à contacter",
        help_text="Par exemple : fleurus",
    )

    category = "Connecteurs iMio"
    api_description = "Ce connecteur propose les méthodes d'échanges avec le produit iA.AES à travers Apims."

    PARENT_PARAM = {
        "description": "Matricule ou RN du parent",
        "example_value": "00000000097",
    }
    CHILD_PARAM = {
        "description": "Identifiant de l'enfant",
        "example_value": "00000000097",
    }

    class Meta:
        verbose_name = "Connecteur Apims AES"

    @property
    def session(self):
        session = requests.Session()
        session.auth = (self.username, self.password)
        session.headers.update({"Accept": "application/json"})
        return session

    @endpoint(
        name="verify-connection",
        perm="can_access",
        description="Valider la connexion entre APIMS et Publik",
    )
    def verify_connection(self, request):
        url = self.server_url
        return self.session.get(url).json()

    @endpoint(
        name="parents",
        methods=["get"],
        perm="can_access",
        description="Lire un parent",
        parameters={"parent_id": PARENT_PARAM},
        example_pattern="{parent_id}/",
        pattern="^(?P<parent_id>\w+)/$",
    )
    def read_parent(self, request, parent_id):
        url = f"{self.server_url}/{self.aes_instance}/persons?person_id={parent_id}"
        return self.session.get(url).json()

    # def create_parent(self, data):
    #     url = f"{self.url}/fleurus/parents"
    #     response = self.session.post(url, json=data)
    #     return response.json()

    # @endpoint(
    #     name="parents",
    #     methods=["get"],
    #     perm="can_access",
    #     description="Obtenir les enfants d'un parent",
    #     parameters={"parent_id": PARENT_PARAM},
    #     example_pattern="{parent_id}/children/",
    #     pattern="^(?P<parent_id>\w+)/children/$",
    # )
    @endpoint(
        name="children",
        methods=["get"],
        perm="can_access",
        description="Obtenir les enfants d'un parent",
        parameters={"parent_id": PARENT_PARAM},
    )
    def children(self, request, parent_id):
        url = f"{self.server_url}/{self.aes_instance}/parents/{parent_id}/kids"
        response = self.session.get(url).json()
        result = []
        for child in response:
            result.append(
                {
                    "id": child["national_number"],
                    "name": child["display_name"],
                    "birthdate": child["birthdate_date"],
                    "activities": child["activity_ids"],
                    "school_implantation": child["school_implantation_id"],
                    "level": child["level_id"],
                    "healthsheet": child["health_sheet_ids"],
                }
            )
        return result

    @endpoint(
        name="get-pp-forms",
        methods=["get"],
        perm="can_access",
        description="Get PP Forms",
    )
    def get_pp_forms(self, requests):
        return self.get_forms()

    def get_forms(self):
        if not getattr(settings, "KNOWN_SERVICES", {}).get("wcs"):
            return
        eservices = list(settings.KNOWN_SERVICES["wcs"].values())[0]
        signed_forms_url = sign_url(
            url=f"{eservices['url']}api/categories/portail-parent/formdefs/?orig={eservices.get('orig')}",
            key=eservices.get("secret"),
        )
        signed_forms_url_response = self.requests.get(signed_forms_url)
        return signed_forms_url_response.json()["data"]

    @endpoint(
        name="homepage",
        methods=["get"],
        perm="can_access",
        description="Construire la page d'accueil d'un parent",
        parameters={"parent_id": PARENT_PARAM},
    )
    def homepage(self, request, parent_id):
        parent_url = (
            f"{self.server_url}/{self.aes_instance}/persons?person_id={parent_id}"
        )
        if self.session.get(parent_url).status_code == 200:
            forms = self.get_forms()
            children_url = (
                f"{self.server_url}/{self.aes_instance}/parents/{parent_id}/kids"
            )
            children = self.session.get(children_url).json()
            result = {
                "is_parent": True,
                "children": [],
            }
            for child in children:
                result["children"].append(
                    {
                        "id": child["national_number"],
                        "name": child["display_name"],
                        "age": child["birthdate_date"],
                        "activities": child["activity_ids"],
                        "school_implantation": False
                        if not child["school_implantation_id"]
                        else child["school_implantation_id"][1],
                        "level": child["level_id"],
                        "healthsheet": self.has_valid_healthsheet(
                            child["national_number"]
                        )
                        if len(child["health_sheet_ids"]) > 0
                        else False,
                        "forms": [
                            {
                                "title": form["title"],
                                "slug": form["slug"],
                                "status": "available",
                                "image": "H",
                            }
                            for form in forms
                        ],
                    }
                )
        else:
            result = {"is_parent": False}
        return result

    def read_child(self, child_id):
        url = f"{self.url}/{self.aes_instance}/kids/{child_id}"
        return self.session.get(url).json()

    # def create_child(self, data, parent_id):
    #     url = f"{self.url}/fleurus/parents/{parent_id}/kids"
    #     response = self.session.post(url, json=data)
    #     return response.json()

    @endpoint(
        name="children",
        methods=["get"],
        perm="can_access",
        description="Obtenir la liste des activités disponibles pour un enfant",
        parameters={"child_id": CHILD_PARAM},
        example_pattern="{child_id}/activities/",
        pattern="^(?P<child_id>\w+)/activities/$",
    )
    def list_available_plains(self, request, child_id):
        url = f"{self.server_url}/{self.aes_instance}/activities/{child_id}?type=holiday_plain"
        return self.session.get(url).json()

    # Swagger itself return a 500 error
    # Waiting for ticket AES-948
    @endpoint(
        name="children",
        methods=["get"],
        perm="can_access",
        description="Obtenir la liste des inscriptions de l'enfant",
        parameters={"child_id": CHILD_PARAM},
        example_pattern="{child_id}/registrations/",
        pattern="^(?P<child_id>\w+)/registrations/$",
    )
    def list_registrations(self, request, child_id):
        url = f"{self.server_url}/{self.aes_instance}/registrations/{child_id}?category_type=holiday_plain"
        return self.session.get(url).json()

    def has_valid_healthsheet(self, child_id):
        url = f"{self.server_url}/{self.aes_instance}/healthsheets/{child_id}"
        response = self.session.get(url)
        healthsheet_last_update = datetime.strptime(
            response.json()[0]["__last_update"][:10], "%Y-%m-%d"
        )
        is_healthsheet_valid = 183 >= (datetime.today() - healthsheet_last_update).days
        return is_healthsheet_valid

    @endpoint(
        name="children",
        methods=["get"],
        perm="can_access",
        description="Lire la fiche santé d'un enfant",
        parameters={"child_id": CHILD_PARAM},
        example_pattern="{child_id}/healthsheet/",
        pattern="^(?P<child_id>\w+)/healthsheet/$",
    )
    def read_healthsheet(self, request, child_id):
        url = f"{self.server_url}/{self.aes_instance}/healthsheets/{child_id}"
        return self.session.get(url).json()

    @endpoint(
        name="healtsheets-fields",
        methods=["get"],
        perm="can_access",
        description="Consulter les champs d'une fiche santé",
        cache_duration=3600,
    )
    def list_healthsheet_fields(self, request):
        url = f"{self.server_url}/{self.aes_instance}/models/healthsheet"
        return self.session.get(url).json()
