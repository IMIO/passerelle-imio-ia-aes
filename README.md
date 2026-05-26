# passerelle-imio-ia-aes

Connecteur [Passerelle](https://doc-publik.entrouvert.com/dev/developpement-d-un-connecteur/) permettant à [Publik](https://www.publik.love/) (Téléservices, w.c.s.) de dialoguer avec **iA.AES** — la solution iMio de gestion des accueils extra-scolaires — via la passerelle d'API **APIMS**.

Concrètement, le connecteur expose au catalogue Publik des endpoints HTTP qui relaient les opérations métier (parents, enfants, plaines de vacances, repas, fiches santé, paiements, soldes, etc.) vers APIMS, et applique au passage la logique propre au Portail Parent (calcul du montant à payer, réservation de solde, validation de fiche santé…).

## Installation

Ajouter l'application aux apps installées de Passerelle :

```python
INSTALLED_APPS += ('passerelle_imio_ia_aes',)
```

Activer le module :

```python
PASSERELLE_APP_PASSERELLE_IMIO_IA_AES_ENABLED = True
```

Le package est compatible avec Django 3.2 à 5.2.

## Configuration

Créer un nouveau connecteur « Connecteur Apims AES » dans l'interface d'administration de Passerelle et renseigner :

| Champ          | Description                                              |
| -------------- | -------------------------------------------------------- |
| `server_url`   | URL du serveur APIMS                                     |
| `username`     | Utilisateur APIMS (basic auth)                           |
| `password`     | Mot de passe APIMS                                       |
| `aes_instance` | Instance iA.AES à contacter (ex. `fleurus`)              |

Côté Publik, le connecteur s'appuie sur `settings.KNOWN_SERVICES` pour retrouver les services **w.c.s.** (récupération de schémas de formulaires, listing des demandes d'un usager) et **authentic** (mise à jour de l'`aes_id` d'un utilisateur après fusion).

## Endpoints

Les endpoints sont regroupés par catégorie d'affichage dans l'interface Passerelle. Voici les principaux domaines couverts :

- **Test** — vérification de la connexion APIMS ↔ Publik
- **Données génériques** — pays, niveaux scolaires, lieux d'accueil,
  implantations scolaires, catégories d'activité
- **Localités** — recherche et listing de localités belges
- **Personne / Parent / Enfant** — création, lecture, recherche et
  mise à jour, ainsi que la page d'accueil agrégée du Portail Parent
- **Responsabilités** — déclaration parent facturable / attestable
- **Plaines** — inscription et désinscription aux plaines de vacances,
  calcul du coût
- **Repas** — menus mensuels, inscriptions / désinscriptions aux repas
  scolaires, gestion du délai limite
- **Fiche santé** — référentiel de questions, lecture et validation
- **Médecin / Contact** — données complémentaires liées à la fiche santé
- **Activités génériques / Journées pédagogiques / Mercredis après-midi**
- **Calcul du montant à payer / Solde / Paiement** — solde par catégorie
  d'activité, réservation de solde, encodage de paiements
- **WCS** — listing des formulaires de la catégorie Portail Parent
- **Utilitaires**

La liste exhaustive (URL, paramètres, exemples) est visible directement dans l'interface d'administration du connecteur une fois celui-ci créé.

## Tests

Lancer les tests unitaires :

```bash
DJANGO_SETTINGS_MODULE=passerelle.settings PASSERELLE_SETTINGS_FILE=tests/settings.py pytest tests/
```

En adaptant le chemin de `pytest` selon l'environnement virtuel utilisé, par exemple `~/envs/publik-env-py3/bin/pytest`.

À ce jour la suite ne teste qu'une fonction utilitaire pure (`compute_amount_with_balance`) qui n'a aucune dépendance Django : en pratique `pytest tests/` sans les variables d'environnement suffit. La forme complète ci-dessus est néanmoins conservée parce qu'elle suit la [convention Passerelle](https://doc-publik.entrouvert.com/dev/developpement-d-un-connecteur/#Tests-unitaires) et qu'elle sera requise dès qu'un test touchera au framework (modèles Django, endpoints HTTP via `django-webtest`, accès base de données…).

## Licence

AGPL-3.0-or-later — voir l'en-tête des fichiers source.
