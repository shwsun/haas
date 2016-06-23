# Copyright 2013-2014 Massachusetts Open Cloud Contributors
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
"""Common functionality for switches with a cisco-like console."""

from abc import ABCMeta, abstractmethod
import re


_CHANNEL_RE = re.compile(r'vlan/(\d+)')


class Session(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def enter_if_prompt(self, interface):
        """Navigate from the main prompt to the prompt for configuring ``interface``."""

    @abstractmethod
    def exit_if_prompt(self):
        """Navigate back to the main prompt from an interface prompt."""

    @abstractmethod
    def enable_vlan(self, vlan_id):
        """Enable ``vlan_id`` for the current interface.

        For this to work, the session must be at an interface prompt (which is
        the "current interface"). See ``enter_if_prompt`` and
        ``exit_if_prompt``.
        """

    @abstractmethod
    def disable_vlan(self, vlan_id):
        """Like ``enable_vlan``, but disables the vlan, rather than enabling it."""

    @abstractmethod
    def set_native(self, old, new):
        """Set the native vlan for the current interface to ``new``.

        ``old`` must be the previous native vlan, or None if there was no
        previous native.
        """

    @abstractmethod
    def disable_native(self, vlan_id):
        """Disable the native vlan.

        ``vlan_id`` is the vlan id of the current native vlan.
        """

    @abstractmethod
    def revert(self):
        """Remove all vlans from the port.
           Allows haas to reset to state in db.
        """

    @abstractmethod
    def disconnect(self):
        """End the session. Must be at the main prompt."""


    def apply_networking(self, action):
        interface = action.nic.port.label
        channel   = action.channel

        self.enter_if_prompt(interface)
        self.console.expect(self.if_prompt)

        if channel == 'vlan/native':
            old_native = None
            old_attachments = filter(lambda a: a.channel == 'vlan/native',
                                        action.nic.attachments)
            if len(old_attachments) != 0:
                old_native = old_attachments[0].network.network_id
            if action.new_network is None:
                self.disable_native(old_native)
            else:
                self.set_native(old_native, action.new_network.network_id)
        else:
            match = re.match(_CHANNEL_RE, channel)
            # TODO: I'd be more okay with this assertion if it weren't possible
            # to mis-configure HaaS in a way that triggers this; currently the
            # administrator needs to line up the network allocator with the
            # switches; this is unsatisfactory. --isd
            assert match is not None, "HaaS passed an invalid channel to the switch!"
            vlan_id = match.groups()[0]
            if action.new_network is None:
                self.disable_vlan(vlan_id)
            else:
                assert action.new_network.network_id == vlan_id
                self.enable_vlan(vlan_id)

        self.exit_if_prompt()
        self.console.expect(self.config_prompt)


def get_prompts(console):
        #Regex to handle different prompt at switch
        #[\r\n]+ will handle any newline
        #.+ will handle any character after newline
        # this sequence terminates with #
        console.expect(r'[\r\n]+.+#')
        cmd_prompt = console.after.split('\n')[-1]
        cmd_prompt = cmd_prompt.strip(' \r\n\t')

        #:-1 omits the last hash character
        return {
            'config_prompt': re.escape(cmd_prompt[:-1] + '(config)#'),
            'if_prompt': re.escape(cmd_prompt[:-1] + '(config-if)#'),
            'main_prompt': re.escape(cmd_prompt),
        }
