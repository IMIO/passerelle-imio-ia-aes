
try:
    import xmlrpc.client
    from xmlrpc.client import ServerProxy
except ImportError:
    import xmlrpclib
    # noinspection PyCompatibility
    from xmlrpclib import ServerProxy

SERVER = 'https://stagingv9-aes.imio.be' #'http://192.168.7.187:8069'
DATABASE = 'stagingv9_extraschool' #'aes_hannut'
USERNAME = 'admin'
PASSWORD = 'admin'

# info = xmlrpclib.ServerProxy('{}/start'.format(SERVER)).start()


server = ServerProxy('{}/xmlrpc/2/common'.format(SERVER))
import ipdb;ipdb.set_trace()
user_id = server.authenticate(DATABASE, USERNAME, PASSWORD, {})

server = ServerProxy('{}/xmlrpc/object'.format(SERVER))
user_ids = server.execute(
    DATABASE, user_id, PASSWORD,
    'res.users', 'search', []
)

users = server.execute(
    DATABASE, user_id, PASSWORD,
    'res.users', 'read', user_ids, []
)

for user in users:
    print(user['id'], user['name'])

str_hello_world = server.execute(
    DATABASE, user_id, PASSWORD,
    'extraschool.parent', 'helloworld', [{'anus':'dtc'}]
)

print(str_hello_world)
