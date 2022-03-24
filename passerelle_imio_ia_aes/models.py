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
import re
import requests
from django.db import models
from django.conf import settings
from django.http import Http404
from django.http import HttpResponse
from django.urls import path, reverse
from django.core.exceptions import MultipleObjectsReturned
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
        "example_value": "11",
    }
    CHILD_PARAM = {
        "description": "Identifiant Odoo interne de l'enfant",
        "example_value": "1",
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
                "example_value": "",
            },
            "partner_type": {"description": "Type de personne", "example_value": ""},
        },
        display_order=0,
        display_category="Parent",
    )
    def search_parent(
        self, request, national_number="", registration_number="", partner_type=""
    ):
        url = f"{self.server_url}/{self.aes_instance}/persons?national_number={national_number}&registration_number={registration_number}&partner_type={partner_type}"
        response = self.session.get(url)
        if response.json()["items_total"] > 1:
            raise MultipleObjectsReturned
        if response.json()["items_total"] == 0:
            parent_id = None
        else:
            parent_id = response.json()["items"][0]["id"]
        return {"parent_id": parent_id}

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
        url = f"{self.server_url}/{self.aes_instance}/parents/{parent_id}"
        response = self.session.get(url).json()
        return response

    @endpoint(
        name="levels",
        methods=["get"],
        perm="can_access",
        description="Lister les niveaux",
        long_description="Liste les niveaux scolaires.",
        display_category="Données génériques",
    )
    def list_levels(self, request):
        url = f"{self.server_url}/{self.aes_instance}/levels"
        response = self.session.get(url).json()
        return response

    @endpoint(
        name="places",
        methods=["get"],
        perm="can_access",
        description="Lister les lieux d'accueil",
        long_description="Liste les lieux d'accueil",
        display_category="Données génériques",
    )
    def list_places(self, request):
        url = f"{self.server_url}/{self.aes_instance}/places"
        response = self.session.get(url).json()
        return response

    def list_localities(self):
        url = f"{self.server_url}/{self.aes_instance}/localities"
        response = self.session.get(url)
        return response.json()["items"]

    def filtered_localities_by_zipcode(self, zipcode):
        localities = [
            locality
            for locality in self.list_localities()
            if locality["zip"] == zipcode
        ]
        return localities

    def cleanup_string(self, s):
        result, accent, without_accent = (
            "",
            ["é", "è", "ê", "à", "ù", "û", "ç", "ô", "î", "ï", "â"],
            ["e", "e", "e", "a", "u", "u", "c", "o", "i", "i", "a"],
        )
        result = re.sub(r"[^\w\s]", "", s).replace(" ", "").lower()
        for ac, wo in zip(accent, without_accent):
            result = result.replace(ac, wo)
        return result

    def compute_matching_score(self, str1, str2):
        cleaned_str1 = self.cleanup_string(str1)
        cleaned_str2 = self.cleanup_string(str2)
        matching_score = 0
        for element in set(cleaned_str1 + cleaned_str2):
            matching_score += max(
                cleaned_str1.count(element), cleaned_str2.count(element)
            ) - min(cleaned_str1.count(element), cleaned_str2.count(element))
        return matching_score

    def search_locality(self, zipcode, locality):
        aes_localities = self.filtered_localities_by_zipcode(zipcode)
        for aes_locality in aes_localities:
            aes_locality["matching_score"] = self.compute_matching_score(
                aes_locality["name"], locality
            )
        return sorted(aes_localities, key=lambda x: x["matching_score"])[0]

    @endpoint(
        name="localities",
        methods=["get"],
        perm="can_access",
        description="Recherche",
        long_description="Recherche, filtre et trie les localités",
        parameters={
            "zipcode": {
                "description": "code postal",
                "example_value": "5032",
            },
            "locality": {
                "description": "Localité",
                "example_value": "Gembloux",
            },
        },
        display_category="Localités",
    )
    def search_and_list_localities(self, request, zipcode, locality):
        aes_localities = self.filtered_localities_by_zipcode(zipcode)
        for aes_locality in aes_localities:
            aes_locality["matching_score"] = self.compute_matching_score(
                aes_locality["name"], locality
            )
        return sorted(aes_localities, key=lambda x: x["matching_score"])

    @endpoint(
        name="create-parent",
        methods=["post"],
        perm="can_access",
        description="Créer un parent",
        long_description="Crée un parent dans AES avec les informations contenues dans le cors de la requête",
        display_category="Parent",
    )
    def create_parent(self, request):
        url = f"{self.server_url}/{self.aes_instance}/parents"
        post_data = json_loads(request.body)
        parent = {
            "firstname": post_data["firstname"],
            "lastname": post_data["lastname"],
            "email": post_data["email"],
            "phone": post_data["phone"],
            "street": post_data["street"],
            "locality_id": self.search_locality(
                post_data["zipcode"], post_data["locality"]
            )["id"],
            "is_company": post_data["is_company"],
            "national_number": post_data["national_number"],
            "registration_number": post_data["registration_number"],
        }
        response = self.session.post(url, json=parent)
        return response.json()

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
        for child in response["items"]:
            result.append(
                {
                    "id": child["id"],
                    "national_number": child["national_number"],
                    "name": child["display_name"],
                    "birthdate": child["birthdate_date"],
                    "activities": child["activity_ids"],
                    "school_implantation": child["school_implantation_id"],
                    "level": child["level_id"],
                    "healthsheet": child["health_sheet_ids"],
                }
            )
        return {"items": result}

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
        parent_url = f"{self.server_url}/{self.aes_instance}/parents/{parent_id}"
        if self.session.get(parent_url).status_code == 200:
            forms = self.get_pp_forms()
            children_url = (
                f"{self.server_url}/{self.aes_instance}/parents/{parent_id}/kids"
            )
            children = self.session.get(children_url).json()["items"]
            result = {
                "is_parent": True,
                "children": [],
            }
            for child in children:
                result["children"].append(
                    {
                        "id": child["id"],
                        "national_number": child["national_number"],
                        "name": child["display_name"],
                        "age": child["birthdate_date"],
                        "activities": child["activity_ids"],
                        "school_implantation": False
                        if not child["school_implantation_id"]
                        else child["school_implantation_id"][1],
                        "level": child["level_id"],
                        "healthsheet": self.has_valid_healthsheet(child["id"]),
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

    @endpoint(
        name="parents",
        methods=["post"],
        perm="can_access",
        description="Créer un enfant",
        long_description="Crée un enfant dans iA.AES avec les informations contenues dans le corps de la requête.",
        parameters={"parent_id": PARENT_PARAM},
        example_pattern="{parent_id}/children/create",
        pattern="^(?P<parent_id>\w+)/children/create$",
        display_category="Enfant",
    )
    def create_child(self, request, parent_id):
        url = f"{self.server_url}/{self.aes_instance}/parents/{parent_id}/kids"
        post_data = json_loads(request.body)
        child = {
            "firstname": post_data["firstname"],
            "lastname": post_data["lastname"],
            "school_implantation_id": post_data["school_implantation_id"],
            "level_id": post_data["level_id"],
            "birthdate_date": post_data["birthdate"],
            "national_number": post_data["national_number"],
        }
        response = self.session.post(url, json=child)
        return response.json()


    # WIP : need a child with available menus to validate this
    @endpoint(
        name="menus",
        methods=["get"],
        perm="can_access",
        description="Lire le menu proposé à un enfant",
        long_description="Retourne le menu proposé à un enfant, en fonction du mois concerné.",
        parameters={"child_id": CHILD_PARAM, "month": {"description": "Mois concerné, si pour ce mois-ci, 1 pour le mois prochain, 2 pour dans deux mois", "example_value": 0}},
        display_category="Repas",
    )
    def list_available_meals(self, request, child_id, month):
        url = f"{self.server_url}/{self.aes_instance}/menus?kid_id={child_id}&month={month}"
        response = self.session.get(url)
        return response.json()


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
        long_description="Retourne, pour un enfant donné, ses inscriptions futures, dans le but de l'en désincrire.",
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
        if response.json()[0]["__last_update"] == response.json()[0]["create_date"]:
            return False
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
        display_category="Enfant",
    )
    def read_healthsheet(self, request, child_id):
        url = f"{self.server_url}/{self.aes_instance}/kids/{child_id}/healthsheet"
        return self.session.get(url).json()[0]

    @endpoint(
        name="healtsheet-fields",
        methods=["get"],
        perm="can_access",
        description="Consulter les champs d'une fiche santé",
        long_description="Liste les champs de la fiche santé et leurs valeurs possible.",
        # cache_duration=3600,
        display_category="Fiche santé",
    )
    def list_healthsheet_fields(self, request):
        url = f"{self.server_url}/{self.aes_instance}/models/healthsheet"
        response = self.session.get(url).json()
        result = dict()
        for k, v in response.items():
            if isinstance(v, dict):
                result[k] = [
                    {"id": choice[0], "text": choice[1]} for choice in v["selection"]
                ]
            elif isinstance(v, list):
                result[k] = [
                    {"id": choice["id"], "text": choice["name"]} for choice in v
                ]
        return result

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
        url = f"{self.server_url}/{self.aes_instance}/parents/{parent_id}/invoices"
        return self.session.get(url).json()["items"]
