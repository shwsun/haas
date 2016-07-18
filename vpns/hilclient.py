# Copyright 2016 Massachusetts Open Cloud Contributors
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

"""This module implements the client calls to HIL."""

import inspect
import json
import os
import requests
import sys
import urllib
import schema

# TODO: This function's name is no longer very accurate.  As soon as it is
# safe, we should change it to something more generic.
def hilclient_url(*args):
    # Prefer an environmental variable for getting the endpoint if available.
    url = os.environ.get('HAAS_ENDPOINT')

    for arg in args:
        url += '/' + urllib.quote(arg,'')
    return url

def hilclient_request(fn, url, data={}):
    """Helper function for making HTTP requests against the API.

    Arguments:

        `fn` - a function from the requests library, one of requests.put,
               requests.get...
        `url` - The url to make the request to
        `data` - the body of the request.

    If the environment variables HAAS_USERNAME and HAAS_PASSWORD are
    defined, The request will use HTTP basic auth to authenticate, with
    the given username and password.
    """
    kwargs = {}
    username = os.getenv('HVPN_USERNAME')
    password = os.getenv('HVPN_PASSWORD')
    if username is not None and password is not None:
        kwargs['auth'] = (username, password)
    return fn(url, data=data, **kwargs)

def hilclient_put(url, data={}):
    return hilclient_request(requests.put, url, data=json.dumps(data))

def hilclient_post(url, data={}):
    return hilclient_request(requests.post, url, data=json.dumps(data))

def hilclient_get(url):
    return hilclient_request(requests.get, url)

def hilclient_delete(url, data={}):
    return hilclient_request(requests.delete, url, data=json.dumps(data))

def node_connect_network(node, nic, network, channel):
    """Connect <node> to <network> on given <nic> and <channel>"""
    url = hilclient_url('node', node, 'nic', nic, 'connect_network')
    return hilclient_post(url, data={'network': network, 'channel': channel})

def node_detach_network(node, nic, network):
    """Detach <node> from the given <network> on the given <nic>"""
    url = hilclient_url('node', node, 'nic', nic, 'detach_network')
    return hilclient_post(url, data={'network': network})


def node_register(node, subtype, *args):
    """Register a node named <node>, with the given type
	if obm is of type: ipmi then provide arguments
	"ipmi", <hostname>, <ipmi-username>, <ipmi-password>
    """
    obm_api = "http://schema.massopencloud.org/haas/v0/obm/"
    obm_types = [ "ipmi", "mock" ]
    #Currently the classes are hardcoded
    #In principle this should come from api.py
    #In future an api call to list which plugins are active will be added.

    if subtype in obm_types:
	if len(args) == 3:
	    obminfo = {"type": obm_api+subtype, "host": args[0],
	    		"user": args[1], "password": args[2]
	    	      }
	else:
	    raise BadArgumentError('Wrong number of arguments for subtype')
    else:
        raise BadArgumentError('Illegal OBM subtype: %s' % subtype)

    url = hilclient_url('node', node)
    return hilclient_put(url, data={"obm": obminfo})


def node_delete(node):
    """Delete <node>"""
    url = hilclient_url('node', node)
    return hilclient_delete(url)


def node_register_nic(node, nic, macaddr):
    """Register existence of a <nic> with the given <macaddr> on the given <node>"""
    url = hilclient_url('node', node, 'nic', nic)
    return hilclient_put(url, data={'macaddr':macaddr})


def node_delete_nic(node, nic):
    """Delete a <nic> on a <node>"""
    url = hilclient_url('node', node, 'nic', nic)
    return hilclient_delete(url)

def show_node(node):
    """Display information about a <node>"""
    url = hilclient_url('node', node)
    return hilclient_get(url)

def show_network(network):
    """Display information about <network>"""
    url = hilclient_url('network', network)
    return hilclient_get(url)

def list_project_nodes(project):
    """List all nodes attached to a <project>"""
    url = hilclient_url('project', project, 'nodes')
    return hilclient_get(url)




