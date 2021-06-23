Changelog
=========

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
