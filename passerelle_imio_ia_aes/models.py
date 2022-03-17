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
        "description": "Identifiant Odoo interne du parent",
        "example_value": "00000000097",
    }
    CHILD_PARAM = {
        "description": "Identifiant Odoo interne de l'enfant",
        "example_value": "00000000097",
    }
    CATEGORY_PARAM = {
        "description": "Identifiants du type d'activité",
        "example_value": "holiday_plain",
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
        long_description="Une simple requête qui permet juste de valider si la connexion est bien établie entre Publik et Apims.",
        display_order=0,
        display_category="Test",
    )
    def verify_connection(self, request):
        url = self.server_url
        return self.session.get(url).json()

    @endpoint(
        name="parents",
        methods=["get"],
        perm="can_access",
        description="Rechercher un parent",
        long_description="Rechercher et lire un parent selon son numéro de registre national ou son matricule",
        parameters={
            "national_number": {
                "description": "Numéro national de l'usager",
                "example_value": "00000000097",
            },
            "registration_number": {
                "description": "Ce numéro correspond matricule de l'usager si celui-ci n'a pas de numéro de registre national. Il s'agit typiquement de son identifiant dans Onyx",
                "example_value": None,
            },
            "partner_type": {
                "description": "Type de personne",
                "example_value": None
            }
        },
        display_order=0,
        display_category="Parent",
    )
    def search_parent(self, request, national_number=None, registration_number=None, partner_type=None):
        url = f"{self.server_url}/{self.aes_instance}/persons?national_number={national_number}&registration_number={registration_number}&partner_type={partner_type}"
        response = self.session.get(url).json()
        return response

    @endpoint(
        name="parents",
        methods=["get"],
        perm="can_access",
        description="Lire un parent",
        long_description="Rechercher et lire un parent selon son numéro de registre national ou son matricule",
        parameters={"parent_id": PARENT_PARAM},
        example_pattern="{parent_id}/",
        pattern="^(?P<parent_id>\w+)/$",
        display_order=0,
        display_category="Parent",
    )
    def read_parent(self, request, parent_id):
        url = f"{self.server_url}/{self.aes_instance}/persons/{parent_id}"
        return self.session.get(url).json()

    # @endpoint(
    #     name="persons",
    #     methods=["post"],
    #     perm="can_access",
    #     description="Créer une personne",
    # )
    # def create_parent(self, data):
    #     url = f"{self.url}/fleurus/parents"
    #     response = self.session.post(url, json=data)
    #     return response.json()

    # @endpoint(
    #     name="parents",
    #     methods=["get"],
    #     perm="can_access",
    #     description="Obtenir les enfants d'un parent",
    #     parameters={"parent_id": PERSON_PARAM},
    #     example_pattern="{parent_id}/children/",
    #     pattern="^(?P<parent_id>\w+)/children/$",
    # )
    @endpoint(
        name="parents",
        methods=["get"],
        perm="can_access",
        description="Lister les enfants d'un parent",
        long_description="Retourne les enfants d'un parent et filtre leurs données pour n'afficher que l'essentiel.",
        parameters={"parent_id": PARENT_PARAM},
        example_pattern="{parent_id}/children/",
        pattern="^(?P<parent_id>\w+)/children/$",
        display_category="Parent",
    )
    def list_children(self, request, parent_id):
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
        description="Lister les formulaires de la catégorie Portail Parent",
        display_category="WCS",
    )
    def list_pp_forms(self, requests):
        return self.get_pp_forms()

    def get_pp_forms(self):
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
        name="parents",
        methods=["get"],
        perm="can_access",
        description="Page d'accueil",
        long_description="Agrège les données dont la page d'accueil du Portail Parent a besoin.",
        parameters={"parent_id": PARENT_PARAM},
        example_pattern="{parent_id}/homepage/",
        pattern="^(?P<parent_id>\w+)/homepage/$",
        display_category="Parent",
    )
    def homepage(self, request, parent_id):
        parent_url = f"{self.server_url}/{self.aes_instance}/persons/{parent_id}"
        if self.session.get(parent_url).status_code == 200:
            forms = self.get_pp_forms()
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

    # @endpoint(
    #     name="children",
    #     methods=["post"],
    #     perm="can_access",
    #     description="Ajouter un enfant dans iA.AES",
    # )
    # def create_child(self, data, parent_id):
    #     url = f"{self.url}/fleurus/parents/{parent_id}/kids"
    #     response = self.session.post(url, json=data)
    #     return response.json()

    # WIP : need a child with available plains to validate this
    @endpoint(
        name="children",
        methods=["get"],
        perm="can_access",
        description="Lister les plaines disponibles pour un enfant",
        long_description="Retourne les plaines auxquelles l'enfant passé peut être inscrit.",
        parameters={"child_id": CHILD_PARAM},
        example_pattern="{child_id}/activities/",
        pattern="^(?P<child_id>\w+)/activities/$",
        display_category="Enfant",
    )
    def list_available_plains(self, request, child_id):
        url = f"{self.server_url}/{self.aes_instance}/kids/{child_id}/activities?type=holiday_plain"
        return self.session.get(url).json()

    # Swagger itself return a 500 error
    # Waiting for ticket AES-948
    # WIP : need a child with registrations to validate this
    @endpoint(
        name="children",
        methods=["get"],
        perm="can_access",
        description="Liste les inscriptions d'un enfant",
        long_description="Retourne, pour un enfant donner, ses inscriptions futures, dans le but de l'en désincrire.",
        parameters={"child_id": CHILD_PARAM, "category": CATEGORY_PARAM},
        example_pattern="{child_id}/registrations",
        pattern="^(?P<child_id>\w+)/registrations$",
        display_category="Enfant",
    )
    def list_registrations(self, request, child_id, category):
        url = f"{self.server_url}/{self.aes_instance}/kids/{child_id}/registrations?category_type={category}"
        response = self.session.get(url)
        return {"status_code": response.status_code, "url": url}

    def has_valid_healthsheet(self, child_id):
        url = f"{self.server_url}/{self.aes_instance}/kids/{child_id}/healthsheet"
        response = self.session.get(url)
        if response.status_code >= 400:
            return {
                "is_valid": False,
                "status_code": response.status_code,
                "details": response.json(),
            }
        healthsheet_last_update = datetime.strptime(
            response.json()[0]["__last_update"][:10], "%Y-%m-%d"
        )
        is_healthsheet_valid = 183 >= (datetime.today() - healthsheet_last_update).days
        return {"is_valid": True}

    @endpoint(
        name="children",
        methods=["get"],
        perm="can_access",
        description="Lire la fiche santé d'un enfant",
        parameters={"child_id": CHILD_PARAM},
        example_pattern="{child_id}/healthsheet/",
        pattern="^(?P<child_id>\w+)/healthsheet/$",
        display_category="Enfant",
    )
    def read_healthsheet(self, request, child_id):
        url = f"{self.server_url}/{self.aes_instance}/kids/{child_id}/healthsheet"
        return self.session.get(url).json()

    @endpoint(
        name="healtsheets-fields",
        methods=["get"],
        perm="can_access",
        description="Consulter les champs d'une fiche santé",
        long_description="Liste les champs de la fiche santé et leurs valeurs possible.",
        cache_duration=3600,
        display_category="Fiche santé",
    )
    def list_healthsheet_fields(self, request):
        url = f"{self.server_url}/{self.aes_instance}/models/healthsheet"
        return self.session.get(url).json()

    # WIP : need a parent with invoices to validate this
    @endpoint(
        name="parents",
        methods=["get"],
        perm="can_access",
        description="Lister les factures d'un parent",
        parameters={
            "parent_id": PARENT_PARAM,
        },
        example_pattern="{parent_id}/invoices/",
        pattern="^(?P<parent_id>\w+)/invoices/$",
        display_category="Parent",
    )
    def list_invoices(self, request, parent_id):
        url = "{self.server_url}/{self.aes_instance}/parents/{parent_id}/invoices"
        return self.session.get(url).json()
