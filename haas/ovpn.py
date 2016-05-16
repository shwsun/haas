import subprocess
import os
import sys


def ovpn(cmd):
    def check():
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)

    def exec():
        return subprocess.call(["sudo","openvpn","--cd /etc/openvpn --config openvpn.conf"])


def main():
    def __init__(self):
        pass

    pass
