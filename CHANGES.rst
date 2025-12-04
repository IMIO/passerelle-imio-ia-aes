Changelog
=========

3.0.3
-----------------

- [PP-668] Fixed: due amount and spent balance for meals.
- [PP-669] Fixed: fetch meal registrations for next year.

3.0.2
-----------------

- [PP-661] Added: get-forms return can be a list of slugs.

3.0.1
-----------------

- [PP-662] Fix: manage empty string as None to create reserving balance for meals

3.0.0
-----------------

- [PP-587] Add endpoint get_activity_categories
- [PP-588] Add 'transaction_id' for generic_create_payment
- [PP-593] Add list_certificates endpoint
- [PP-595] Adapt get_forms with multiple keywords 
- [PP-604] Add pay_invoice endpoint
- [PP-608] Add list_pedagogicals_days
- [PP-609] Add create_pedagogicals_days_inscriptions & list_pedagogical_days_per_dates
- [PP-614] Add compute_childcare_amount endpoint
- [PP-634] Add comments into compute_meals_order_amount.
- [PP-635] Add delete_pedagogical_registration def
- [PP-612] Add read_pedagogical_registrations def
- [PP-608] Add list_pedagogical_days date filtering
- [PP-656] Add get_wednesday_afternoon def


2.2.0
-----------------

- [PP-589] Add endpoint get_all_balances_for_parent

2.1.10
-----------------

- [SUP-44639] Return parent_id in get_balance response
- [SUP-44639] Add some comments to explain get_balance

2.1.9
-----------------

- [PP-562] Fix options that trigger price category computing when updating personnal data

2.1.8
-----------------

- [SUP-42572] Round computed amount in school meals.

2.1.7
-----------------

- [PP-542] Add endpoint to read translated country.
- [SUP-41782] Set end_date as friday in plain registrations.

2.1.6
-----------------

- [PP-535] Replace healthsheet diseases fields with fields bloc
- [PP-535] Replace healthsheet allergies fields with fields bloc
- [PP-535] Replace healthsheet medications fields with fields bloc
- [PP-535] Disable "new diseases" from questions as it is always True

2.1.5
-----------------

- [MPP-517] Use isocalendar for date selection when creating plain registrations.

2.1.4
-----------------

- [MPP-505] Fix various typo in healthsheet's questions.

2.1.3
-----------------

- [AES-1793] Split payments over activity categories and invoiceable parents.

2.1.2
-----------------

- [SUP-39366] Adapt to change in WCS API

2.1.1
-----------------

- [TELE-1939] Fix get balance parameters
- [TELE-1939] Remove logging

2.1.0
-----------------

- [MPP-149] Add online payment for meals.
- [MPP-499] Manage parent's balance for meal online payments

2.0.1
-----------------
- [MPP-484] Added: caching some endpoints.

2.0.0
-----------------
- [MPP-476] Added: child's price category can depend of his school implantation.
- [AES-1559] Fixed: remove unused field.
- [MPPNIVA-9][MPPNIVA-10] Added: update person endpoint.
- [MPP-478] Added: is_disabled key on meal registrations and meal menu endpoints.
- [MPP-478] Added: filter by parent on meal registrations sent to AES
- [MPP-466] Updated: check delay and insert it in disabled in inscriptions of a child
- [MPP-466] Updated: don't send meal registrations post if nothing to post
- [MPP-480] Fixed: cast str into int for proper comparison in homepage's method
- [MPP-467] Updated: add invoiceable parents in parent's children
- [MPP-391] Added: get invoiceable parent in homepage's data
- [MPPNIVA-9][MPPNIVA-10] Added: management of child and parent update forms in homepage's data
- [MPP-391] Added: management of becoming invoiceable form in homepage's data
- [MPP-391] Added: update responsibility patch method
- [MPP-391] Added: responsibility's id per child when listing them for a parent
- Fix endpoint description.

1.9.2
-----------------
- [MPP-468] Fixed: order of available plain's weeks

1.9.1
-----------------
- [MPP-454] Fixed: ask wcs only once for school implantations offering meals"
- Revert Development Status

1.9.0
-----------------
- [MPP-454] Added: school meals related forms appeared if the right school is checked in pp-repas-scolaires form options or all schools are unchecked
- black

1.8.6
-----------------
- [MPP-452] Fixed: meals unregistrations retake working days into account.

1.8.5
-----------------
- [MPP-450] Added: raise exception if search localities return an empty list

1.8.4
-----------------
- [MPP-446] Added: use new homepage endpoint from aes-api

1.8.3
-----------------
- [MPP-447] Fixed: explicitely remove allergies consequences and their treatment if no allergies nor other allergies

1.8.2
-----------------
- [MPP-447] Added: set empty list of allergies instead of NoneType
- [MPP-447] Fixed: explicitely remove data about allergies consequences and treatment if no allergies

1.8.1
-----------------
- [MPP-444] Fixed: send gravity and treatment for other diseases if no diseases_ids are checked

1.8.0
-----------------
- [MPP-444] Added: allergies endpoint using allergies aes-api endpoint
- [MPP-444] Changed: diseases endpoint to use diseases aes-api endpoint
- [MPP-444] Added: healthsheet id to child healthsheet endpoint
- [MPP-444] Added: send other allergies and diseases to iA.AES

1.7.6
-----------------
- [MPP-443] Changed: invalidate healthsheet after 30 days instead of 183

1.7.5
-----------------
- [MPP-441] Added: text with zipcode and locality name.

1.7.4
-----------
- [MPP-435] Added: get child medications
- [MPP-435] Added: defined has_medication field items and child's related value
- [MPP-435] Removed: child self medication, which does not exist in healthsheet forms

1.7.3
----------------
- [MPP-432] Fixed: send allergy_ids as list of int when updating healthsheet [nhi]

1.7.2
----------------
- Changed: manage optional and mandatory authorizations separatly [nhi]

1.7.1
----------------
- Added: filter optional or mandatory authorizations [nhi]

1.7.0
----------------
- Added: allergy treatment, bike, emotional support, hearing aid, glasses, mutuality, nap and weight in child's healthsheet's data [nhi]
- Added: get authorizations for healthsheet fields [nhi]
- Added: authorizations in child's healthsheet's data [nhi]
- Changed: use Passerelle for healthsheet questions [nhi]
- Fixed: allergy consequences in healthsheet [nhi]

1.6.0
----------------
- Added: rewrite parent's aes_id in case of merge in iA.AES. [nhi]

1.5.0
----------------
- Added: is parent has pending plains registrations in homepage [nhi]

1.4.0
-----------------
- Added: fetch parent's structured communication for holiday plains [nhi]

1.3.2
-----------------
- Changed: be less strict in zipcode recognition when searching localities [nhi]

1.3.1
-----------------
- Changed: deadline for meal unregistration can now be current day [nhi]

1.3.0
-----------------
- Added: tool for getting age group birthdates [nhi]

1.2.1
-----------------
- Fixed: monday computing in plains [nhi]

1.2.0
-----------------
- Added: add deadline to meal unregistration endpoint [nhi]

1.1.0
-----------------
- Added: unregistration endpoint [nhi]
- Updated: meals endpoints [nhi]

1.0.0
-----------------
- Added: new version for AESv15
- Added: read parent, healthsheets, children, available plains, parent's invoices
- Added: list wcs pp forms
- Added: create homepage
  [nhi]

0.2.19
-----------------
- Added : children filtering by school
  [nhi]

0.2.18
-----------------
- set author to iA.Teleservices team
- set home page
- set version in setup.py
- use iateleservicesCreateDeb pipeline function
- set install path to jenkinsfile
  [nhi]

0.2.17
-----------------
- [INFRA-4003] [TELE-1119] add -k to avoid SSL error following the Infra advice about that
  [dmshd]

0.2.16
-----------------
- create migration 0002

0.2.15
-----------------
- do not assume input parameters are given when getting parent's children
- do not assume input parameters are given when reaching for plaines
  [nhi]

0.2.14
-----------------
- clean workspace after successful build
  [nhi]

0.2.13
-----------------
- set django requirement from 1.11 to 2.3
- do not auto build dependencies
  [nhi]

0.2.12
-----------------
- set django requirement from 1:1.11 to 2:2.3
  [nhi]

0.2.11
-----------------
- force fpm to use python3
  [nhi]

0.2.10
-----------------
- try with python3 and django 2.2 as required
  [nhi]

0.2.9
-----------------
- get parent's invoices from AES with parent's rn
  [nhi]

0.2.8
-----------------
- update versionning scheme to remove letters
  [nhi]

0.2.7w
-----------------
- get activity_name instead of False if AES throw no theme
  [nhi]


0.2.7v
-----------------
- fix comma
  [nhi]

0.2.7u
-----------------
- display monday's in response when getting plains
  [nhi]

0.2.7t
-----------------
- display monday's in response when registering a child to plains
  [nhi]
  
0.2.7s
-----------------
- securizing get plains if there is no theme
  [nhi]

0.2.7r
-----------------
- remove copied pasted code
- upgrade get_raw_plaines for easier testing
  [nhi]

0.2.7q
-----------------
- display plain's theme if existing, else display plain's name
  [nhi]

0.2.7p
-----------------
- return aes response instead of true when validating plains
  [nhi]

0.2.7n
-----------------
- import json
  [nhi]

0.2.7m
------------------
- send structured child registration to plain data to AES
  [nhi]

0.2.7l
------------------
- reformat data from aes for get_plaines_v2
  [nhi]

0.2.7k
------------------
- add get_plaines_v2 which get correctly structured data
  [nhi]

0.2.7j
------------------
- rename tst_connexion to test_connexion
  [nhi]

0.2.7i
------------------
- [MPPCAUA-60] Ask AES if a child already exist, based on his RN
  [nhi]

0.2.7h
------------------
- [MPPCAUA-50] add method to get the meals of a child
  [nhi]

0.2.7g
------------------
- [TELE-695] use passerelle json_loads to prevent conversion errors
  [dmu]

0.2.7f
------------------

- [MPPCAUA-41] new method to get children with parent's nrn
  [nhi]

0.2.7e
------------------

- Fix encoding (python3)
  [boulch]

0.2.7d
------------------

- Fix some python3 import and lib.
  [boulch]

0.2.7c
------------------

- Fix test_connexion endpoint
  [boulch]

  0.2.7b
------------------

- Fix models to python3 compatibility and drop python2 : import xmlrpc and object to list

0.2.7a
------------------

- Adapt Jenkinsfile to install package python3/dist-package instead of python2

0.2.5a
------------------

- Adapt package name and build-depends and debian/rules for Passerelle Python 3

0.2.4a
------------------

- change install requirement from 'passerelle' to 'python3-passerelle' in setup.py
- change programming language in setup.py
- adapt dependencies in ./debian/control

0.2.2r
------------------

- firsts commits and only python2.x


0.0.3a
------------------

- Fix imports for python3 AND python2 compatibily.
