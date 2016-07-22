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

"""This module implements the VPN command line tool."""
from vpns import config, server
from vpns.endpoint import VpnProject, store_certificates

import inspect
import json
import os
import requests
import sys
import urllib
import schema

from functools import wraps

command_dict = {}
usage_dict = {}
MIN_PORT_NUMBER = 1
MAX_PORT_NUMBER = 2**16 - 1

def cmd(f):
    """A decorator for CLI commands.

    This decorator firstly adds the function to a dictionary of valid CLI
    commands, secondly adds exception handling for when the user passes the
    wrong number of arguments, and thirdly generates a 'usage' description and
    puts it in the usage dictionary.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except TypeError:
            # TODO TypeError is probably too broad here.
            sys.stderr.write('Invalid arguements.  Usage:\n')
            help(f.__name__)
    command_dict[f.__name__] = wrapped
    def get_usage(f):
        args, varargs, _, _ = inspect.getargspec(f)
        showee = [f.__name__] + ['<%s>' % name for name in args]
        args = ' '.join(['<%s>' % name for name in args])
        if varargs:
            showee += ['<%s...>' % varargs]
        return ' '.join(showee)
    usage_dict[f.__name__] = get_usage(f)
    return wrapped


def check_status_code(response):
    if response.status_code < 200 or response.status_code >= 300:
        sys.stderr.write('Unexpected status code: %d\n' % response.status_code)
        sys.stderr.write('Response text:\n')
        sys.stderr.write(response.text + "\n")
    else:
        sys.stdout.write(response.text + "\n")

# TODO: This function's name is no longer very accurate.  As soon as it is
# safe, we should change it to something more generic.
def object_url(*args):
    # Prefer an environmental variable for getting the endpoint if available.
    url = os.environ.get('HVPN_ENDPOINT')

    for arg in args:
        url += '/' + urllib.quote(arg,'')
    return url

def do_request(fn, url, data={}):
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

def do_put(url, data={}):
    return do_request(requests.put, url, data=json.dumps(data))

def do_post(url, data={}):
    return do_request(requests.post, url, data=json.dumps(data))

def do_get(url, data={}):
    return do_request(requests.get, url, data=json.dumps(data))

def do_delete(url, data={}):
    return do_request(requests.delete, url, data=json.dumps(data))

@cmd
def serve(port):
    try:
        port = schema.And(schema.Use(int), lambda n: MIN_PORT_NUMBER <= n <= MAX_PORT_NUMBER).validate(port)
    except schema.SchemaError:
	sys.exit('Error: Invaid port. Must be in the range 1-65535.')
    except Exception as e:
	sys.exit('Unxpected Error!!! \n %s' % e)

    """Start the VPN API server"""
    # We need to import api here so that the functions within it get registered
    # (via `rest_call`), though we don't use it directly:
    from haas import rest
    from vpns import api
    server.init()
    rest.serve(port, debug=True)


@cmd
def list_vpns():
    """List all vpn endpoints"""
    url = object_url('vpns')
    check_status_code(do_get(url))

@cmd
def vpn_create(project, network):
    """Create a vpn for <project, network>"""
    url = object_url('vpn', project)
    response = do_put(url, data={'network' : network})
    sys.stderr.write('status: %d\n' % response.status_code)
    sys.stderr.write('text: %s\n' % response.text)

@cmd
def vpn_destroy(project, network):
    """Delete vpn for <project, network>"""
    url = object_url('vpn', project)
    check_status_code(do_delete(url, data={'network' : network}))

@cmd
def get_vpn_certificates(project, network):
    """Get client specific data about a vpn endpoint"""
    url = object_url('vpn', project)
    response = do_get(url, data={'network' : network})
    if response.status_code < 200 or response.status_code >= 300:
        sys.stderr.write('Unexpected status code: %d\n' % response.status_code)
        sys.stderr.write('Response text:\n')
        sys.stderr.write(response.text + "\n")
        return

    sys.stderr.write("response.text: <%s>\n" % response.text)
    certs = json.loads(response.text)
    store_certificates(certs)
    

@cmd
def help(*commands):
    """Display usage of all following <commands>, or of all commands if none are given"""
    if not commands:
        sys.stdout.write('Usage: %s <command> <arguments...> \n' % sys.argv[0])
        sys.stdout.write('Where <command> is one of:\n')
        commands = sorted(command_dict.keys())
    for name in commands:
        # For each command, print out a summary including the name, arguments,
        # and the docstring (as a #comment).
        sys.stdout.write('  %s\n' % usage_dict[name])
        sys.stdout.write('      %s\n' % command_dict[name].__doc__)


def main():
    """Entry point to the CLI.

    There is a script located at ${source_tree}/scripts/haas, which invokes
    this function.
    """
    config.setup()

    if len(sys.argv) < 2 or sys.argv[1] not in command_dict:
        # Display usage for all commands
        help()
    else:
        command_dict[sys.argv[1]](*sys.argv[2:])
