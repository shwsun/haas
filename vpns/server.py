"""Manage server-side startup"""
import sys
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

def init_nodes():
    pass
    
def init():
    """Set up the api server's internal state.

    This is a convenience wrapper that calls the other setup routines in
    this module in the correct order
    """
    init_endpoints()
    init_nodes()
