import requests, base64, hmac, hashlib, datetime
import random
import urllib
try:
    import urlparse
except ImportError:
    from urllib.parse import urlparse
from hashlib import sha256
# https://git.entrouvert.org/wcs.git/tree/wcs/api_utils.py

# Doc Entr'ouvert : authentificaiton pour utiliser les apis.
# https://doc-publik.entrouvert.com/tech/wcs/api-webservices/authentification/

#  Doc Entr'ouvert : Récupération de coordonnées
# https://doc-publik.entrouvert.com/tech/wcs/api-webservices/recuperation-des-donnees-d-un-formulaire/

#  Doc Entr'ouvert : Evolution du workflow
# https://doc-publik.entrouvert.com/tech/wcs/api-webservices/traitement-d-un-formulaire/

algo = 'sha256'
timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
key = "yPWNGX3c9PHyf2Huuuac97MvS58ArCb8f8wnTWgYEKa732x3eeEJjDxEA83Fp5PT"
query_string = "https://demo-formulaires.guichet-citoyen.be/tests-et-bac-a-sable/demo-cb-aes/1/jump/trigger/validate"
orig = "aes"

def sign_url(url, key, orig, algo='sha256', timestamp=None, nonce=None):
    parsed = urlparse.urlparse(url)
    new_query = sign_query(parsed.query, key, orig, algo, timestamp, nonce)
    return urlparse.urlunparse(parsed[:4] + (new_query,) + parsed[5:])


def sign_query(query, key, orig, algo='sha256', timestamp=None, nonce=None):
    if timestamp is None:
        timestamp = datetime.datetime.utcnow()
    timestamp = timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
    if nonce is None:
        nonce = hex(random.getrandbits(128))[2:-1]
    new_query = query
    if new_query:
        new_query += '&'
    new_query += urllib.urlencode((
        ('algo', algo),
        ('orig', orig),
        ('timestamp', timestamp),
        ('nonce', nonce)))
    signature = base64.b64encode(sign_string(new_query, key, algo=algo))
    new_query += '&signature=' + urllib.quote(signature)
    return new_query

def sign_string(s, key, algo='sha256', timedelta=30):
    digestmod = getattr(hashlib, algo)
    hash = hmac.HMAC(key, digestmod=digestmod, msg=s)
    return hash.digest()

query_full = sign_url(query_string, key, orig)
print(requests.post(query_full))
