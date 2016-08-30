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

"""This module provides the VPN service's public API.

TODO: Spec out and document what sanitization is required.
"""
import json
import sys
import logging

from schema import Schema, Optional

from vpns.endpoint import *
from vpns.hilclient import (
    node_connect_network, node_detach_network, show_network)
#from vpns.endpoint import Endpoints as ep

from haas.auth import get_auth_backend
from haas.rest import rest_call
from haas.errors import (
    AllocationError, DuplicateError, ServerError, NotFoundError)


# Project Code #
################


@rest_call('GET', '/vpns', Schema({}))
def list_vpns():
    """List all VPN endpoints.

    Returns a JSON array of strings representing a list of <project,channel>
    tuples.

    Example:  '[{"project": "proj", "network": {
                                        "name": "net", "channel": "chann"}
                {"project": "myproj", "network": {
                                        "name": "mynet", "channel": "chann"}}]'
    """
    get_auth_backend().require_admin()
    vpns = [{'id': ep.key,
             'project': ep.project,
             'network': {
                 'name': ep.network,
                 'channel': ep.chann
             },
             'node': ep.node,
             'nic': ep.nic} for ep in Endpoints]
    return json.dumps(vpns)


@rest_call('PUT', '/vpn/<project>', Schema({'project': basestring,
                                            'network': basestring}))
def vpn_create(project, network, channel):
    """Create a VPN for <project, network, channel>.

    If the VPN already exists, a DuplicateError will be raised.
    """
    get_auth_backend().require_admin()
    _assert_absent(project, network)

    ep = find_unused_endpoint()

    if not Nodes:
        allocate_node()

    # find a free nic
    nic = None
    for node in Nodes:
        node.show_nics()
        nic = node.allocate_nic()
        if nic is not None:
            break

    if nic is None:
        raise AllocationError("No free NICs.")

    response = show_network(network)
    if response.status_code < 200 or response.status_code >= 300:
        logging.warn("show_network failed: %d" % response.status_code)
        return response.text, response.status_code

    properties = json.loads(response.text)
    # channels = properties['channels']

    ep.allocate(project, node.key, network, nic, channel)

    ep.claim()

    response = node_connect_network(node.key, nic, network, channel)
    if response.status_code < 200 or response.status_code >= 300:
        logging.warn("node_connect_network failed: %d" % response.status_code)
        ep.release()
        ep.unclaim()
        node.release_nic(nic)
        return response.text, response.status_code

    return '', 202


@rest_call('GET', '/vpn/<project>', Schema({'project': basestring,
                                            'network': basestring}))
def get_vpn_certificates(project, network):
    """Get the client related data for the given VPN for.

    If the project does not exist, a NotFoundError will be raised.
    """
    get_auth_backend().require_admin()
    ep = _must_find(project, network)

    try:
        result = ep.load_certificates()
    except Exception as e:
        raise ServerError("Internal File System Error: %s" % e)

    sys.stderr.write("key: %s\n" % result['ca_crt'])
    return json.dumps(result)


@rest_call('DELETE', '/vpn/<project>', Schema({'project': basestring,
                                               'network': basestring}))
def vpn_destroy(project, network):
    """Delete endpoint associated with <project,network>

    If the project does not exist, a NotFoundError will be raised.
    """
    get_auth_backend().require_admin()
    ep = _must_find(project, network)

    logging.info("detaching node " + ep.node + " nic " + ep.nic)
    node_detach_network(ep.node, ep.nic, network)

    for node in Nodes:
        if node.key == ep.node:
            node.release_nic(ep.nic)
            break

    ep.unclaim()


def _assert_absent(project, network):
    for ep in Endpoints:
        if project == ep.project and network == ep.network:
            raise DuplicateError(network)


def _must_find(project, network):
    for ep in Endpoints:
        if project == ep.project and network == ep.network:
            return ep

    raise NotFoundError("No VPN for project %s network %s."
                        % (project, network))


def _find_node(node):
    for n in Nodes:
        if n.key == node:
            return n

    raise NotFoundError("No node for %s registered." % node)
