# 2016 Massachusetts Open Cloud Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the
# License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS
# IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.  See the License for the specific language
# governing permissions and limitations under the License.

""" VPN Endpoint state. """

from haas.errors import *
from vpns.hilclient import list_project_nodes, show_node

import os
from os.path import expanduser

import logging

logger = logging.getLogger(__name__)

VpnProject = 'VPN_project'
Endpoints = []
Nodes = []

class VpnEndpoint:
    cert_path = '/etc/openvpn/'
    cert_base = 'certs'
    lock_file = 'lock'

    def __init__(self, project, network, channel='null'):
        self.key = project
        self.id = 1
        self.network = network
        self.channel = channel
        self.vpn  = -1
        self.node = None
        self.nic  = None

    def __init__(self, id):
        self.key = id
        self.project = 'NONE'
        self.network = 'NONE'
        self.channel = -1
        self.vpn  = -1
        self.node = 'NONE'
        self.nic  = None

    def getwd(self):
        return os.path.join(self.cert_path,
                            self.cert_base + '.' + str(self.key))

    def load_certificates(self):
        certdir = self.getwd()
        certs = {}
        try:
            with open(os.path.join(certdir, 'ca.crt')) as f:
                certs['ca_crt'] = f.read()

            clientbase = 'client' + str(clientid)
            with open(os.path.join(certdir, clientbase + '.crt')) as f:
                certs['client_crt'] = f.read()

            with open(os.path.join(certdir, clientbase + '.key')) as f:
                certs['client_key'] = f.read()
        except:
            raise

        return certs

    def claim(self):
        certdir = self.getwd()
        try:
            with open(os.join(certdir, self.lock_file), 'r+') as f:
                rawdata = f.read()
                owner = json.loads(rawdata)
                if owner['node'] is not 'NONE':
                    raise ProjectMismatchError("endpoint is already claimed")

                owner = { 'node' : self.node, 'network' : self.network }
                f.write(json.dumps(owner))
        except:
            raise

    def unclaim(self):
        certdir = getwd()
        try:
            with open(os.join(certdir, self.lock_file), 'r+') as f:
                rawdata = f.read()
                owner = json.loads(rawdata)
                if owner['node'] is not self.node:
                    raise ProjectMismatchError("not endpoint owner!")

                owner = { 'node' : 'NONE', 'network' : 'NONE' }
                f.write(json.dumps(owner))
        except:
            raise
        
    def findOwner(self):
        certdir = self.getwd()
        try:
            with open(os.path.join(certdir, self.lock_file), 'r') as f:
                rawdata = f.read()
                owner = json.loads(rawdata)
                self.node = owner['node']
                self.network = owner['network']
        except:
            raise


def store_certificates(certs):
    """ Note: this is run on the client, not the server
    """
    certdir = os.path.join(expanduser('~'), '.openvpn')
    try:
        os.makedirs(certdir)
    except OSError:
        if not os.path.isdir(certdir):
            sys.stderr.write("Can't create directory %s\n" % certdir)
            return

    try:
        with open(os.path.join(certdir, 'ca.crt'), 'w') as f:
            f.write(certs['ca_crt'])

        with open(os.path.join(certdir, 'client.crt'), 'w') as f:
            f.write(certs['client_crt'])

        with open(os.path.join(certdir, 'client.key'), 'w') as f:
            f.write(certs['client_key'])
    except OSError as e:
            sys.stderr.write("Can't write file %s: %s\n" % certdir, str(e))
    

class VpnNode:
    def __init__(self, name):
        self.key = name
        self.used_nics = []
        self.free_nics = []

    def register_nic(self, nic):
        if nic in self.free_nics:
            raise DuplicateError(nic)
        if nic in self.used_nics:
            raise DuplicateError(nic)
        self.free_nics.append(nic)

    def allocate_nic(self):
        nic = self.free_nics.pop()
        if nic is not None:
            self.used_nics.append(nic)
        return nic


def init_nodes():
    """ select an unused node off the vpn's project list """
    global VpnProject
    if VpnProject is None:
        logging.warn("where did the VpnProject go?")
        VpnProject = 'VPN_project'

    response = list_project_nodes(VpnProject)
    if response.status_code < 200 or response.status_code >= 300:
        return

    # list_project_nodes returns a list of string names
    project_nodes = json.loads(response.text)
    for pn in project_nodes:
        node = VpnNode(pn)
        allocate_nics(node)
        Nodes.append(node)


def allocate_node():
    """ select an unused node off the vpn's project list """
    global VpnProject
    if VpnProject is None:
        logging.warn("where did the VpnProject go?")
        VpnProject = 'VPN_project'

    response = list_project_nodes(VpnProject)
    if response.status_code < 200 or response.status_code >= 300:
        return

    # list_project_nodes returns a list of string names
    project_nodes = json.loads(response.text)
    for pn in project_nodes:
        # Try to select a node that is not already on our list
        already_have_it = False
        for n in Nodes:
            if n.key == pn:
                already_have_it = True
                break
        if not already_have_it:
            break

def allocate_nics(node):
    """ register all the nics on the given node """
    response = show_node(node.key)
    if response.status_code < 200 or response.status_code >= 300:
        return

    details = json.loads(response.text)
    for nic in details['nics']:
        try:
            node.register_nic(nic['label'])
        except Exception as e:
            logging.error(e.msg)

