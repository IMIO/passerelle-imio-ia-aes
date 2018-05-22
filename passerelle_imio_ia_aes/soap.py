# Passerelle - uniform access to data and services
# Copyright (C) 2015  Entr'ouvert
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

# borrowed from https://pypi.python.org/pypi/suds_requests
# and https://docs.oracle.com/cd/E50245_01/E50253/html/vmprg-soap-example-authentication-python.html


import requests
import StringIO

from suds.client import Client
from suds.transport.http import HttpAuthenticated
from suds.transport import Reply
from suds.plugin import MessagePlugin, DocumentPlugin

from suds.sudsobject import asdict


class Filter(MessagePlugin):

    def marshalled(self, context):
        context.envelope.set('xmlns:xm', 'http://www.w3.org/2005/05/xmlmime')

    def received(self, context):
        reply = context.reply
        context.reply = reply[reply.find("<?xml version"):reply.rfind(">") + 1]

class Handlewsdl(DocumentPlugin):

    def loaded(self, context):
        # unknown types, so present them as strings
        context.document = context.document.replace('type="iph:DossierID"', 'type="xsd:string"')
        context.document = context.document.replace('type="iph:TypeTechnique"', 'type="xsd:string"')


class Transport(HttpAuthenticated):
    def __init__(self, model, **kwargs):
        self.model = model
        HttpAuthenticated.__init__(self, **kwargs)

    def get_requests_kwargs(self):
        kwargs = {}
        if self.model.username:
            kwargs['auth'] = (self.model.username, self.model.password)
        if self.model.keystore:
            kwargs['cert'] = (self.model.keystore.path, self.model.keystore.path)
        if not self.model.verify_cert:
            kwargs['verify'] = False
        return kwargs

    def open(self, request):
        # only use our custom handler to fetch service resources, not schemas
        # from other namespaces
        if 'www.w3.org' in request.url:
            return HttpAuthenticated.open(self, request)
        resp = self.model.requests.get(request.url, headers=request.headers,
                **self.get_requests_kwargs())
        return StringIO.StringIO(resp.content)

    def send(self, request):
        request.message = request.message.replace("contentType", "xm:contentType")
        self.addcredentials(request)
        resp = self.model.requests.post(request.url, data=request.message,
                headers=request.headers, **self.get_requests_kwargs())
        return Reply(resp.status_code, resp.headers, resp.content)

# plugins=[Handlewsdl(), Filter()]
def get_client(instance):
    transport = Transport(instance)
    return Client(instance.wsdl_url, transport=transport, cache=None)
