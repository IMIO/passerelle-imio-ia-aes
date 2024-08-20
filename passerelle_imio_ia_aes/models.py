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
from email import header

import json
import logging
import re
import requests
from calendar import Calendar, monthrange
from django.db import models
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.urls import path, reverse
from django.core.exceptions import MultipleObjectsReturned
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from passerelle.base.models import BaseResource
from passerelle.base.signature import sign_url
from passerelle.utils.api import endpoint
from passerelle.utils.jsonresponse import APIError
from requests.exceptions import ConnectionError
from workalendar.europe import Belgium


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
        "example_value": "22",
    }
    PERSON_PARAM = {
        "description": "Identifiant Odoo interne de la personne",
        "example_value": "1",
    }
    CATEGORY_PARAM = {
        "description": "Identifiants du type d'activité",
        "example_value": "holiday_plain",
    }
    FORMS_ICONS = {
        "pp-plaines-de-vacances": "static/imio/images/portail_parent/black-camp.svg",
        "pp-fiche-sante": "static/imio/images/portail_parent/black-sante.svg",
        "pp-repas-scolaires": "static/imio/images/portail_parent/black-repas.svg",
        "pp-desinscription-repas": "static/imio/images/portail_parent/black-no-repas.svg",
    }

    class Meta:
        verbose_name = "Connecteur Apims AES"

    @property
    def session(self):
        session = requests.Session()
        session.auth = (self.username, self.password)
        session.headers.update({"Accept": "application/json"})
        return session

    ############
    ### Test ###
    ############

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

    ##########################
    ### Données génériques ###
    ##########################

    @endpoint(
        name="countries",
        methods=["get"],
        perm="can_access",
        description="Lister les pays",
        long_description="Liste les pays de iA.AES",
        display_category="Données génériques",
        cache_duration=3600,
    )
    # list_states instead of list_countries as list_countries didn't work, don't know why.
    def list_states(self, request):
        url = f"{self.server_url}/{self.aes_instance}/countries"
        response = self.session.get(url)
        return response.json()

    @endpoint(
        name="levels",
        methods=["get"],
        perm="can_access",
        description="Lister les niveaux",
        long_description="Liste les niveaux scolaires.",
        display_category="Données génériques",
        cache_duration=600
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
        long_description="Liste les lieux d'accueil.",
        display_category="Données génériques",
        cache_duration=600,
    )
    def list_places(self, request):
        url = f"{self.server_url}/{self.aes_instance}/places"
        response = self.session.get(url).json()
        return response

    @endpoint(
        name="school-implantations",
        methods=["get"],
        perm="can_access",
        description="Lister les implantations scolaires",
        long_description="Liste les implantations scolaires.",
        display_category="Données génériques",
        cache_duration=600
    )
    def list_school_implantations(self, request):
        url = f"{self.server_url}/{self.aes_instance}/school-implantations"
        response = self.session.get(url).json()
        return response

    ##############
    ### Utiles ###
    ##############

    def get_localities(self):
        url = f"{self.server_url}/{self.aes_instance}/localities"
        response = self.session.get(url)
        items = [
            dict(
                id=item["id"],
                name=item["name"],
                zip=item["zip"],
                text=f"{item['zip']} - {item['name']}",
            )
            for item in response.json()["items"]
        ]
        result = dict(items=items, items_total=response.json()["items_total"])
        return result

    def filter_localities_by_zipcode(self, zipcode):
        localities = [
            locality
            for locality in self.get_localities()["items"]
            if locality["zip"][:3] == zipcode[:3]
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
        aes_localities = self.filter_localities_by_zipcode(str(zipcode))
        for aes_locality in aes_localities:
            aes_locality["matching_score"] = self.compute_matching_score(
                aes_locality["name"], locality
            )
        sorted_localities = sorted(aes_localities, key=lambda x: x["matching_score"])
        filtered_localities = [
            locality for locality in sorted_localities if locality["matching_score"] < 5
        ]
        if len(filtered_localities) == 0:
            raise ValueError(
                f"L'association du code postal {zipcode} et de la localité {locality.capitalize()} n'est pas connu."
            )
        return filtered_localities

    def list_countries(self):
        url = f"{self.server_url}/{self.aes_instance}/countries"
        response = self.session.get(url)
        return response.json()["items"]

    def search_country(self, country):
        aes_countries = self.list_countries()
        for aes_country in aes_countries:
            aes_country["matching_score"] = self.compute_matching_score(
                aes_country["value"], country
            )
        return sorted(aes_countries, key=lambda x: x["matching_score"])[0]

    @endpoint(
        name="localities",
        methods=["get"],
        perm="can_access",
        description="Rechercher une localité",
        long_description="Recherche, filtre et trie les localités",
        parameters={
            "zipcode": {
                "description": "code postal",
                "example_value": "5030",
            },
            "locality": {
                "description": "Localité",
                "example_value": "Gbloux",
            },
        },
        example_pattern="search/",
        pattern="^search/$",
        display_category="Localités",
    )
    def search_and_list_localities(self, request, zipcode, locality):
        return self.search_locality(zipcode, locality)

    @endpoint(
        name="localities",
        methods=["get"],
        perm="can_access",
        description="Lister les localités",
        long_description="Liste les localités et leurs codes postaux.",
        display_category="Localités",
        cache_duration=600,
    )
    def list_localities(self, request):
        return self.get_localities()

    ##############
    ### Person ###
    ##############

    @endpoint(
        name="persons",
        methods=["patch"],
        perm="can_access",
        description="Mettre à jour un enfant ou un parent",
        long_description="Mets à jour un enfant ou un parent, en fonction de la démarche d'origine",
        parameters={
            "id": PERSON_PARAM,
            "partner_type": {
                "description": "'parent' or 'child'",
                "example_value": "child",
            }
        },
        example_pattern="{id}",
        pattern="^(?P<id>\w+)$",
        display_category="Personne",
    )
    def update_person(self, request, id, partner_type):
        data = json.loads(request.body)
        form_register_child_schema = self.get_data_from_wcs("api/formdefs/pp-enregistrer-un-enfant/schema")
        patch_data = {
            "is_invoicing_differs_by_home": True if form_register_child_schema["options"]["child_type_facturation"] == "oui" else False,
            "is_invoicing_differs_by_school": True if form_register_child_schema["options"]["prefered_school_pricing"] == "oui" else False,
            "municipality_zipcodes": data["municipality_zipcodes"]
        }
        if partner_type == "child":
            patch_data.update({
                "firstname": data["child_firstname"],
                "lastname": data["child_lastname"],
                "birthdate_date": "-".join(reversed(data["child_birthdate"].split("/"))),
                "national_number": data["child_national_number"],
                "school_implantation_id": int(data["child_school_implantation"]),
                "other_ref": data.get("child_other_reference") or ""
            })
        elif partner_type == "parent":
            patch_data.update({
                "country_id": int(data["parent_country_id"]),
                "email": data["parent_email"],
                "locality_box": data["parent_num_box"],
                "street_number": data["parent_num_house"],
                "phone": data["parent_phone"],
                "street": data["parent_street"],
                "professional_phone": data["parent_professional_phone"],
                "mobile": data["parent_mobile_phone"]
            })
            if data["parent_country"].lower() == "belgique":
                patch_data.update({"locality_id": data["parent_locality_id"]})
            else:
                patch_data.update({"zip": data["parent_zipcode"], "city": data["parent_city"]})
        else:
            return HttpResponseBadRequest(f"{partner_type} is not a valid partner.")
        url = f"{self.server_url}/{self.aes_instance}/persons/{id}"
        response = self.session.patch(url, json=patch_data)
        response.raise_for_status()
        return True

    ##############
    ### Parent ###
    ##############

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
        display_category="Parent",
    )
    def search_parent(
        self, request, national_number="", registration_number="", partner_type=""
    ):
        url = f"{self.server_url}/{self.aes_instance}/persons?national_number={national_number}&registration_number={registration_number}&partner_type={partner_type}"
        response = self.session.get(url)
        response.raise_for_status()
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
        long_description="Lire un parent selon son identifiant dans iA.AES",
        parameters={"parent_id": PARENT_PARAM},
        example_pattern="{parent_id}/",
        pattern="^(?P<parent_id>\w+)/$",
        display_category="Parent",
        cache_duration=30
    )
    def read_parent(self, request, parent_id):
        url = f"{self.server_url}/{self.aes_instance}/parents/{parent_id}/"
        response = self.session.get(url).json()
        return response

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
        post_data = json.loads(request.body)
        parent = {
            "firstname": post_data["firstname"],
            "lastname": post_data["lastname"],
            "email": post_data["email"],
            "phone": post_data["phone"],
            "street": post_data["street"],
            "is_company": post_data["is_company"],
            "street_number": post_data["street_number"],
            "country_id": self.search_country(post_data["country"])["id"],
        }
        if post_data["national_number"]:
            parent["national_number"] = post_data["national_number"]
        if post_data["registration_number"]:
            parent["registration_number"] = post_data["registration_number"]
        if post_data["country"].lower() == "belgique":
            parent["locality_id"] = self.search_locality(
                post_data["zipcode"], post_data["locality"]
            )[0]["id"]
        else:
            parent["zip"] = post_data["zipcode"]
            parent["city"] = post_data["locality"]
        response = self.session.post(url, json=parent)
        response.raise_for_status()
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
        cache_duration=15
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
                    "lastname": child["lastname"],
                    "firstname": child["firstname"],
                    "age": child["age"],
                    "birthdate_date": child["birthdate_date"],
                    "activities": child.get("activity_ids"),
                    "school_implantation": child["school_implantation_id"],
                    "level": child["level_id"],
                    "healthsheet": child["health_sheet_ids"],
                    "invoiceable_parents": child["parent_ids"],
                    "responsibility_id": child["responsibility_id"]
                }
            )
        return {"items": result}

    @endpoint(
        name="get-forms",
        methods=["get"],
        perm="can_access",
        description="Lister les formulaires de la catégorie Portail Parent",
        display_category="WCS",
        cache_duration=30
    )
    def list_forms(self, requests):
        path = "api/categories/portail-parent/formdefs/"
        return self.get_data_from_wcs(path)["data"]

    def get_data_from_wcs(self, path):
        if not getattr(settings, "KNOWN_SERVICES", {}).get("wcs"):
            return
        eservices = list(settings.KNOWN_SERVICES["wcs"].values())[0]
        signed_forms_url = sign_url(
            url=f"{eservices['url']}{path}?orig={eservices.get('orig')}",
            key=eservices.get("secret"),
        )
        signed_forms_url_response = self.requests.get(signed_forms_url)
        signed_forms_url_response.raise_for_status()
        return signed_forms_url_response.json()

    def get_school_implantations_with_meals(self):
        """Return the list of school implantations offering meals as a list of int
        Return
        ------
            List of str
        """
        path = "api/formdefs/pp-repas-scolaires/schema"
        return self.get_data_from_wcs(path)["options"]["implantations_scolaires"]

    def set_form_status(self, form_slug, has_valid_healthsheet):
        if form_slug == "pp-plaines-de-vacances":
            result = None if has_valid_healthsheet else "locked"
        elif form_slug == "pp-fiche-sante":
            result = "valid" if has_valid_healthsheet else "invalid"
        elif form_slug == "pp-repas-scolaires":
            result = None
        elif form_slug == "pp-desinscription-repas":
            result = None
        return result

    @endpoint(
        name="parents",
        methods=["get"],
        perm="can_access",
        description="Communication structurée pour les plaines",
        long_description="Retourne la communication structurée d'un parent pour la catégorie d'activité plaines. "
        "C'est l'API qui fait le filtre. Retourne une erreur si plusieurs sont trouvées.",
        parameters={"parent_id": PARENT_PARAM},
        example_pattern="{parent_id}/plain-structured-communication/",
        pattern="^(?P<parent_id>\w+)/plain-structured-communication/$",
        display_category="Parent",
    )
    def get_plain_structured_communication(self, request, parent_id):
        url = f"{self.server_url}/{self.aes_instance}/parents/{parent_id}/structured-communications"
        response = self.session.get(url)
        response.raise_for_status()
        if len(response.json()) > 1:
            raise MultipleObjectsReturned
        return response.json()[0]

    def has_plain_registrations(self, user_uuid):
        if not getattr(settings, "KNOWN_SERVICES", {}).get("wcs"):
            return
        eservices = list(settings.KNOWN_SERVICES["wcs"].values())[0]
        signed_forms_url = sign_url(
            url=f"{eservices['url']}api/users/{user_uuid}/forms?orig={eservices.get('orig')}",
            key=eservices.get("secret"),
        )
        signed_forms_url_response = self.requests.get(signed_forms_url)
        signed_forms_url_response.raise_for_status()
        for demand in signed_forms_url_response.json()["data"]:
            if (
                demand["form_slug"] == "pp-fiche-inscription-plaine"
                and demand["form_status"] == "En attente de validation"
            ):
                return True
        return False

    def update_parent_id(self, new_parent_aes_id, parent_uuid):
        """Update user's aes_id

        Keyword arguments:
        new_parent_aes_id -- new parent's ID in iA.AES after a merge.
        parent_uuid -- user's uuid in authentic
        """
        if not getattr(settings, "KNOWN_SERVICES", {}).get("authentic"):
            return
        authentic = list(settings.KNOWN_SERVICES["authentic"].values())[0]
        url_with_signature = sign_url(
            url=f"{authentic['url']}api/users/{parent_uuid}/?orig={authentic.get('orig')}",
            key=authentic.get("secret"),
        )
        authentic_response = self.requests.patch(
            url_with_signature, json={"aes_id": new_parent_aes_id}
        )
        authentic_response.raise_for_status()
        return authentic_response.json()

    @endpoint(
        name="parents",
        methods=["get"],
        perm="can_access",
        description="Page d'accueil",
        long_description="Agrège les données dont la page d'accueil du Portail Parent a besoin.",
        parameters={
            "parent_id": PARENT_PARAM,
            "parent_uuid": {
                "description": "UUID de l'utilisateur dans iA.Téléservices, utilisé pour vérifier s'il a des insriptions aux plaines en attente de validation",
                "example_value": "38a1128f48f14880b1cb9e24ebd3e033",
            },
        },
        example_pattern="{parent_id}/homepage",
        pattern="^(?P<parent_id>\w+)/homepage$",
        display_category="Parent",
    )
    def homepage(self, request, parent_id, parent_uuid):
        """Check and update user's aes_id and build parent portal data structure

        Parameters:
            new_parent_aes_id: new parent's ID in iA.AES after a merge.
            parent_uuid: user's uuid in authentic

        Returns:
            json
        """
        if not parent_id.isdigit():
            return None
        url = f"{self.server_url}/{self.aes_instance}/parents/{parent_id}/homepage"
        response = self.session.get(url)
        response.raise_for_status()
        consolidated_parent_id = response.json().get("parent_id")
        if consolidated_parent_id != int(parent_id):
            self.update_parent_id(
                consolidated_parent_id, parent_uuid
            )  # TODO should be done asynchronously
        forms = self.get_data_from_wcs("api/categories/portail-parent/formdefs/")[
            "data"
        ]
        form_slugs = [form["slug"] for form in forms]
        if "pp-repas-scolaires" in form_slugs:
            school_implantations_with_meals = self.get_school_implantations_with_meals()
        else:
            school_implantations_with_meals = []
        result = dict(
            parent_id=consolidated_parent_id,
            has_plain_registrations=self.has_plain_registrations(parent_uuid),
            children=list(),
            is_update_child_available="pp-modifier-les-donnees-d-un-enfant" in form_slugs,
            is_update_parent_available="pp-modifier-mes-donnees-parent" in form_slugs,
            is_become_invoiceable_available="pp-me-designer-facturable" in form_slugs
        )
        for child in response.json().get("children"):
            child_forms = list()
            if child["invoiceable_parent_id"]:
                child_forms = [
                    {
                        "title": form["title"],
                        "slug": form["slug"],
                        "status": self.set_form_status(
                            form["slug"], child["has_valid_healthsheet"]
                        ),
                        "image": self.FORMS_ICONS[form["slug"]],
                    }
                    for form in forms
                    if form["slug"] in self.FORMS_ICONS
                    and (
                        "repas" not in form["slug"]
                        or self.does_school_have_meals(
                            child["school_implantation"], school_implantations_with_meals
                        )
                    )
                ]
            ts_child = dict(
                id=child["id"],
                national_number=child["national_number"],
                name=child["name"],
                age=child["age"],
                school_implantation=False
                if not child["school_implantation"]
                else child["school_implantation"],
                level=child["level"],
                healthsheet=child["has_valid_healthsheet"],
                invoiceable_parent_id=child["invoiceable_parent_id"],
                forms=child_forms,
            )
            result["children"].append(ts_child)
        return result

    ##############
    ### Enfant ###
    ##############

    def read_child(self, child_id):
        url = f"{self.url}/{self.aes_instance}/kids/{child_id}"
        return self.session.get(url).json()

    def list_price_categories(self):
        url = f"{self.server_url}/{self.aes_instance}/price_categories"
        response = self.session.get(url)
        response.raise_for_status()
        price_categories = dict()
        for price_category in response.json()["items"]:
            price_categories[price_category["name"]] = price_category["id"]
        return price_categories

    def set_price_category(
        self, is_invoicing_differs_by_home, is_invoicing_differs_by_school, is_parent_lives_in_municipality, is_child_scholarised_in_municipality
    ):
        """
        Défini la catégorie tarifaire de l'enfant en fonction de son implantation scolaire et du domicile de son parent
        @param is_invoicing_differs_by_home: bool
        @param is_invoicing_differs_by_school: bool
        @param is_parent_lives_in_municipality : bool
        @param is_child_scholarised_in_municipality: bool
        @returns price_category: int
        """
        price_categories = self.list_price_categories()
        if not is_invoicing_differs_by_home and not is_invoicing_differs_by_school:
            price_category = price_categories["Aucun"]
        elif is_invoicing_differs_by_home and is_parent_lives_in_municipality or is_invoicing_differs_by_school and is_child_scholarised_in_municipality:
            price_category = price_categories["Commune"]
        else:
            price_category = price_categories["Hors Commune"]
        return price_category

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
        post_data = json.loads(request.body)
        price_category_id = self.set_price_category(
            is_invoicing_differs_by_home=post_data["invoicing_differs_by_home"] in ("oui", "non_renseigne"), # non-renseigne est possible dans ce cas pour des raisons de rétro-compatibilité
            is_invoicing_differs_by_school=post_data["invoicing_differs_by_school"] == "oui", # Ici, non-renseigne n'est pas possible car pas de rétro-compatibilité à gérer
            is_parent_lives_in_municipality=post_data["parent_zipcode"] in post_data["municipality_zipcodes"],
            is_child_scholarised_in_municipality=not (len(post_data["school_implantation"]) <= 6 and "autre" in post_data["school_implantation"].lower()), # La longueur pour gérer les cas comme l'école communale de Bautre et le vrai test.
        )
        child = {
            "firstname": post_data["firstname"],
            "lastname": post_data["lastname"],
            "school_implantation_id": int(post_data["school_implantation_id"]),
            "level_id": int(post_data["level_id"]),
            "birthdate_date": post_data["birthdate"],
            "price_category_id": price_category_id,
        }
        if post_data["national_number"]:
            child["national_number"] = post_data["national_number"]
        response = self.session.post(url, json=child)
        response.raise_for_status()
        return response.json()

    @endpoint(
        name="children",
        methods=["get"],
        perm="can_access",
        description="Rechercher un enfant",
        long_description="Recherche et compte les enfants qui correspondent aux critères. Retourne le nombre d'enfants trouvés",
        parameters={
            "national_number": {
                "description": "Numéro national de l'enfant.",
                "example_value": "00000000097",
            },
            "lastname": {
                "description": "Nom de l'enfant.",
                "example_value": "DU JARRE D'IN",
            },
            "firstname": {
                "description": "Prénom de l'enfant",
                "example_value": "Charlotte",
            },
            "birthdate": {
                "description": "Date de naissance de l'enfant",
                "example_value": "2018-03-31",
            },
        },
        example_pattern="search",
        pattern="^search",
        display_category="Enfant",
    )
    def search_child(
        self,
        request,
        national_number=None,
        firstname=None,
        lastname=None,
        birthdate=None,
    ):
        if national_number:
            url_parameters = f"national_number={national_number}"
        elif lastname and firstname and birthdate:
            url_parameters = (
                f"lastname={lastname}&firstname={firstname}&birthdate={birthdate}"
            )
        else:
            raise TypeError(
                "You have to give either the national_number, or the lastname, firstname and birthdate."
            )
        url = f"{self.server_url}/{self.aes_instance}/persons?{url_parameters}"
        response = self.session.get(url)
        response.raise_for_status()
        if response.json()["items_total"] == 1:
            child = response.json()["items"][0]
        elif response.json()["items_total"] == 0:
            child = None
        else:
            raise MultipleObjectsReturned(
                "More than one child were found. A manual action is needed."
            )
        return {"child": child}

    @endpoint(
        name="children",
        methods=["patch"],
        perm="can_access",
        description="Ajouter un parent",
        long_description="Ajoute un parent à un enfant",
        parameters={"child_id": CHILD_PARAM},
        example_pattern="{child_id}/add-parent",
        pattern="^(?P<child_id>\w+)/add-parent$",
        display_category="Enfant",
    )
    def add_parent_to_child(self, request, child_id):
        url = f"{self.server_url}/{self.aes_instance}/kids/{child_id}"
        parent = json.loads(request.body)
        response = self.session.patch(url, json=parent)
        response.raise_for_status()
        return True

    @endpoint(
        name="responsibilities",
        methods=["patch"],
        perm="can_access",
        description="Ajoute facturable ou attestable",
        long_description="Renseigne une responsabilité comme facturable, ce qui permet au parent d'entamer des démarches, et éventuellement attestable.",
        parameters={"responsibility_id": {
                "description": "Identifiant du lien entre le parent et l'enfant",
                "example_value": "37",
            },
        },
        example_pattern="{responsibility_id}",
        pattern="^(?P<responsibility_id>\w+)$",
        display_category="Responsabilités",
    )
    def update_responsibilities(self, request, responsibility_id):
        url = f"{self.server_url}/{self.aes_instance}/responsibilities/{responsibility_id}"
        data = json.loads(request.body)
        response = self.session.patch(url, json=data)
        response.raise_for_status()
        return HttpResponse(status=204)

    ##############
    ### PLAINS ###
    ##############

    @endpoint(
        name="plains",
        methods=["get"],
        perm="can_access",
        description="Lister les plaines disponibles pour un enfant",
        long_description="Retourne les plaines auxquelles l'enfant passé peut être inscrit.",
        parameters={"child_id": CHILD_PARAM},
        example_pattern="raw",
        pattern="^raw$",
        display_category="Plaines",
    )
    def list_available_plains_raw(self, request, child_id):
        url = f"{self.server_url}/{self.aes_instance}/plains?kid_id={child_id}"
        response = self.session.get(url)
        return response.json()

    @endpoint(
        name="plains",
        methods=["get"],
        perm="can_access",
        description="Lister les plaines disponibles pour un enfant",
        long_description="Retourne les plaines auxquelles l'enfant passé peut être inscrit.",
        parameters={"child_id": CHILD_PARAM},
        display_category="Plaines",
        cache_duration=15,
    )
    def list_available_plains(self, request, child_id):
        url = f"{self.server_url}/{self.aes_instance}/plains?kid_id={child_id}"
        response = self.session.get(url)
        plains = [plain for plain in response.json() if plain["nb_remaining_place"] > 0]
        weeks, available_plains = set(), []
        for activity in plains:
            new_activity = {
                "id": "{}_{}_{}".format(
                    activity["year"], activity["week"], activity["id"]
                ),
                "text": activity.get("theme")
                if activity.get("theme") and activity.get("theme") != "False"
                else activity["name"],
                "week": activity["week"],
                "year": activity["year"],
                "start_date": activity["start_date"],
                "end_date": activity["end_date"],
                "age_group_manager_id": activity["age_group_manager_id"],
                "remaining_places": activity["nb_remaining_place"],
            }
            if activity["week"] not in weeks:
                available_plains.append(
                    {
                        "id": activity["week"],
                        "text": "Semaine {}".format(activity["week"]),
                        "activities": [new_activity],
                        "week": activity["week"],
                        "monday": date.fromisocalendar(
                            activity["year"], activity["week"], 1
                        ),
                        "year": activity["year"],
                    }
                )
                weeks.add(activity["week"])
            else:
                [
                    week["activities"].append(new_activity)
                    for week in available_plains
                    if week["id"] == activity["week"]
                ]
        return sorted(available_plains, key=lambda x: x["monday"])

    @endpoint(
        name="registrations",
        methods=["post"],
        perm="can_access",
        description="Inscrire un enfant aux plaines",
        long_description="Inscrit un enfant aux plaines de vacances",
        display_category="Plaines",
        example_pattern="create",
        pattern="^create$",
    )
    def create_plain_registrations(self, request):
        url = f"{self.server_url}/{self.aes_instance}/plains/registration"
        post_data = json.loads(request.body)
        plains = []
        for plain in post_data["plains"]:
            activity_id = plain["id"]
            start_date = datetime.strptime(
                f"1-{plain['week']}-{plain['year']}", "%w-%W-%Y"
            )
            end_date = start_date + timedelta(days=6)
            plains.append(
                {
                    "activity_id": int(activity_id.split("_")[-1]),
                    "start_date": datetime.strftime(start_date, "%Y-%m-%d"),
                    "end_date": datetime.strftime(end_date, "%Y-%m-%d"),
                    "age_group_manager_id": plain["age_group_manager_id"],
                }
            )
        registrations = {
            "kid_id": int(post_data["child_id"]),
            "parent_id": int(post_data["parent_id"]),
            "form_number": int(post_data["form_number"]),
            "plains": plains,
        }
        response = self.session.post(url, json=registrations)
        response.raise_for_status()
        return response.json()

    @endpoint(
        name="registrations",
        methods=["delete"],
        perm="can_access",
        description="Désinscrire un enfant d'une plaine",
        long_description="Désinscrit un enfant d'une plaine de vacance",
        display_category="Plaines",
        parameters={
            "registration_id": {
                "description": "Identifiant de l'inscription",
                "exemple_value": "19",
            }
        },
        example_pattern="delete",
        pattern="^delete$",
    )
    def delete_plain_registration(self, request, registration_id):
        url = f"{self.server_url}/{self.aes_instance}/plains/registration/{registration_id}"
        response = self.session.delete(url)
        response.raise_for_status()
        return response.json()

    @endpoint(
        name="registrations",
        methods=["get"],
        perm="can_access",
        description="Demander le coût des inscriptions aux plaines",
        long_description="Demande le coût des inscriptions aux plaines de vacances, en fonction des identifiants des demandes.",
        display_category="Plaines",
        example_pattern="cost",
        pattern="^cost$",
    )
    def get_plains_registrations_cost(self, request, form_numbers):
        url = f"{self.server_url}/{self.aes_instance}/plains/registrations/cost?form_numbers={form_numbers}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    #############
    ### REPAS ###
    #############

    def does_school_have_meals(self, school, school_implantations_with_meals):
        """Check if the school given by it's id offers meals
        Parameters
        ----------
            school: int or str
                id of school
            school_implantations_with_meals: list of str
                school implantations as a list of ids, can be empty
        Return
        ------
            Bool
        """
        if (
            not school_implantations_with_meals
            or str(school) in school_implantations_with_meals
        ):
            return True
        return False

    def is_in_time(self, scheduled, days_in_delay, no_later_than):
        """
        Returns True if deadline isn't reached yead

        Parameters
        ----------
            scheduled : datetime.datetime
                datetime of scheduled event
            days_in_delay : int
                number of days in delay
            no_later_than : datetime.time
                last hour:minute before deadline
        """

        def is_workday(day):
            cal = Belgium()
            return cal.is_working_day(date(day.year, day.month, day.day))

        now = datetime.now()
        if days_in_delay < 0:
            raise ValueError("days_in_delay must be equal or superior to 0")
        evaluated, remaining_delay = scheduled, days_in_delay
        while remaining_delay > 0:
            evaluated = evaluated - timedelta(days=1)
            if is_workday(evaluated):
                remaining_delay = remaining_delay - 1
        result = (
            time(now.hour, now.minute) < no_later_than
            if (
                date(evaluated.year, evaluated.month, evaluated.day)
                - date(now.year, now.month, now.day)
            ).days
            == 0
            else now < evaluated
        )
        return result

    def get_meal_registrations(self, child_id, parent_id=None):
        url = f"{self.server_url}/{self.aes_instance}/school-meals/registrations?kid_id={child_id}"
        response = self.session.get(url)
        response.raise_for_status()
        if isinstance(response.json(), list):
            registrations = response.json()
        else:
            registrations = response.json().get("items")
        return registrations

    def reverse_date(self, date, separator):
        return separator.join(reversed(date.split(separator)))

    def set_disabled_on_meal(self, registration, meal_date, parent_id):
        disabled, reasons = False, []
        if registration is not None and parent_id is not None and int(parent_id) not in registration['meal_authorized_parent_ids']:
            disabled = True
            reasons.append("Initial registering parent is not current parent")
        if meal_date <= date.today() + timedelta(days=1):
            disabled = True
            reasons.append("Too late to register: the meal date has passed or is today")
        return disabled, " - ".join(reasons)

    def get_month_menu(self, child_id, parent_id, month):
        url = f"{self.server_url}/{self.aes_instance}/menus?kid_id={child_id}&month={month}"
        response = self.session.get(url)
        response.raise_for_status()
        registrations = {f"_{self.reverse_date(registration['meal_date'], '-')}_{registration['meal_regime']}-{registration['meal_activity_id']}": registration
                         for registration in self.get_meal_registrations(child_id)}
        menus = []
        for menu in response.json()["items"]:
            for meal in menu["meal_ids"]:
                if isinstance(meal, dict):
                    meal_id = f"_{self.reverse_date(menu['date'], '-')}_{meal['regime']}-{meal['activity_id']}"
                    registration = registrations.get(meal_id)
                    disabled, disabling_reason = self.set_disabled_on_meal(registration, datetime.strptime(menu['date'], "%Y-%m-%d").date(), parent_id)
                    menus.append(
                        {
                            "id": meal_id,
                            "date": menu["date"],
                            "text": meal["name"],
                            "type": meal["regime"],
                            "meal_id": meal["meal_id"],
                            "price": meal["price"],
                            "activity_id": meal["activity_id"],
                            "is_disabled": disabled,
                            "disabling_reason": disabling_reason
                        }
                    )
        return {"data": sorted(menus, key=lambda x: x["id"])}

    def validate_month_menu(self, month_menu):
        checked_menu_ids, errors = list(), dict()
        for menu in month_menu["data"]:
            if menu["id"] in checked_menu_ids:
                index_menu = checked_menu_ids.index(menu["id"])
                error = {
                    "meal_id": menu["meal_id"],
                    "name": menu["text"],
                    "activity_id": menu["activity_id"],
                }
                if not errors.get(menu["id"]):
                    errors[menu["id"]] = {
                        "date": menu["date"],
                        "activity_id": menu["activity_id"],
                        "regime": menu["type"],
                        "meal_ids": [
                            {
                                "meal_id": month_menu["data"][index_menu]["meal_id"],
                                "name": month_menu["data"][index_menu]["text"],
                                "activity_id": month_menu["data"][index_menu][
                                    "activity_id"
                                ],
                            }
                        ],
                    }
                errors[menu["id"]]["meal_ids"].append(error)
            checked_menu_ids.append(menu["id"])
        return errors

    @endpoint(
        name="menus",
        methods=["get"],
        perm="can_access",
        description="Lire le menu pour un enfant",
        long_description="Retourne le menu auquel l'enfant peut être inscrit.",
        parameters={
            "child_id": CHILD_PARAM,
            "parent_id": PARENT_PARAM,
            "month": {
                "description": "0 pour le mois actuel, 1 pour le mois prochain, 2 pour le mois d'après.",
                "example_value": "1",
            },
        },
        display_category="Repas",
    )
    def read_month_menu(self, request, child_id, month, parent_id=None):
        if not parent_id.isdigit():
            raise ValueError("parent_id is invalid")
        month_menu = self.get_month_menu(child_id, parent_id, month)
        list_errors = self.validate_month_menu(month_menu)
        if len(list_errors) > 0:
            return {"errors_in_menus": list_errors}
        return month_menu
    
    def get_balance(self, parent_id, activity_category_type, child_id=None, year=None, month=None):
        url = f"{self.server_url}/{self.aes_instance}/parents/{parent_id}/balances/{activity_category_type}"
        if child_id or year or month:
            url += "?"
            url += "&".join(f"{k}={v}" for k, v in {"child_id": child_id, "year": year, "month": month}.items() if v)
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def reserve_balance(self, parent_id, data):
        url = f"{self.server_url}/{self.aes_instance}/parents/{parent_id}/reserved-balances"
        logging.info(f"Reserving {data}")
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    @endpoint(
        name="parents",
        methods=["get"],
        perm="can_access",
        description="Solde du parent pour un type de catégorie d'activité",
        long_description="Renvoie la valeur du solde du parent.",
        example_pattern="{parent_id}/balance/activity_category_type",
        pattern="^(?P<parent_id>\w+)/balance/(?P<activity_category_type>\w+)$",
        parameters={
            "parent_id": PARENT_PARAM,
            "activity_category_type": {
                "description": "Identifiant du type de la catégorie d'activité",
                "example_value": "meal",
            },
            "child_id": CHILD_PARAM,
            "month": {
                "description": "0 pour le mois actuel, 1 pour le mois prochain, 2 pour le mois d'après.",
                "example_value": "1",
            },
        },
        display_category="Parent",
    )
    def get_balance_for_activity_category_type(self, request, parent_id, activity_category_type, child_id=None, month=None):
        if month is not None and month not in ["0", "1", "2"]:
            raise ValueError(
                "Le mois ne peut avoir comme valeur que 0, 1, ou 2. Voir la description du paramètre pour en savoir plus."
            )
        reference_day = date.today() + relativedelta(months=int(month))
        return self.get_balance(parent_id, activity_category_type, child_id=child_id, year=reference_day.year, month=reference_day.month)

    def get_or_create_child_registration_line(self, data):
        response = self.session.post(f"{self.server_url}/{self.aes_instance}/school-meals/registrations/lines", json=data)
        response.raise_for_status()
        return response.json()

    @endpoint(
        name="parents",
        methods=["post"],
        perm="can_access",
        description="Montant d'une commande de repas",
        long_description="Calcule le montant à payer en fonction de la commande et du solde du parent",
        example_pattern="{parent_id}/menus/registrations/cost",
        pattern="^(?P<parent_id>\w+)/menus/registrations/cost$",
        parameters={
            "parent_id": PARENT_PARAM
        },
        display_category="Repas",
    )
    def compute_meals_order_amount(self, request, parent_id):
        body = json.loads(request.body)
        order = body.get('order')
        reserved_balance = None
        total_amount = sum([meal['price'] for meal in order if not meal.get("is_disabled")])
        if body.get("month") and body.get("year"):
            year, month = int(body.get('year')), int(body.get('month'))
        balance = self.get_balance(parent_id, "meal", body.get("child_id"), year, month)
        if balance.get("amount") <= 0: # Vérifier si correct, notamment si le montant bloqué est supérieur au solde
            return {
                "activity_category_id": balance["activity_category_id"],
                "reserved_balance": reserved_balance,
                "child_registration_line_id": "",
                "due_amount": total_amount,
                "initial_balance": balance["amount"],
                "prepayment_by_category_id": balance["prepayment_by_category_id"],
                "spent_balance": 0, 
                "total_amount": total_amount,
            }
        # If total <= balance: due_amount set to 0, spent_balance set to balance - total
        due_amount, spent_balance = 0, total_amount
        # If total > balance
        if total_amount > balance["amount"]:
            due_amount = total_amount - balance["amount"]
            spent_balance = balance["amount"]
        # Reserve spent balance
        child_registration_line_response = None
        reserved_balance = None
        if spent_balance:
            child_registration_line = {
                "kid_id": body["child_id"],
                "parent_id": int(parent_id),
                "school_implantation_id": int(body["school_implantation_id"]),
                "month": int(body["month"]),
                "year": int(body["year"])
            }
            child_registration_line_response = self.get_or_create_child_registration_line(child_registration_line)
            reserved_balance = None
            if spent_balance - balance["already_reserved_amount"] > 0:
                reserved_balance = self.reserve_balance(parent_id, {
                    "prepayment_by_category_id": balance["prepayment_by_category_id"],
                    "amount": spent_balance - balance["already_reserved_amount"],
                    "date": date.today().strftime("%Y-%m-%d"),
                    "reserving_request": int(body['form_number']),
                    "child_registration_line_id": child_registration_line_response["id"]
                })

        return {
            "activity_category_id": balance["activity_category_id"],
            "reserved_balance": reserved_balance,
            "child_registration_line_id": child_registration_line_response["id"],
            "due_amount": due_amount,
            "initial_balance": balance["amount"],
            "prepayment_by_category_id": balance["prepayment_by_category_id"],
            "spent_balance": spent_balance,
            "total_amount": total_amount,
        }

    def create_meals_payment(self, data):
        response = self.session.post(f"{self.server_url}/{self.aes_instance}/school-meals/payments", json=data)
        response.raise_for_status()
        return response.json()

    @endpoint(
        name="parents",
        methods=["post"],
        perm="can_access",
        description="Encode un paiement",
        long_description="Encode un paiement générique.",
        display_category="Parent",
        parameters={
            "parent_id": PARENT_PARAM,
        },
        example_pattern="{parent_id}/payments/",
        pattern="^(?P<parent_id>\d+)/payments/$",
    )
    def generic_create_payment(self, request, parent_id):
        body = json.loads(request.body)
        payment = self.create_meals_payment({
            "activity_category_id": body["activity_category_id"],
            "amount": body["amount"].replace(",", "."),
            "comment": body["comment"],
            "date": date.today().strftime("%Y-%m-%d"),
            "parent_id": parent_id, # TODO: parent facturable
            "prepayment_by_category_id": body["prepayment_by_category_id"],
            "type": "online"
        })
        return payment

    @endpoint(
        name="parents",
        methods=["post"],
        perm="can_access",
        description="Réserve du solde",
        long_description="Réserve du solde d'un parent pour le rendre non disponible pour d'autres commandes.",
        display_category="Parent",
        parameters={
            "parent_id": PARENT_PARAM,
        },
        example_pattern="{parent_id}/reserved-balances/",
        pattern="^(?P<parent_id>\d+)/reserved-balances/$",
    )
    def create_reserved_balance(self, request, parent_id):
        body = json.loads(request.body)
        if not body["child_registration_line_id"]:
            child_registration_line = {
                    "kid_id": body["child_id"],
                    "parent_id": int(parent_id), # TODO: parent factu
                    "school_implantation_id": int(body["school_implantation_id"]),
                    "month": int(body["month"]),
                    "year": int(body["year"])
                }
            child_registration_line_response = self.get_or_create_child_registration_line(child_registration_line)
        reserved_balance = self.reserve_balance(parent_id, {
                "prepayment_by_category_id": body["prepayment_by_category_id"],
                "amount": body["amount"].replace(",", "."),
                "date": date.today().strftime("%Y-%m-%d"),
                "reserving_request": int(body['form_number']),
                "child_registration_line_id": body["child_registration_line_id"] or child_registration_line_response["id"]
            }
        )
        return reserved_balance

    @endpoint(
        name="parents",
        methods=["delete"],
        perm="can_access",
        description="Débloque un solde",
        long_description="Supprime un blocage de solde.",
        display_category="Parent",
        parameters={
            "parent_id": PARENT_PARAM,
            "reserved_balance_id": {
                "description": "Solde bloqué à supprimer",
                "example_value": 1,
            }
        },
        example_pattern="{parent_id}/reserved-balances/{reserved_balance_id}",
        pattern="^(?P<parent_id>\d+)/reserved-balances/(?P<reserved_balance_id>\d+)$",
    )
    def free_balance(self, request, parent_id, reserved_balance_id):
        url = f"{self.server_url}/{self.aes_instance}/parents/{parent_id}/reserved-balances/{reserved_balance_id}"
        response = self.session.delete(url)
        response.raise_for_status()
        return True

    @endpoint(
        name="menus",
        methods=["post"],
        perm="can_access",
        description="Inscrire un enfant aux repas",
        long_description="Crée les inscriptions aux repas dans iA.AES pour un enfant.",
        example_pattern="registrations",
        pattern="^registrations$",
        display_category="Repas",
    )
    def create_menu_registration(self, request):
        post_data = json.loads(request.body)
        date_menu = datetime.strptime(post_data["meals"][0]["date"], "%Y-%m-%d")
        data = {
            "kid_id": int(post_data["child_id"]),
            "parent_id": int(post_data["parent_id"]),
            "month": date_menu.month,
            "year": date_menu.year,
            "meals": [
                {
                    "day": int(meal["date"][-2:]),
                    "activity_id": meal["activity_id"],
                    "meal_ids": [meal["meal_id"]],
                }
                for meal in post_data["meals"] if not meal.get("is_disabled")
            ],
        }
        if not len(data["meals"]):
            return
        url = f"{self.server_url}/{self.aes_instance}/school-meals/registrations"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    @endpoint(
        name="children",
        methods=["get"],
        perm="can_access",
        description="Liste les inscriptions aux repas d'un enfant",
        long_description="Retourne, pour un enfant donné, ses inscriptions futures, dans le but de l'en désincrire.",
        parameters={
            "child_id": CHILD_PARAM,
            "parent_id": PARENT_PARAM,
            "month": {
                "description": "Mois sélectionné - 0 pour ce mois-ci, 1 pour le mois prochain, 2 pour le mois d'après.",
                "example_value": 0,
            },
            "days_in_delay": {
                "description": "Délai en jours avant le repas.",
                "example_value": 1,
            },
            "no_later_than": {
                "description": "Dernier moment avant la désinscription, lors du dernier jour permis par le délai.",
                "example_value": "19:00",
            },
        },
        example_pattern="{child_id}/registrations",
        pattern="^(?P<child_id>\w+)/registrations$",
        display_category="Repas",
    )
    def list_meal_registrations(
        self, request, child_id, parent_id=None, days_in_delay=1, no_later_than="19:00", month=None
    ):
        if month is not None and month not in [0, 1, 2]:
            raise ValueError(
                "Le mois ne peut avoir comme valeur que 0, 1, ou 2. Voir la description du paramètre pour en savoir plus."
            )
        registrations = self.get_meal_registrations(child_id=child_id)
        result = list()
        for registration in registrations:
            meal_date = datetime.strptime(registration["meal_date"], "%Y-%m-%d")
            if month is not None:
                today = datetime.today()
                selected_month = (
                    today.month + month
                    if today.month < 13
                    else today.month + month - 12
                )
            if (month is None or meal_date.month == selected_month):
                is_disabling_delay = not self.is_in_time(meal_date, days_in_delay, time.fromisoformat(no_later_than))
                result.append(
                    {
                        "id": f"_{datetime.strftime(meal_date, '%d-%m-%Y')}_{registration['meal_regime']}-{registration['meal_activity_id']}",
                        "meal_detail_id": int(registration["meal_detail_id"]),
                        "date": registration["meal_date"],
                        "text": f"{datetime.strftime(meal_date, '%d/%m/%Y')} {registration['meal_name']}",
                        "regime": registration["meal_regime"],
                        "parent_id": registration["meal_parent_id"],
                        "disabled": is_disabling_delay or (bool(parent_id) and int(parent_id) not in registration['meal_authorized_parent_ids'])
                    }
                )
        return {"data": result}

    @endpoint(
        name="children",
        methods=["get"],
        perm="can_access",
        description="Liste brutalement les inscriptions aux repas d'un enfant",
        long_description="Retourne, pour un enfant donné, ses inscriptions futures brutes, dans le but de voir ce qui s'y passe.",
        parameters={
            "child_id": CHILD_PARAM,
        },
        example_pattern="{child_id}/registrations/raw",
        pattern="^(?P<child_id>\w+)/registrations/raw$",
        display_category="Repas",
    )
    def get_meal_registrations_raw(self, request, child_id):
        return self.get_meal_registrations(child_id=child_id)

    @endpoint(
        name="children",
        methods=["post"],
        perm="can_access",
        description="Désinscrire un enfant des repas",
        long_description="Supprime des inscriptions aux repas dans iA.AES pour un enfant.",
        example_pattern="registrations/delete",
        pattern="^registrations/delete$",
        display_category="Repas",
    )
    def delete_menu_registration(self, request):
        data = dict()
        data["meals"] = [
            meal["meal_detail_id"] for meal in json.loads(request.body).get("meals")
        ]
        url = f"{self.server_url}/{self.aes_instance}/school-meals/registrations/delete"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    ###################
    ### Fiche santé ###
    ###################

    @endpoint(
        name="healthsheet-questions",
        methods=["get"],
        perm="can_access",
        description="Référence les questions liées à la fiche santé.",
        display_category="Fiche santé",
    )
    def healthsheet_questions(self, request):
        return {
            "data": [
                {
                    "id": "blood_type",
                    "text": "Quel est le groupe sanguin de l'enfant ?",
                },
                {"id": "bike", "text": "L'enfant sait-il rouler à vélo ?"},
                {"id": "glasses", "text": "L'enfant porte-t-il des lunettes ?"},
                {
                    "id": "hearing_aid",
                    "text": "L'enfant porte-t-il un appareil auditif ?",
                },
                {"id": "nap", "text": "L'enfant fait-il la sieste ?"},
                {
                    "id": "emotional_support",
                    "text": "L'enfant a-t-il un doudou ou une tutute ?",
                },
                {"id": "weight", "text": "Quel est le poids de l'enfant ?"},
                {
                    "id": "tetanos",
                    "text": "L'enfant a-t'il été vacciné contre le tétanos ?",
                },
                {
                    "id": "intervention",
                    "text": "L'enfant a-t'il subit une intervention récemment ?",
                },
                {"id": "swim", "text": "L'enfant sait-il nager ?"},
                {"id": "handicap", "text": "L'enfant souffre t'il d'un handicap ?"},
                {"id": "activity_no_available", "text": "Activités non praticables"},
                {"id": "regime", "text": "L'enfant suit-il un régime spécifique ?"},
                {
                    "id": "arnica",
                    "text": "Autorisez-vous les accompagnants à utiliser du gel arnica ?",
                },
                {"id": "allergies", "text": "L'enfant a-t'il des allergies ?"},
                {
                    "id": "new_allergies",
                    "text": "Permettre aux parents d'ajouter d'autres allergies ?",
                },
                {"id": "diseases", "text": "L'enfant a-t'il des maladies ?"},
                {
                    "id": "new_diseases",
                    "text": "Permettre aux parents d'ajouter d'autres maladies ?",
                },
                {
                    "id": "mutuality",
                    "text": "À quelle mutuelle l\enfant est-il affilié ?",
                },
                {
                    "id": "medication",
                    "text": "L'enfant doit-il prendre des médicaments ?",
                },
                {
                    "id": "medical_data",
                    "text": "Y a-t-il des "
                    "données médicales "
                    "spécifiques "
                    "importantes à "
                    "connaître pour le "
                    "bon déroulement "
                    "des activités ("
                    "épilepsie,"
                    "problème "
                    "cardiaque, "
                    "asthme, ...) ?",
                    "disabled": True,
                },
                {
                    "id": "other_contact_address",
                    "text": "Demander l'adresse des autres contacts",
                },
                {
                    "id": "photo",
                    "text": "L'enfant peut-il être pris en photo durant les stages ou les plaines ?",
                },
                {
                    "id": "photo_general",
                    "text": "L'enfant peut-il être pris en photo lors des garderies, ateliers, spectacles, ou autre ?",
                },
                {
                    "id": "facebook",
                    "text": "Les photos de l'enfant peuvent-elles être publiées sur les réseaux sociaux (site de la commune, "
                    "Facebook) ?",
                },
                {
                    "id": "medical_autorisation",
                    "text": "Je marque mon accord pour que la prise en charge ou les traitements estimés nécessaires soient entrepris durant le séjour de mon enfant par les responsables de l’accueil ou par le service médical qui y est associé. J’autorise le médecin local à prendre les décisions qu’il juge urgentes et indispensables pour assurer l’état de santé de l’enfant, même s’il s’agit d’une intervention chirurgicale. En cas d’urgence, les parents/tuteurs seront avertis le plus rapidement possible. Néanmoins, s’ils ne sont pas joignables et que l’urgence le requiert, l’intervention se fera sans leur consentement.",
                },
                {
                    "id": "covid",
                    "text": "Je m’engage sur l’honneur à ce que moi-même ou un autre adulte de la bulle sociale de mon enfant soit joignable par téléphone et d’avoir la possibilité de venir chercher l’enfant immédiatement pendant toute la durée de l’activité si son état de santé le nécessite, et de s’engager dans ce cas à faire consulter le participant dès que possible (et endéans les 24h du retour au plus tard) par son médecin référent ou un autre médecin si ce dernier n’est pas disponible",
                },
                {
                    "id": "rgpd",
                    "text": "Je consens au traitement de mes données à caractère personnel par l'Administration communale de Chaudfontaine conformément à sa charte relative à la protection de la vie privée.",
                },
            ]
        }

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
        is_healthsheet_valid = 30 >= (datetime.today() - healthsheet_last_update).days
        return is_healthsheet_valid

    @endpoint(
        name="children",
        methods=["get"],
        perm="can_access",
        description="Lire la fiche santé d'un enfant",
        parameters={"child_id": CHILD_PARAM},
        example_pattern="{child_id}/healthsheet/",
        pattern="^(?P<child_id>\w+)/healthsheet/$",
        display_category="Fiche santé",
    )
    def read_healthsheet(self, request, child_id):
        url = f"{self.server_url}/{self.aes_instance}/kids/{child_id}/healthsheet"
        response = self.session.get(url)
        data = response.json()[0]
        healthsheet = dict()
        healthsheet["activity_no_available_reason"] = (
            data["activity_no_available_reason"] or ""
        )
        healthsheet["activity_no_available_selection"] = data[
            "activity_no_available_selection"
        ]
        healthsheet["activity_no_available_text"] = (
            data["activity_no_available_text"] or ""
        )
        healthsheet["allergy_consequence"] = data["allergy_consequence"] or ""
        healthsheet["allergy_ids"] = [
            str(allergy["id"]) for allergy in data["allergy_ids"]
        ]
        healthsheet["allergy_selection"] = data["allergy_selection"]
        healthsheet["allergy_treatment"] = data["allergy_treatment"] or ""
        healthsheet["allowed_contact_ids"] = data["allowed_contact_ids"]
        healthsheet["authorization_ids"] = data["authorization_ids"]
        healthsheet["arnica"] = data["arnica"]
        healthsheet["bike"] = data["bike"]
        healthsheet["blood_type"] = data["blood_type"]
        healthsheet["comment"] = data["comment"]
        healthsheet["disease_ids"], healthsheet["disease_details"] = list(), list()
        for disease in data["disease_ids"]:
            healthsheet["disease_ids"].append(str(disease["disease_type_id"][0]))
            healthsheet["disease_details"].append(
                {
                    "gravity": disease["gravity"] or "",
                    "treatment": disease["disease_text"],
                }
            )
        healthsheet["doctor_id"] = data["doctor_id"]
        healthsheet["emotional_support"] = data["emotional_support"]
        healthsheet["facebook"] = data["facebook"]
        healthsheet["first_date_tetanus"] = data["first_date_tetanus"]
        healthsheet["handicap_selection"] = data["handicap_selection"]
        healthsheet["has_medication"] = (
            "yes" if len(data["medication_ids"]) > 0 else "not_specified"
        )
        healthsheet["hearing_aid"] = data["hearing_aid"]
        healthsheet["glasses"] = data["glasses"]
        healthsheet["id"] = data["id"]
        healthsheet["intervention_text"] = data["intervention_text"] or ""
        healthsheet["intervention_selection"] = data["intervention_selection"]
        healthsheet["last_date_tetanus"] = data["last_date_tetanus"]
        healthsheet["level_handicap"] = data["level_handicap"]
        healthsheet["medication_ids"] = [
            {
                "name": medication["name"],
                "quantity": medication["quantity"],
                "period": medication["period"],
                "self_medication": medication["self_medication_selection"],
            }
            for medication in data["medication_ids"]
        ]
        healthsheet["mutuality"] = data["mutuality"] or ""
        healthsheet["nap"] = data["nap"]
        # healthsheet["medication_type_selection"] = data.get("medication_type_selection") or []
        healthsheet["photo"] = data["photo"]
        healthsheet["photo_general"] = data["photo_general"]
        healthsheet["self_medication"] = data["self_medication"]
        healthsheet["specific_regime_selection"] = data["specific_regime_selection"]
        healthsheet["specific_regime_text"] = data["specific_regime_text"] or ""
        healthsheet["swim"] = data["swim"]
        healthsheet["swim_level"] = data["swim_level"]
        healthsheet["tetanus_selection"] = data["tetanus_selection"]
        healthsheet["to_go_alone"] = data["to_go_alone"]
        healthsheet["type_handicap"] = data["type_handicap"]
        healthsheet["weight"] = data["weight"] or ""
        return healthsheet

    @endpoint(
        name="children",
        methods=["put"],
        perm="can_access",
        description="Mettre à jour la fiche santé d'un enfant",
        parameters={"child_id": CHILD_PARAM},
        example_pattern="{child_id}/healthsheet/update",
        pattern="^(?P<child_id>\w+)/healthsheet/update$",
        display_category="Fiche santé",
    )
    def update_healthsheet(self, request, child_id):
        origin_data = json.loads(request.body)
        put_data = dict()
        # prepare authorizations
        authorizations = list()
        if origin_data["mandatory_authorizations"]:
            authorizations += origin_data["mandatory_authorizations"]
        if origin_data["optional_authorizations"]:
            authorizations += origin_data["optional_authorizations"]
        # prepare put_data
        if origin_data["activity_no_available_reason"]:
            put_data["activity_no_available_reason"] = origin_data[
                "activity_no_available_reason"
            ]
        if origin_data["allergy_consequence"] and (
            origin_data["allergy_ids"] or origin_data["other_allergies"]
        ):
            put_data["allergy_consequence"] = origin_data["allergy_consequence"]
        else:
            put_data["allergy_consequence"] = ""
        put_data["allergy_ids"] = (
            [int(allergy) for allergy in origin_data["allergy_ids"]]
            if origin_data["allergy_ids"]
            else list()
        )
        if origin_data["allergy_treatment"] and (
            origin_data["allergy_ids"] or origin_data["other_allergies"]
        ):
            put_data["allergy_treatment"] = origin_data["allergy_treatment"]
        else:
            put_data["allergy_treatment"] = ""
        if origin_data["arnica"]:
            put_data["arnica"] = origin_data["arnica"]
        put_data["authorization_ids"] = [
            int(authorization) for authorization in authorizations
        ]
        if origin_data["bike"]:
            put_data["bike"] = origin_data["bike"]
        if origin_data["blood_type"]:
            put_data["blood_type"] = origin_data["blood_type"]
        if origin_data["comment"]:
            put_data["comment"] = origin_data["comment"]
        if origin_data["child_id"]:
            put_data["child_id"] = int(origin_data["child_id"])
        if origin_data["doctor_id"]:
            put_data["doctor_id"] = origin_data["doctor_id"]
        if origin_data["emotional_support"]:
            put_data["emotional_support"] = origin_data["emotional_support"]
        if origin_data["facebook"]:
            put_data["facebook"] = origin_data["facebook"]
        if origin_data["first_date_tetanus"]:
            put_data["first_date_tetanus"] = origin_data["first_date_tetanus"]
        if origin_data["glasses"]:
            put_data["glasses"] = origin_data["glasses"]
        if origin_data["hearing_aid"]:
            put_data["hearing_aid"] = origin_data["hearing_aid"]
        if origin_data["last_date_tetanus"]:
            put_data["last_date_tetanus"] = origin_data["last_date_tetanus"]
        if origin_data["level_handicap"]:
            put_data["level_handicap"] = origin_data["level_handicap"]
        if origin_data["mutuality"]:
            put_data["mutuality"] = origin_data["mutuality"]
        if origin_data["nap"]:
            put_data["nap"] = origin_data["nap"]
        if origin_data["other_allergies"]:
            # As other_allergies is a list of list, we need to make it a list of string. It is a list of list
            # because of the type of other_allergies field in form.
            put_data["other_allergies"] = [
                allergy[0] for allergy in origin_data["other_allergies"]
            ]
        if origin_data["other_diseases"]:
            # As other_diseases is a list of list, we need to make it a list of string. It is a list of list
            # because of the type of other_diseases field in form.
            put_data["other_diseases"] = [
                disease[0] for disease in origin_data["other_diseases"]
            ]
        if origin_data["photo"]:
            put_data["photo"] = origin_data["photo"]
        if origin_data["photo_general"]:
            put_data["photo_general"] = origin_data["photo_general"]
        if origin_data["swim"]:
            put_data["swim"] = origin_data["swim"]
        if origin_data["swim_level"]:
            put_data["swim_level"] = origin_data["swim_level"]
        if origin_data["to_go_alone"]:
            put_data["to_go_alone"] = origin_data["to_go_alone"]
        if origin_data["type_handicap"]:
            put_data["type_handicap"] = origin_data["type_handicap"]
        if origin_data["weight"]:
            put_data["weight"] = origin_data["weight"]

        medication_ids, allowed_contact_ids = [], []
        for key, value in origin_data.items():
            if ("selection" in key or "text" in key) and value:
                put_data[key] = value or ""
            elif "medication_" in key and value:
                medication = value.split(" - ")
                if medication[0] != "None":
                    medication_ids.append(
                        {
                            "name": medication[0],
                            "quantity": int(medication[1])
                            if medication[1] and medication[1] != "None"
                            else None,
                            "period": medication[2],
                            "self_medication_selection": medication[3],
                        }
                    )
            elif "contact" in key:
                contact = value.split(" ; ")
                if contact[0]:
                    allowed_contact_ids.append(
                        {"partner_id": int(contact[0]), "parental_link": contact[1]}
                    )
        disease_ids = list()
        if origin_data["disease_ids"]:
            for disease_id in enumerate(origin_data["disease_ids"]):
                disease_ids.append(
                    {
                        "disease_type_id": int(disease_id[1]),
                        "gravity": origin_data.get(f"disease_{disease_id[0]}_gravity"),
                        "disease_text": origin_data.get(
                            f"disease_{disease_id[0]}_treatment"
                        ),
                    }
                )
        if medication_ids:
            put_data["medication_ids"] = medication_ids
        if allowed_contact_ids:
            put_data["allowed_contact_ids"] = allowed_contact_ids
        put_data["disease_ids"] = disease_ids
        if not disease_ids:
            put_data["other_disease_gravity"] = (origin_data.get(f"disease_0_gravity"),)
            put_data["other_disease_text"] = (origin_data.get(f"disease_0_treatment"),)
        url = f"{self.server_url}/{self.aes_instance}/kids/{child_id}/healthsheet"
        response = self.session.put(url, json=put_data)
        response.raise_for_status()
        return True

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
                    {"id": str(choice["id"]), "text": choice["name"]} for choice in v
                ]
        # Artificially add items of has_medication field that does not exist in iA.AES
        result.update(
            {
                "has_medication": [
                    {"id": "not_specified", "text": "Non renseigné"},
                    {"id": "no", "text": "Non"},
                    {"id": "yes", "text": "Oui"},
                ]
            }
        )
        return result

    @endpoint(
        name="authorizations",
        methods=["get"],
        perm="can_access",
        description="Rechercher les autorisations",
        long_description="Rerchercher les autorisations que le parent doit cocher dans la fiche santé.",
        display_category="Fiche santé",
        parameters={
            "filter": {
                "description": "Filter le résultat. Laisser vide pour ne pas filtrer. Les deux valeurs possibles sont 'mandatory' et 'optional'.",
                "example_value": "mandatory",
                "optional": True,
                "type": "str",
                "default_value": "mandatory",
            },
        },
        cache_duration=600,
    )
    def get_authorizations(self, request, filter=None):
        if filter and filter not in ["mandatory", "optional"]:
            raise ValueError(
                f"Filter value '{filter}' is unknown. It must be 'mandatory' or 'optional'."
            )
        url = f"{self.server_url}/{self.aes_instance}/authorizations"
        response = self.session.get(url).json()
        if not filter:
            return response
        if filter == "mandatory":
            is_mandatory = True
        if filter == "optional":
            is_mandatory = False
        result = list()
        for authorization in response["data"]:
            if authorization["is_mandatory"] == is_mandatory:
                result.append(authorization)
        return {"data": result}

    @endpoint(
        name="allergies",
        methods=["get"],
        perm="can_access",
        description="Lister les allergies",
        long_description="Lister les allergies qui peuvent être proposées dans le contexte d'une fiche santé",
        display_category="Fiche santé",
        parameters={
            "healthsheet": {
                "description": "Identifiant d'une fiche santé",
                "example_value": 1,
                "optional": True,
                "type": "int",
                "default_value": None,
            },
        },
        cache_duration=60
    )
    def list_allergies(self, request, healthsheet=None):
        url = f"{self.server_url}/{self.aes_instance}/allergies"
        if healthsheet:
            url += f"?health_sheet_id={healthsheet}"
        response = self.session.get(url)
        response.raise_for_status()
        result = dict(
            data=[
                {"id": str(allergy["id"]), "name": allergy["name"]}
                for allergy in response.json()["data"]
            ]
        )
        return result

    @endpoint(
        name="diseases",
        methods=["get"],
        perm="can_access",
        description="Lister les maladies",
        long_description="Lister les maladies qui peuvent être proposées dans le contexte d'une fiche santé",
        display_category="Fiche santé",
        parameters={
            "healthsheet": {
                "description": "Identifiant d'une fiche santé",
                "example_value": 1,
                "optional": True,
                "type": "int",
                "default_value": None,
            },
        },
        cache_duration=60,
    )
    def list_diseases(self, request, healthsheet=None):
        url = f"{self.server_url}/{self.aes_instance}/diseases"
        if healthsheet:
            url += f"?health_sheet_id={healthsheet}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    ################
    ### Contacts ###
    ################

    @endpoint(
        name="contacts",
        methods=["post"],
        perm="can_access",
        description="Créer un contact",
        long_description="Crée un contact.",
        example_pattern="create",
        pattern="^create$",
        display_category="Contact",
    )
    def create_contact(self, request):
        post_data = json.loads(request.body)
        url = f"{self.server_url}/{self.aes_instance}/contacts"
        contact = {
            "firstname": post_data["firstname"],
            "lastname": post_data["lastname"],
            "phone": post_data["phone"],
            "mobile": post_data["mobile"] or "",
            "street": post_data["street"],
            "is_company": False,
            "locality_id": int(post_data["locality_id"])
            if post_data["locality_id"]
            else None,
            "country_id": int(post_data["country_id"])
            if post_data["country_id"]
            else None,
            "zip": post_data.get("zipcode") or "",
            "city": post_data.get("city") or "",
        }
        response = self.session.post(url, json=contact)
        response.raise_for_status()
        return response.json()

    #################
    ### Méddecins ###
    #################

    @endpoint(
        name="doctors",
        methods=["post"],
        perm="can_access",
        description="Créer un médecin",
        example_pattern="create",
        pattern="^create$",
        display_category="Médecin",
    )
    def create_doctor(self, request):
        post_data = json.loads(request.body)
        url = f"{self.server_url}/{self.aes_instance}/doctors"
        doctor = {
            "firstname": post_data["firstname"],
            "lastname": post_data["lastname"],
            "phone": post_data["phone"],
            "mobile": post_data["mobile"] or "",
            "street": post_data["street"],
            "is_company": False,
            "country_id": int(post_data["country_id"]),
        }
        if doctor["country_id"] == 20:
            doctor["locality_id"] = int(post_data["locality_id"])
        else:
            doctor["zip"] = post_data["zip"]
            doctor["city"] = post_data["city"]
        response = self.session.post(url, json=doctor)
        response.raise_for_status()
        return response.json()

    ################
    ### Factures ###
    ################

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

    ################
    ### Paiement ###
    ################

    @endpoint(
        name="payment",
        methods=["post"],
        perm="can_access",
        description="Créer un Paiement",
        example_pattern="create",
        pattern="^create$",
        display_category="Paiement",
    )
    def create_payment(self, request):
        post_data = json.loads(request.body)
        url = f"{self.server_url}/{self.aes_instance}/payment"
        payment = {
            "parent_id": int(post_data["parent_id"]),
            "amount": float(post_data["amount"].replace(",", ".")),
            "comment": post_data["comment"],
        }
        response = self.session.post(url, json=payment)
        response.raise_for_status()
        return response.json()

    ###################
    ### Utilitaires ###
    ###################

    @endpoint(
        name="date-limite",
        methods=["get"],
        perm="can_access",
        description="Calcule une date de naissance limite",
        long_description="Calcule une date, qui correspond à une limite de\
             date de naissance, en fonction de la date de début d'activité,\
             ainsi que d'un âge en année, mois et jours.",
        parameters={
            "limit_date": {
                "description": "Date au format DD/MM/YYYY",
                "example_value": "26/12/2022",
            },
            "age_years": {
                "description": "Années en entier, au moins 0.",
                "example_value": 5,
            },
            "age_months": {
                "description": "Mois, en entier, entre 0 et 12.",
                "example_value": 11,
            },
            "age_days": {
                "description": "Date, en jours, au moins 0.",
                "example_value": 30,
            },
        },
        display_category="Utilitaires",
    )
    def get_limit_birthdate(self, request, limit_date, age_years, age_months, age_days):
        day, month, year = [int(el) for el in limit_date.split("/")]
        if age_months > 12:
            raise ValueError("month must be int between 0 and 12")
        elif month > age_months:
            result = date(year - age_years, month - age_months, day) - timedelta(
                days=age_days
            )
        else:
            result = date(
                year - 1 - age_years, month - age_months + 12, day
            ) - timedelta(days=age_days)
        return {"data": result}
