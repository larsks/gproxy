import json
import struct
from cStringIO import StringIO
import varint
import logging

from datatypes import *

LOG = logging.getLogger('protocol')

server_status = {'status': {'players':
                            {'max': 20, 'online': 0},
                            'version': {'protocol': 4, 'name': 'CraftBukkit 1.7.5'},
                            'description': 'Email minecraft@vankelsted.org for access.'},
                 }

def coroutine(func):
    def start(*args, **kwargs):
        g = func(*args, **kwargs)
        g.next()
        return g
    return start

class Engine (object):
    expected = {
        0: [0],
        1: [0],
        2: [0,1],
        3: [1],
    }

    HANDSHAKE       = 0
    STATUS_REQUEST  = 0
    PING            = 0x01
    STATUS_RESPONSE = 0

    def __init__(self):
        self.state = 0
        self.buffer = ''
        self.complete = False
        self.waiting = False

    def send(self, bytes):
        self.buffer += bytes
        response = []

        while self.buffer:
            pktlen, data = Varint().decode(self.buffer)

            if len(data) < pktlen:
                self.waiting = True
                break

            self.buffer = self.buffer[pktlen+1:]

            print 'TOP S:', self.state

            self.waiting = False
            pktid, data = Varint().decode(data)
            if self.state in self.expected and not pktid in self.expected[self.state]: 
                raise ValueError('unexpected packet id %d in state %d' % (
                    pktid, self.state))

            if self.state == 0:
                if pktid == Engine.HANDSHAKE:
                    pkt, data = Handshake.decode(data)
                    print 'HANDSHAKE:', pkt
                    if pkt['next_state'] != 1:
                        self.buffer = bytes
                        self.complete = True
                        break
                    self.state = 1
            elif self.state == 1:
                if pktid == Engine.STATUS_REQUEST:
                    # no payload
                    response.append(
                        Packet().encode({
                            'id': Engine.STATUS_RESPONSE,
                            'payload': Status().encode(server_status)}))
                    self.state = 2
            elif self.state == 2:
                if pktid == Engine.PING:
                    pkt, data = Ping.decode(data)
                    response.append(
                        Packet().encode({
                            'id': Engine.PING,
                            'payload': Ping().encode(pkt)}))

                    self.completed = True

            print 'BOTTOM S:', self.state, 'BUFFER:', repr(self.buffer)

        return response

if __name__ == '__main__':
    data=[
        '18 00 04 12 62 6f 75 6e 63 65 72 2e 6f 64 64 62 '
        '69 74 2e 63 6f 6d 63 dd 01',

        '01 00',

        '93 01 00 90 01 7b 22 64 65 73 63 72 69 70 74 69 '
        '6f 6e 22 3a 22 45 6d 61 69 6c 20 6d 69 6e 65 63 '
        '72 61 66 74 40 76 61 6e 6b 65 6c 73 74 65 64 2e '
        '6f 72 67 20 66 6f 72 20 61 63 63 65 73 73 2e 22 '
        '2c 22 70 6c 61 79 65 72 73 22 3a 7b 22 6d 61 78 '
        '22 3a 32 30 2c 22 6f 6e 6c 69 6e 65 22 3a 30 7d '
        '2c 22 76 65 72 73 69 6f 6e 22 3a 7b 22 6e 61 6d '
        '65 22 3a 22 43 72 61 66 74 42 75 6b 6b 69 74 20 '
        '31 2e 37 2e 35 22 2c 22 70 72 6f 74 6f 63 6f 6c '
        '22 3a 34 7d 7d',

        '09 01 00 00 01 45 3d 2f 98 96',

        '09 01 00 00 01 45 3d 2f 98 96',
    ]

    clientdata=[
        '18 00 04 12 62 6f 75 6e 63 65 72 2e 6f 64 64 62 '
        '69 74 2e 63 6f 6d 63 dd 01',

        '01 00',

        '09 01 00 00 01 45 3d 2f 98 96',
    ]

    bytes = ''
    for chunk in clientdata:
        chunk = [int(x, base=16) for x in chunk.split()]
        chunk = struct.pack('>%dB' % len(chunk), *chunk)
        bytes += chunk

    pe = Engine()
    while True:
        from_client = bytes[:8]
        print '<--', repr(from_client)
        bytes = bytes[8:]
        res = pe.send(from_client)
        for data in res:
            print '-->', repr(data)

        if not bytes:
            break

