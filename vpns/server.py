"""Manage server-side startup"""
# import sys
import os

from vpns.endpoint import *


def init_endpoints():
    # Note: will raise exception if cert_path does not exist
    dir = os.listdir(VpnEndpoint.cert_path)

    for f in dir:
        fparts = f.split('.')
        if fparts[0] == VpnEndpoint.cert_base and len(fparts) == 2:
            # fparts at 1 should be the endpoint index, e.g. certs.3
            ep = VpnEndpoint(fparts[1])
            ep.findOwner()
            Endpoints.append(ep)

            if ep.node != 'NONE':
                for node in Nodes:
                    if node.key == ep.node:
                        logging.info('found in use node %s, net %s'
                                     % (ep.node, ep.network))
                        ep.nic, ep.channel = node.find_network(ep.network)
                        break


def init_nodes():
    project_nodes = vpn_project_nodes()
    for n in project_nodes:
        node = VpnNode(n)
        register_nics(node)
        Nodes.append(node)


def init():
    """Set up the api server's internal state.

    This is a convenience wrapper that calls the other setup routines in
    this module in the correct order
    """
    if os.geteuid() != 0:
        raise IllegalStateError("Must run as root")
        return

    init_nodes()
    init_endpoints()
