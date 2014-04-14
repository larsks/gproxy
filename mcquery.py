#!/usr/bin/python

import os
import sys
import argparse
import socket
import select

from datatypes import *
from exc import *

def send_query():
    cli = socket.create_connection((args.remotehost, args.remoteport))

    data = Packet.encode({'id': HANDSHAKE,
                          'payload': Handshake.encode({
                              'protocol_version': args.protocol_version,
                              'server_address': args.remotehost,
                              'server_port': args.remoteport,
                              'next_state': 1})})
    cli.send(data)

    data = Packet.encode({'id': HANDSHAKE,
                          'payload': ''})
    cli.send(data)

    res = ''
    while True:
        data = cli.recv(8192)
        if not data:
            break

        res += data
        try:
            pkt, remainder = Packet.decode(res)
            info, remainder = Status.decode(pkt['payload'])
            break
        except NeedMoreData:
            continue

    return info['status']

def print_info(info):
    print args.remotehost, args.remoteport, \
        '%d/%d' % (info['players']['online'], info['players']['max']), \
        info['version']['protocol'], info['version']['name'], \
        info['description']   

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--protocol-version', '-V',
                   default=5,
                   type=int)
    p.add_argument('remotehost')
    p.add_argument('remoteport',
                   nargs='?',
                   default=25565,
                   type=int)
    return p.parse_args()

def main():
    global args
    args = parse_args()

    info = send_query()
    print_info(info)

if __name__ == '__main__':
    main()


