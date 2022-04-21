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


import logging
import re
import requests
from django.db import models
from django.conf import settings
from django.http import Http404
from django.http import HttpResponse
from django.urls import path, reverse
from django.core.exceptions import MultipleObjectsReturned
from datetime import datetime, timedelta
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
        "example_value": "22",
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
        return response.json()

    def filter_localities_by_zipcode(self, zipcode):
        localities = [
            locality
            for locality in self.get_localities()["items"]
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
        aes_localities = self.filter_localities_by_zipcode(str(zipcode))
        for aes_locality in aes_localities:
            aes_locality["matching_score"] = self.compute_matching_score(
                aes_locality["name"], locality
            )
        return sorted(aes_localities, key=lambda x: x["matching_score"])[0]

    def list_countries(self):
        url = f"{self.server_url}/{self.aes_instance}/countries"
        response = self.session.get(url)
        return response.json()["items"]

    def search_country(self, country):
        aes_countries = self.list_countries()
        for aes_country in aes_countries:
            aes_country["matching_score"] = self.compute_matching_score(
                aes_country["name"], country
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
        aes_localities = self.filter_localities_by_zipcode(str(zipcode))
        for aes_locality in aes_localities:
            aes_locality["matching_score"] = self.compute_matching_score(
                aes_locality["name"], locality
            )
        return sorted(aes_localities, key=lambda x: x["matching_score"])

    @endpoint(
        name="localities",
        methods=["get"],
        perm="can_access",
        description="Lister les localités",
        long_description="Liste les localités et leurs codes postaux.",
        display_category="Localités",
    )
    def list_localities(self, request):
        return self.get_localities()

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
        display_category="Parent",
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
        post_data = json_loads(request.body)
        parent = {
            "firstname": post_data["firstname"],
            "lastname": post_data["lastname"],
            "email": post_data["email"],
            "phone": post_data["phone"],
            "street": post_data["street"],
            "is_company": post_data["is_company"],
            "national_number": post_data["national_number"],
            "registration_number": post_data["registration_number"],
            "country_id": self.search_country(post_data["country"])["id"],
        }
        if post_data["country"].lower() == "belgique":
            parent["locality_id"] = self.search_locality(
                post_data["zipcode"], post_data["locality"]
            )["id"]
        else:
            parent["zip"] = post_data["zipcode"]
            parent["city"] = post_data["locality"]
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
                    "age": child["age"],
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
        signed_forms_url_response.raise_for_status()
        return signed_forms_url_response.json()["data"]

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
        description="Page d'accueil",
        long_description="Agrège les données dont la page d'accueil du Portail Parent a besoin.",
        parameters={"parent_id": PARENT_PARAM},
        example_pattern="{parent_id}/homepage/",
        pattern="^(?P<parent_id>\w+)/homepage/$",
        display_category="Parent",
    )
    def homepage(self, request, parent_id):
        url = f"{self.server_url}/{self.aes_instance}/parents/{parent_id}/kids"
        response = self.session.get(url)
        response.raise_for_status()
        if response.status_code == 200:
            forms = self.get_pp_forms()
            children = response.json()["items"]
            result = {
                "is_parent": True,
                "children": [],
            }
            for child in children:
                has_valid_healthsheet = self.has_valid_healthsheet(child["id"])
                result["children"].append(
                    {
                        "id": child["id"],
                        "national_number": child["national_number"],
                        "name": child["display_name"],
                        "age": child["age"],
                        "activities": child["activity_ids"],
                        "school_implantation": False
                        if not child["school_implantation_id"]
                        else child["school_implantation_id"][1],
                        "level": child["level_id"],
                        "healthsheet": has_valid_healthsheet,
                        "forms": [
                            {
                                "title": form["title"],
                                "slug": form["slug"],
                                "status": self.set_form_status(
                                    form["slug"], has_valid_healthsheet
                                ),
                                "image": self.FORMS_ICONS[form["slug"]],
                            }
                            for form in forms
                            if form["slug"] in self.FORMS_ICONS
                        ],
                    }
                )
        else:
            result = {"is_parent": False, "status": response.status_code}
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
        self, compute_price_category, parent_zipcode, municipality_zipcodes
    ):
        price_categories = self.list_price_categories()
        if compute_price_category == "non":
            price_category = price_categories["Aucun"]
        elif parent_zipcode in municipality_zipcodes:
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
        post_data = json_loads(request.body)
        price_category_id = self.set_price_category(
            post_data["compute_price_category"],
            post_data["parent_zipcode"],
            post_data["municipality_zipcodes"],
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
        self.logger.info(f"CHILD : {child}")
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
        url = f"{self.server_url}/{self.aes_instance}/persons?national_number={national_number}&lastname={lastname}&firstname={firstname}&birthdate={birthdate}"
        response = self.session.get(url)
        response.raise_for_status()
        if response.json()["items_total"] == 1:
            child = response.json()["items"][0]
        elif response.json()["items_total"] == 0:
            child = None
        else:
            raise MultipleObjectsReturned
        return {"child": child}

    @endpoint(
        name="children",
        methods=["patch"],
        perm="can_access",
        description="Ajouter un parent",
        long_description="Ajoute un parent à un enfant",
        parameters={"child_id": CHILD_PARAM, "parent_id": PARENT_PARAM},
        example_pattern="{child_id}/add_parent/",
        pattern="^(?P<child_id>\w+)/add_parent/$",
        display_category="Enfant",
    )
    def add_parent_to_child(self, request, child_id, parent_id):
        url = f"{self.server_url}/{self.aes_instance}/kids/{child_id}/?parent_id={parent_id}"
        response = self.session.patch(url)
        response.raise_for_status()
        return response.json()

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
    )
    def list_available_plains(self, request, child_id):
        url = f"{self.server_url}/{self.aes_instance}/plains?kid_id={child_id}"
        response = self.session.get(url)
        weeks, result = set(), []
        for activity in response.json():
            new_activity = {
                "id": "{}_{}_{}".format(
                    activity["year"], activity["week"], activity["id"]
                ),
                "text": activity.get("theme")
                if activity.get("theme") and activity.get("theme") != "False"
                else activity["activity_name"],
                "week": activity["week"],
                "year": activity["year"],
                "start_date": activity["start_date"],
                "end_date": activity["end_date"],
                "age_group_manager_id": activity["age_group_manager_id"],
            }
            if activity["week"] not in weeks:
                result.append(
                    {
                        "id": activity["week"],
                        "text": "Semaine {}".format(activity["week"]),
                        "activities": [new_activity],
                        "week": activity["week"],
                        "monday": datetime.strptime(
                            "{}-{}-1".format(datetime.today().year, activity["week"]),
                            "%Y-%W-%w",
                        ).date(),
                        "year": activity["year"],
                    }
                )
                weeks.add(activity["week"])
            else:
                [
                    week["activities"].append(new_activity)
                    for week in result
                    if week["id"] == activity["week"]
                ]
        return result

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
        post_data = json_loads(request.body)
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

    def get_month_menu(self, child_id, month):
        url = f"{self.server_url}/{self.aes_instance}/menus?kid_id={child_id}&month={month}"
        response = self.session.get(url)
        response.raise_for_status()
        menus = []
        for menu in response.json()["items"]:
            menus.append(
                {
                    "id": f"_{menu['date'][8:]}{menu['date'][4:8]}{menu['date'][:4]}_{menu['meal_ids'][1]['regime']}-{menu['meal_ids'][1]['activity_id']}",
                    "date": menu["date"],
                    "text": menu["meal_ids"][1]["name"],
                    "type": menu["meal_ids"][1]["regime"],
                    "meal_id": menu["meal_ids"][1]["meal_id"],
                    "activity_id": menu["meal_ids"][1]["activity_id"],
                }
            )
        return {"data": sorted(menus, key=lambda x: x["id"])}

    def validate_month_menu(self, month_menu):
        checked_menu_ids, errors = list(), list()
        for menu in month_menu["data"]:
            if menu["id"] in checked_menu_ids:
                error = {"date": menu["date"], "regime": menu["type"]}
                errors.append(error)
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
            "month": {
                "description": "0 pour le mois actuel, 1 pour le mois prochain, 2 pour le mois d'après.",
                "example_value": "1",
            },
        },
        display_category="Repas",
    )
    def read_month_menu(self, request, child_id, month):
        month_menu = self.get_month_menu(child_id, month)
        list_errors = self.validate_month_menu(month_menu)
        if len(list_errors) > 0:
            return {"errors_in_menus": list_errors}
        return month_menu

    @endpoint(
        name="menus",
        methods=["post"],
        perm="can_access",
        description="Inscrire un enfant aux repas",
        long_description="Crée les inscriptions aux repas dans iA.AES pour un enfant.",
        example_pattern="registration",
        pattern="^registration$",
        display_category="Repas",
    )
    def create_menu_registration(self, request):
        post_data = json_loads(request.body)
        date_menu = datetime.strptime(post_data["meals"][0]["date"], "%Y-%m-%d")
        data = {
            "kid_id": int(post_data["child_id"]),
            "month": str(date_menu.month),
            "year": date_menu.year,
            "school_implantation_id": post_data["school_implantation_id"][0],
            "meals": [
                {
                    "date": meal["date"],
                    "activity_id": meal["activity_id"],
                    "meal_ids": [meal["meal_id"]],
                }
                for meal in post_data["meals"]
            ],
        }
        url = f"{self.server_url}/{self.aes_instance}/menus/registration"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

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

    ###################
    ### Fiche santé ###
    ###################

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
        display_category="Fiche santé",
    )
    def read_healthsheet(self, request, child_id):
        url = f"{self.server_url}/{self.aes_instance}/kids/{child_id}/healthsheet"
        response = self.session.get(url)
        return response.json()[0]

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
        origin_data = json_loads(request.body)
        put_data = dict()
        if origin_data["activity_no_available_reason"]:
            put_data["activity_no_available_reason"] = origin_data[
                "activity_no_available_reason"
            ]
        if origin_data["allergy_consequence"]:
            put_data["allergy_consequence"] = origin_data["allergy_consequence"]
        if origin_data["allergy_ids"]:
            put_data["allergy_ids"] = origin_data["allergy_ids"]
        if origin_data["blood_type"]:
            put_data["blood_type"] = origin_data["blood_type"]
        if origin_data["child_id"]:
            put_data["child_id"] = origin_data["child_id"]
        if origin_data["doctor_id"]:
            put_data["doctor_id"] = origin_data["doctor_id"]
        if origin_data["facebook"]:
            put_data["facebook"] = origin_data["facebook"]
        if origin_data["first_date_tetanus"]:
            put_data["first_date_tetanus"] = origin_data["first_date_tetanus"]
        if origin_data["last_date_tetanus"]:
            put_data["last_date_tetanus"] = origin_data["last_date_tetanus"]
        if origin_data["level_handicap"]:
            put_data["level_handicap"] = origin_data["level_handicap"]
        if origin_data["other_allergies"]:
            put_data["other_allergies"] = origin_data["other_allergies"]
        if origin_data["other_diseases"]:
            put_data["other_diseases"] = origin_data["other_diseases"]
        if origin_data["photo"]:
            put_data["photo"] = origin_data["photo"]
        if origin_data["photo_general"]:
            put_data["photo_general"] = origin_data["photo_general"]
        if origin_data["self_medication"]:
            put_data["self_medication"] = origin_data["self_medication"]
        if origin_data["swim"]:
            put_data["swim"] = origin_data["swim"]
        if origin_data["swim_level"]:
            put_data["swim_level"] = origin_data["swim_level"]
        # if origin_data["to_go_alone"]:
        #     put_data["to_go_alone"] = origin_data["to_go_alone"]
        if origin_data["type_handicap"]:
            put_data["type_handicap"] = origin_data["type_handicap"]

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
                            "quantity": int(medication[1]),
                            "period": medication[2],
                            "self_medication_selection": medication[3],
                        }
                    )
            elif "contact" in key:
                contact = value.split(" ; ")
                allowed_contact_ids.append(
                    {"partner_id": int(contact[0]), "parental_link": contact[1]}
                )
        disease_ids = [
            {
                "disease_type_id": int(disease_id[1]),
                "gravity": origin_data.get(f"disease_{disease_id[0]}_gravity"),
                "disease_text": origin_data.get(f"disease_{disease_id[0]}_treatment"),
            }
            for disease_id in enumerate(origin_data["disease_ids"])
        ]
        if medication_ids:
            put_data["medication_ids"] = medication_ids
        if allowed_contact_ids:
            put_data["allowed_contact_ids"] = allowed_contact_ids
        if disease_ids:
            put_data["disease_ids"] = disease_ids
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
                    {"id": choice["id"], "text": choice["name"]} for choice in v
                ]
        return result

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
        post_data = json_loads(request.body)
        url = f"{self.server_url}/{self.aes_instance}/contacts"
        contact = {
            "firstname": post_data["firstname"],
            "lastname": post_data["lastname"],
            "phone": post_data["phone"],
            "mobile": post_data["mobile"] or "",
            "street": post_data["street"],
            "is_company": False,
            "locality_id": int(post_data["locality_id"]),
            "country_id": int(post_data["country_id"]),
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
        post_data = json_loads(request.body)
        url = f"{self.server_url}/{self.aes_instance}/doctors"
        doctor = {
            "firstname": post_data["firstname"],
            "lastname": post_data["lastname"],
            "phone": post_data["phone"],
            "mobile": post_data["mobile"] or "",
            "street": post_data["street"],
            "is_company": False,
            "locality_id": int(post_data["locality_id"]),
            "country_id": int(
                post_data["country_id"]
            ),  # self.search_country(post_data["country"])["id"],
            "zip": post_data.get("zipcode") or "",
            "city": post_data.get("city") or "",
        }
        # if post_data["country"].lower() == "belgique":
        #     doctor["locality_id"] = self.search_locality(
        #         post_data["zipcode"], post_data["locality"]
        #     )["id"]
        # else:
        #     doctor["zip"] = post_data["zipcode"]
        #     doctor["city"] = post_data["locality"]
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
