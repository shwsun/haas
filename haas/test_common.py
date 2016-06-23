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

from haas.model import *
from haas.migrations import create_db
from haas.config import cfg
from haas.rest import app, init_auth
from haas import api, config
from StringIO import StringIO
from abc import ABCMeta, abstractmethod
import json
import subprocess
import sys
import os.path


def config_testsuite():
    """Loads an initial config from ``testsuite.cfg``.

    This is meant to be used as/from a pytest fixture, but isn't declared
    here as such; individual modules should declare fixtures which use it.

    Tests which don't care about a specific configuration should leave the
    config alone. This allows the developer to test with different
    configurations, e.g. different DBMS backends.

    if testsuite.cfg doesn't exist, sane defaults are provided.
    """
    # NOTE: The file ``testsuite.cfg.default`` Should be updated whenever
    # The default settings here are modified.
    if os.path.isfile('testsuite.cfg'):
        config.load('testsuite.cfg')
    else:
        config_set({
            'extensions': {
                # Use the null network allocator and auth plugin by default:
                'haas.ext.network_allocators.null': '',
                'haas.ext.auth.null': '',
            },
            'devel': {
                'dry_run': True,
            },
            'headnode': {
                'base_imgs': 'base-headnode, img1, img2, img3, img4',
            },
            'database': {
                'uri': 'sqlite:///:memory:',
            }
        })




def config_merge(config_dict):
    """Modify the configuration according to ``config_dict``.

    ``config_dict`` should be a dictionary mapping section names (strings)
    to dictionaries mapping option names within a section (again, strings)
    to their values. If the value of a section, or option is None, that
    section or option is removed. Otherwise, the section is created if it
    does not exist, and any options are set to the specified values.
    """
    for section in config_dict.keys():
        if config_dict[section] is None:
            print('remove section: %r' % section)
            cfg.remove_section(section)
        else:
            if not cfg.has_section(section):
                print('add section: %r' % section)
                cfg.add_section(section)
            for option in config_dict[section].keys():
                if config_dict[section][option] is None:
                    print('remove option: %r' % option)
                    cfg.remove_option(section, option)
                else:
                    print('set option: %r' % option)
                    cfg.set(section, option, config_dict[section][option])


def config_set(config_dict):
    """Set the configuration according to ``config_dict``.

    This works like ``config_merge``, except that it starts from an empty
    configuration.
    """
    config_clear()
    config_merge(config_dict)


def config_clear():
    """Clear the contents of the current HaaS configuration"""
    for section in cfg.sections():
        cfg.remove_section(section)


def network_create_simple(network, project):
    """Create a simple project-owned network.

    This is a shorthand for the network_create API call, that defaults
    parameters to the most common case---namely, that the network is owned by
    a project, has access only by that project, and uses an allocated
    underlying net_id.  Note that this is the only valid set of parameters for
    a network that belongs to a project.

    The test-suite uses this extensively, for tests that don't care about more
    complicated features of networks.
    """
    api.network_create(network, project, project, "")

def newDB():
    """Configures and returns a connection to a freshly initialized DB."""
    with app.app_context():
        init_db()
        create_db()

def releaseDB():
    """Do we need to do anything here to release resources?"""
    with app.app_context():
        db.drop_all()

def fresh_database(request):
    """Runs the test against a newly populated DB.

    This is meant to be used as a pytest fixture, but isn't declared
    here as such; individual modules should declare it as a fixture.

    This must run *after* the config file (or equivalent) has been loaded.
    """
    newDB()
    request.addfinalizer(lambda: releaseDB())


def with_request_context():
    """Run the test inside of a request context.

    This combines flask's request context with our own setup. It is intended
    to be used via pytests' `yield_fixture`, but like the other fixtures in
    this module, must be declared as such in the test module itself.
    """
    with app.test_request_context():
        init_auth()
        yield


class ModelTest:
    """Superclass with tests common to all models.

    Inheriting from ``ModelTest`` will generate tests in the subclass (each
    of the methods beginning with ``test_`` below), but the ``ModelTest`` class
    itself does not generate tests. (pytest will ignore it because the name of
    the class does not start with ``Test`).
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def sample_obj(self):
        """returns a sample object, which can be used for various tests.

        There aren't really any specific requirements for the object, just that
        it be "valid."
        """

    def test_repr(self):
        print(self.sample_obj())

    def test_insert(self):
        db.session.add(self.sample_obj())


class NetworkTest:
    """Superclass for network-related deployment tests"""

    def get_port_networks(self, ports):
        ret = {}
        ports_by_switch = {}
        for port in ports:
            if port.owner not in ports_by_switch:
                ports_by_switch[port.owner] = []
            ports_by_switch[port.owner].append(port)
        for switch, ports in ports_by_switch.iteritems():
            session = switch.session()
            switch_port_networks = session.get_port_networks(ports)
            session.disconnect()
            for k, v in switch_port_networks.iteritems():
                ret[k] = v
        return ret

    def get_network(self, port, port_networks):
        """Returns all interfaces on the same network as a given port"""
        if port not in port_networks:
            return set()
        result = set()
        for k, v in port_networks.iteritems():
            networks = set([net for channel, net in v])
            for _, net in port_networks[port]:
                if net in networks:
                    result.add(k)
        return result

    def get_all_ports(self, nodes):
        ports = []
        for node in nodes:
            for nic in node.nics:
                ports.append(nic.port)
        return ports

    def collect_nodes(self):
        """Add 4 available nodes with nics to the project.

        If there are not enough nodes, this will rais an api.AllocationError.
        """
        free_nodes = Node.query.filter_by(project_id=None).all()
        nodes = []
        for node in free_nodes:
            if len(node.nics) > 0:
                api.project_connect_node('anvil-nextgen', node.label)
                nodes.append(node)
                if len(nodes) >= 4:
                    break

        # If there are not enough nodes with nics, raise an exception
        if len(nodes) < 4:
            raise api.AllocationError(('At least 4 nodes with at least ' +
                '1 NIC are required for this test. Only %d node(s) were ' +
                'provided.') % len(nodes))
        return nodes


def site_layout():
    """Load the file site-layout.json, and populate the database accordingly.

    This is meant to be used as a pytest fixture, but isn't declared
    here as such; individual modules should declare it as a fixture.

    Full documentation for the site-layout.json file format is located in
    ``docs/testing.md``.
    """
    layout_json_data = open('site-layout.json')
    layout = json.load(layout_json_data)
    layout_json_data.close()

    for switch in layout['switches']:
        api.switch_register(**switch)

    for node in layout['nodes']:
        api.node_register(node['name'],obm=node['obm'])
        for nic in node['nics']:
            api.node_register_nic(node['name'], nic['name'], nic['mac'])
            api.switch_register_port(nic['switch'], nic['port'])
            api.port_connect_nic(nic['switch'], nic['port'], node['name'], nic['name'])


def headnode_cleanup(request):
    """Clean up headnode VMs left by tests.

    This is meant to be used as a pytest fixture, but isn't declared
    here as such; individual modules should declare it as a fixture.

    This is to work around an irritating bug in some versions of libvirt, which
    causes 'virsh undefine' to fail if called too quickly.  This decorator
    depends on the database containing an accurate list of headnodes.
    """

    def undefine_headnodes():
        for hn in Headnode.query:
            # XXX: Our current version of libvirt has a bug that causes this
            # command to hang for a minute and throw an error before
            # completing successfully.  For this reason, we are ignoring any
            # errors thrown by 'virsh undefine'. This should be changed once
            # we start using a version of libvirt that has fixed this bug.
            try:
                hn.delete()
            except subprocess.CalledProcessError:
                pass

    request.addfinalizer(undefine_headnodes)


def initial_db():
    """Populates the database with a useful set of objects.

    This allows us to avoid some boilerplate in tests which need a few objects
    in the database in order to work.

    Note that this fixture requires the use of the following extensions:

        - haas.ext.switches.mock
        - haas.ext.obm.mock
    """
    for required_extension in 'haas.ext.switches.mock', 'haas.ext.obm.mock':
        assert required_extension in sys.modules, \
            "The 'initial_db' fixture requires the extension %r" % \
            required_extension

    from haas.ext.switches.mock import MockSwitch
    from haas.ext.obm.mock import MockObm

    with app.app_context():
        # Create a couple projects:
        runway = Project("runway")
        manhattan = Project("manhattan")
        for proj in [runway, manhattan]:
            db.session.add(proj)

        # ...including at least one with nothing in it:
        db.session.add(Project('empty-project'))

        # ...A variety of networks:

        networks = [
            {
                'creator': None,
                'access': [],
                'allocated': True,
                'label': 'stock_int_pub',
            },
            {
                'creator': None,
                'access': [],
                'allocated': False,
                'network_id': 'ext_pub_chan',
                'label': 'stock_ext_pub',
            },
            {
                # For some tests, we want things to initialyl be attached to a
                # network. This one serves that purpose; using the others would
                # interfere with some of the network_delete tests.
                'creator': None,
                'access': [],
                'allocated': True,
                'label': 'pub_default',
            },
            {
                'creator': runway,
                'access': [runway],
                'allocated': True,
                'label': 'runway_pxe'
            },
            {
                'creator': None,
                'access': [runway],
                'allocated': False,
                'network_id': 'runway_provider_chan',
                'label': 'runway_provider',
            },
            {
                'creator': manhattan,
                'access': [manhattan],
                'allocated': True,
                'label': 'manhattan_pxe'
            },
            {
                'creator': None,
                'access': [manhattan],
                'allocated': False,
                'network_id': 'manhattan_provider_chan',
                'label': 'manhattan_provider',
            },
            {
                'creator': None,
                'access': [manhattan, runway],
                'allocated': False,
                'network_id': 'manhattan_runway_provider_chan',
                'label': 'manhattan_runway_provider',
            },
            {
                'creator': manhattan,
                'access': [manhattan, runway],
                'allocated': True,
                'label': 'manhattan_runway_pxe',
            },
        ]

        for net in networks:
            if net['allocated']:
                net['network_id'] = \
                    get_network_allocator().get_new_network_id()
            db.session.add(Network(**net))

        # ... Two switches. One of these is just empty, for testing deletion:
        db.session.add(MockSwitch(label='empty-switch',
                                  hostname='empty',
                                  username='alice',
                                  password='secret',
                                  type=MockSwitch.api_name))

        # ... The other we'll actually attach stuff to for other tests:
        switch = MockSwitch(label="stock_switch_0",
                            hostname='stock',
                            username='bob',
                            password='password',
                            type=MockSwitch.api_name)

        # ... Some free ports:
        db.session.add(Port('free_port_0', switch))
        db.session.add(Port('free_port_1', switch))

        # ... Some nodes (with projets):
        nodes = [
            {'label': 'runway_node_0', 'project': runway},
            {'label': 'runway_node_1', 'project': runway},
            {'label': 'manhattan_node_0', 'project': manhattan},
            {'label': 'manhattan_node_1', 'project': manhattan},
            {'label': 'free_node_0', 'project': None},
            {'label': 'free_node_1', 'project': None},
        ]
        for node_dict in nodes:
            obm=MockObm(type=MockObm.api_name,
                        host=node_dict['label'],
                        user='user',
                        password='password')
            node = Node(label=node_dict['label'], obm=obm)
            node.project = node_dict['project']
            db.session.add(Nic(node, label='boot-nic', mac_addr='Unknown'))

            # give it a nic that's attached to a port:
            port_nic = Nic(node, label='nic-with-port', mac_addr='Unknown')
            port = Port(node_dict['label'] + '_port', switch)
            port.nic = port_nic

        # ... Some headnodes:
        headnodes = [
            {'label': 'runway_headnode_on', 'project': runway, 'on': True},
            {'label': 'runway_headnode_off', 'project': runway, 'on': False},
            {'label': 'runway_manhattan_on', 'project': manhattan, 'on': True},
            {'label': 'runway_manhattan_off', 'project': manhattan, 'on': False},
        ]
        for hn_dict in headnodes:
            headnode = Headnode(hn_dict['project'],
                                    hn_dict['label'],
                                    'base-headnode')
            headnode.dirty = not hn_dict['on']
            hnic = Hnic(headnode, 'pxe')
            db.session.add(hnic)

            # Connect them to a network, so we can test detaching.
            hnic = Hnic(headnode, 'public')
            hnic.network = Network.query \
                .filter_by(label='pub_default').one()


        # ... and at least one node with no nics (useful for testing delete):
        obm=MockObm(type=MockObm.api_name,
            host='hostname',
            user='user',
            password='password')
        db.session.add(Node(label='no_nic_node', obm=obm))

        db.session.commit()
