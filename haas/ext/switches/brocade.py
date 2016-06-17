# Copyright 2016 Massachusetts Open Cloud Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the
# License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS
# IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language
# governing permissions and limitations under the License.

"""A switch driver for Brocade NOS.

Uses the XML REST API for communicating with the switch.
"""

import logging
from lxml import etree
from os.path import dirname, join
import re
import requests
import schema

from haas.migrations import paths
from haas.model import db, Switch

paths[__name__] = join(dirname(__file__), 'migrations', 'brocade')

logger = logging.getLogger(__name__)


class Brocade(Switch):
    api_name = 'http://schema.massopencloud.org/haas/v0/switches/brocade'

    __mapper_args__ = {
        'polymorphic_identity': api_name,
    }

    id = db.Column(db.Integer, db.ForeignKey('switch.id'), primary_key=True)
    hostname = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    interface_type = db.Column(db.String, nullable=False)

    @staticmethod
    def validate(kwargs):
        schema.Schema({
            'hostname': basestring,
            'username': basestring,
            'password': basestring,
            'interface_type': basestring,
        }).validate(kwargs)

    def session(self):
        return self

    def disconnect(self):
        pass

    def apply_networking(self, action):
        """ Apply a NetworkingAction to the switch.

        Args:
            action: NetworkingAction to apply to the switch.
        """
        interface = action.nic.port.label
        channel = action.channel

        if channel == 'vlan/native':
            if action.new_network is None:
                self._remove_native_vlan(interface)
            else:
                self._set_native_vlan(interface,
                                      action.new_network.network_id)
        else:
            match = re.match(re.compile(r'vlan/(\d+)'), channel)
            assert match is not None, "HaaS passed an invalid channel to the switch!"
            vlan_id = match.groups()[0]

            if action.new_network is None:
                self._remove_vlan_from_trunk(interface, vlan_id)
            else:
                assert action.new_network.network_id == vlan_id
                self._add_vlan_to_trunk(interface, vlan_id)

    def get_port_networks(self, ports):
        """Get port configurations of the switch.

        Args:
            ports: List of ports to get the configuration for.

        Returns: Dictionary containing the configuration of the form:
        {
            Port<"port-3">: [("vlan/native", "23"), ("vlan/52", "52")],
            Port<"port-7">: [("vlan/23", "23")],
            Port<"port-8">: [("vlan/native", "52")],
            ...
        }

        """
        response = {}
        for port in ports:
            response[port] = filter(None, [self._get_native_vlan(port)]) \
                             + self._get_vlans(port)
        return response

    def _get_mode(self, interface):
        """ Return the mode of an interface.

        Args:
            interface: interface to return the mode of

        Returns: 'access' or 'trunk'

        Raises: AssertionError if mode is invalid.

        """
        url = self._construct_url(interface, suffix='mode')
        response = requests.get(url, auth=self._auth)
        root = etree.fromstring(response.text)
        mode = root.find(self._construct_tag('vlan-mode')).text
        return mode

    def _set_mode(self, interface, mode):
        """ Set the mode of an interface.

        Args:
            interface: interface to set the mode of
            mode: 'access' or 'trunk'

        Raises: AssertionError if mode is invalid.

        """
        if mode in ['access', 'trunk']:
            url = self._construct_url(interface, suffix='mode')
            payload = '<mode><vlan-mode>%s</vlan-mode></mode>' % mode
            requests.put(url, data=payload, auth=self._auth)
        else:
            raise AssertionError('Invalid mode')

    def _get_vlans(self, interface):
        """ Return the vlans of a trunk port.

        Does not include the native vlan. Use _get_native_vlan.

        Args:
            interface: interface to return the vlans of

        Returns: List containing the vlans of the form:
        [('vlan/vlan1', vlan1), ('vlan/vlan2', vlan2)]
        """
        try:
            url = self._construct_url(interface, suffix='trunk')
            response = requests.get(url, auth=self._auth)
            root = etree.fromstring(response.text)
            vlans = root.\
                find(self._construct_tag('allowed')).\
                find(self._construct_tag('vlan')).\
                find(self._construct_tag('add')).text
            return [('vlan/%s' % x, x) for x in vlans.split(',')]
        except AttributeError:
            return []

    def _get_native_vlan(self, interface):
        """ Return the native vlan of an interface.

        Args:
            interface: interface to return the native vlan of

        Returns: Tuple of the form ('vlan/native', vlan) or None
        """
        try:
            url = self._construct_url(interface, suffix='trunk')
            response = requests.get(url, auth=self._auth)
            root = etree.fromstring(response.text)
            vlan = root.find(self._construct_tag('native-vlan')).text
            return ('vlan/native', vlan)
        except AttributeError:
            return None

    def _add_vlan_to_trunk(self, interface, vlan):
        """ Add a vlan to a trunk port.

        If the port is not trunked, its mode will be set to trunk.

        Args:
            interface: interface to add the vlan to
            vlan: vlan to add
        """
        self._set_mode(interface, 'trunk')
        url = self._construct_url(interface, suffix='trunk/allowed/vlan')
        payload = '<vlan><add>%s</vlan></vlan>' % vlan
        requests.put(url, data=payload, auth=self._auth)

    def _remove_vlan_from_trunk(self, interface, vlan):
        """ Remove a vlan from a trunk port.

        Args:
            interface: interface to remove the vlan from
            vlan: vlan to remove
        """
        url = self._construct_url(interface, suffix='trunk/allowed/vlan')
        payload = '<vlan><remove>%s</remove></vlan>' % vlan
        requests.put(url, data=payload, auth=self._auth)

    def _set_native_vlan(self, interface, vlan):
        """ Set the native vlan of an interface.

        Args:
            interface: interface to set the native vlan to
            vlan: vlan to set as the native vlan
        """
        self._set_mode(interface, 'trunk')
        self._disable_native_tag(interface)
        url = self._construct_url(interface, suffix='trunk')
        payload = '<trunk><native-vlan>%s</native-vlan></trunk>' % vlan
        requests.put(url, data=payload, auth=self._auth)

    def _remove_native_vlan(self, interface):
        """ Remove the native vlan from an interface.

        Args:
            interface: interface to remove the native vlan from
        """
        url = self._construct_url(interface, suffix='trunk/native-vlan')
        requests.delete(url, auth=self._auth)

    def _disable_native_tag(self, interface):
        """ Disable tagging of the native vlan

        Args:
            interface: interface to disable the native vlan tagging of

        """
        url = self._construct_url(interface, suffix='trunk/tag/native-vlan')
        response = requests.delete(url, auth=self._auth)


    def _construct_url(self, interface, suffix=None):
        """ Construct the API url for a specific interface appending suffix.

        Args:
            interface: interface to construct the url for
            suffix: suffix to append at the end of the url

        Returns: string with the url for a specific interface and operation
        """
        # %22 is the encoding for double quotes (") in urls.
        # % escapes the % character.
        # Double quotes are necessary in the url because switch ports contain
        # forward slashes (/), ex. 101/0/10 is encoded as "101/0/10".
        return '%(hostname)s/rest/config/running/interface/' \
               '%(interface_type)s/%%22%(interface)s%%22/switchport/%(suffix)s' % {
                  'hostname': self.hostname,
                  'interface_type': self.interface_type,
                  'interface': interface,
                  'suffix': suffix
        }

    @property
    def _auth(self):
        return self.username, self.password

    @staticmethod
    def _construct_tag(name):
        """ Construct the xml tag by prepending the brocade tag prefix. """
        return '{urn:brocade.com:mgmt:brocade-interface}%s' % name
