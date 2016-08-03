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

    def __init__(self, id):
        self.key = id
        self.project = 'NONE'
        self.network = 'NONE'
        self.channel = -1
        self.node = 'NONE'
        self.clientid = 1
        self.nic  = None

    def getwd(self):
        return os.path.join(self.cert_path,
                            self.cert_base + '.' + str(self.key))

    def allocate(self, proj, node, net, nic, channel):
        self.project = proj
        self.node = node
        self.network = net
        self.nic  = nic
        self.channel = channel
        
    def release(self):
        self.node = 'NONE'
        self.network = 'NONE'

    def getVpnNode(self):
        for n in Nodes:
            if n.key == self.node:
                return n

    def load_certificates(self):
        certdir = self.getwd()
        certs = {}
        try:
            with open(os.path.join(certdir, 'ca.crt')) as f:
                certs['ca_crt'] = f.read()

            clientbase = 'client' + str(self.clientid)
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
            with open(os.path.join(certdir, self.lock_file), 'r+') as f:
                rawdata = f.read()
                owner = json.loads(rawdata)
                if owner['node'] != 'NONE':
                    raise ProjectMismatchError(
                                         "endpoint is already claimed for node "
                                         + owner['node'])

                f.seek(0)
                owner = { 'project' : self.project, 
                          'node' : self.node, 
                          'network' : self.network }
                f.write(json.dumps(owner))
                f.truncate()
        except:
            raise

    def unclaim(self):
        certdir = self.getwd()
        try:
            with open(os.path.join(certdir, self.lock_file), 'r+') as f:
                rawdata = f.read()
                owner = json.loads(rawdata)
                if owner['node'] != self.node:
                    raise ProjectMismatchError("not endpoint owner!")

                f.seek(0)
                owner = { 'project' : 'NONE',
                          'node' : 'NONE',
                          'network' : 'NONE' }
                f.write(json.dumps(owner))
                f.truncate()

                self.allocate('NONE', 'NONE', 'NONE', 'NONE', 'NONE') 
        except:
            raise
        
    def findOwner(self):
        certdir = self.getwd()
        try:
            with open(os.path.join(certdir, self.lock_file), 'r') as f:
                rawdata = f.read()
                owner = json.loads(rawdata)
                self.project = owner['project']
                self.node = owner['node']
                self.network = owner['network']
        except:
            raise

def find_unused_endpoint():
    """ Finds an unclaimed endpoint."""
    for ep in Endpoints:
        if ep.node == 'NONE':
            return ep


def store_certificates(certs):
    """ Note: this is run on the client, not the server """
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

class VpnNic:
    def __init__(self, name, nets):
        self.key = name
        self.networks = nets.copy()


class VpnNode:
    def __init__(self, name):
        self.key = name
        self.used_nics = []
        self.free_nics = []

    def find_nic(self, name):
        for n in self.free_nics:
            if n.key == name:
                return n
        for n in self.used_nics:
            if n.key == name:
                return n
        return None

    def find_network(self, net):
        """ return nic name and channel for network """
        for nic in self.used_nics:
            for chan, nw in nic.networks.iteritems():
                logging.info('find network: %s %s' % (chan, nw))
                if nw == net:
                   return nic.key, chan 
        return 'NONE', 'NONE'

    def register_nic(self, nic, networks):
        if self.find_nic(nic) is not None:
            raise DuplicateError(nic)
        if networks:
            n = VpnNic(nic, networks)
            self.used_nics.append(n)
        else:
            n = VpnNic(nic, {})
            self.free_nics.append(n)

    def allocate_nic(self):
        if self.free_nics:
            nic = self.free_nics.pop()
            self.used_nics.append(nic)
            return nic.key
        return None

    def release_nic(self, nic):
        for n in self.used_nics:
            if n.key == nic:
                self.used_nics.remove(n)
                self.free_nics.append(n)
                return
        raise IllegalStateError

    def show_nics(self):
        logging.info("used nics:")
        for n in self.used_nics:
            logging.info("unic: " + n.key)
        logging.info("free nics:")
        for n in self.free_nics:
            logging.info("fnic: " + n.key)
        
def vpn_project_nodes():
    """ select an unused node off the vpn project list """
    global VpnProject
    if VpnProject is None:
        logging.warn("where did the VpnProject go?")
        VpnProject = 'VPN_project'

    response = list_project_nodes(VpnProject)
    if response.status_code < 200 or response.status_code >= 300:
        return []

    # list_project_nodes returns a list of string names
    project_nodes = json.loads(response.text)
    return project_nodes

def allocate_node():
    """ Look for an unused/new node in the project pool. By "new" we mean
    a node not in the local list of Nodes. This is likely a node that has
    been provisioned after the server started. """

    already_have_it = True
    project_nodes = vpn_project_nodes()
    for pn in project_nodes:
        # Try to select a node that is not already on our list
        already_have_it = False
        for n in Nodes:
            if n.key == pn:
                already_have_it = True
                break # from inner for
        if not already_have_it:
            break # from outer for

    if not already_have_it:
        node = VpnNode(pn)
        register_nics(node)
        Nodes.append(node)

def register_nics(node):
    """ register all the nics on the given node """
    response = show_node(node.key)
    if response.status_code < 200 or response.status_code >= 300:
        return

    details = json.loads(response.text)
    for nic in details['nics']:
        try:
            logging.info('register nic %s %r\n' % (nic['label'], nic['networks']))
            node.register_nic(nic['label'], nic['networks'])
        except Exception as e:
            logging.error(str(e))
            raise
