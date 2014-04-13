import json
import struct
from cStringIO import StringIO
import logging

from datatypes import *
from exc import *

LOG = logging.getLogger(__name__)

default_status_response = {'players': {'max': 20, 'online': 0},
                           'version': {'protocol': 4,
                                       'name': 'Minecraft Server'},
                           'description': 'Minecraft proxy'},
                

class Engine (object):
    '''This is a super-minimal implementation of the handshake portion of
    the Minecraft protocol.  Create an Engine object:

        e = Engine()

    Feed data to the engine using `e.send(data)` and receive back a list of
    responses to send to the client.  Check for `e.complete` to see if the
    handshake process is complete:

        responses = e.send(data)
        for response in responses:
            client.send(response)
        if e.complete:
            break

    After the engine exits, `e.buffer` will contain any data from the
    client that has not been processed.
    '''

    # Maps states to expected packet ids.
    expected = {
        0: [0],
        1: [0],
        2: [0,1],
        3: [1],
    }

    # Packet IDs.  Geez, Mojang, how about some variety?
    HANDSHAKE       = 0
    STATUS_REQUEST  = 0
    PING            = 0x01
    STATUS_RESPONSE = 0

    def __init__(self, status_response=default_status_response):
        self.state = 0
        self.buffer = ''
        self.complete = False
        self.status_response = status_response

    def send(self, bytes):
        self.buffer += bytes
        response = []

        while self.buffer:
            try:
                pkt, data = Packet.decode(self.buffer)
            except NeedMoreData:
                break

            self.buffer = data

            if self.state in self.expected and not pkt['id'] in self.expected[self.state]: 
                raise ValueError('unexpected packet id %d in state %d' % (
                    pkt['id'], self.state))

            if self.state == 0:
                if pkt['id'] == Engine.HANDSHAKE:
                    pkt, remainder = Handshake.decode(pkt['payload'])
                    LOG.debug('handshake: %s', ', '.join('%s=%s' % (k,v) for k,v in pkt.items()))
                    if pkt['next_state'] != 1:
                        self.buffer = bytes
                        self.complete = True
                        break
                    self.state = 1
            elif self.state == 1:
                if pkt['id'] == Engine.STATUS_REQUEST:
                    LOG.debug('status request')
                    # no payload
                    response.append(
                        Packet.encode({
                            'id': Engine.STATUS_RESPONSE,
                            'payload': Status.encode({'status':
                                                      self.status_response})}))
                    self.state = 2
            elif self.state == 2:
                if pkt['id'] == Engine.PING:
                    ping, remainder = Ping.decode(pkt['payload'])
                    LOG.debug('ping, time=%s' % ping['time'])
                    response.append(
                        Packet().encode({
                            'id': Engine.PING,
                            'payload': Ping().encode(ping)}))

                    self.completed = True

        return response

def hexdump(s):
    dump = []
    for c in s:
        dump.append('%02X' % ord(c))
    return ' '.join(dump)

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG)

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
        print '<--', repr(from_client), hexdump(from_client)
        bytes = bytes[8:]
        res = pe.send(from_client)
        for data in res:
            print '-->', repr(data), hexdump(data)

        if not bytes:
            break

