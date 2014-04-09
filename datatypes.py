from six import add_metaclass
import struct
import json

class Atom(object):
    def decode(self, data):
        return data

    def encode(self, value):
        return value

class Struct(Atom):
    def __init__(self, format):
        self.format = format
        self.size = struct.calcsize(format)
        super(Struct, self).__init__()

    def encode(self, value):
        try:
            return struct.pack(self.format, *value)
        except TypeError:
            return struct.pack(self.format, value)

    def decode(self, data):
        val = struct.unpack(self.format, data[:self.size])
        if len(val) == 1:
            val = val[0]
        return val, data[self.size:]

class Varint(Atom):
    def encode(self, value):
        data = ''

        while True:
            if value > 127:
                # Yield a byte with the most-significant-bit (MSB) set plus 7
                # bits of data from the value.
                data+= chr((1 << 7) | (value & 0x7f))

                # Shift to the right 7 bits to drop the data we've already
                # encoded. If we've encoded all the data for this value, set the
                # None flag.
                value >>=  7
            else:
                # This is either the last byte or only byte for the value, so
                # we don't set the MSB.
                data += chr(value)
                break

        return data

    def decode(self, data):
        value = 0
        base = 1
        for i, raw_byte in enumerate(data):
            val_byte = ord(raw_byte)
            value += (val_byte & 0x7f) * base
            if (val_byte & 0x80):
                # The MSB was set; increase the base and iterate again, continuing
                # to calculate the value.
                base *= 128
            else:
                # The MSB was not set; this was the last byte in the value.
                break

        return value, data[i+1:]

class String(Atom):
    def __init__(self):
        super(String, self).__init__()
        self.varint = Varint()

    def encode(self, value):
        return self.varint.encode(len(value)) + value

    def decode(self, data):
        strlen, data = self.varint.decode(data)
        value, data = data[:strlen], data[strlen:]
        return value, data

class JSONString(Atom):
    def __init__(self):
        super(JSONString, self).__init__()
        self.varint = Varint()

    def encode(self, value):
        data = json.dumps(value)
        return self.varint.encode(len(data)) + data

    def decode(self, data):
        strlen, data = self.varint.decode(data)
        value, data = data[:strlen], data[strlen:]
        return json.loads(value)

class Field (object):
    fieldcount = 0

    def __init__(self, wrapped):
        self._wrapped = wrapped
        self._id = Field.fieldcount
        Field.fieldcount += 1

    def __getattr__(self, k):
        return getattr(self._wrapped, k)

class PacketMeta (type):
    def __init__(cls, name, bases, attrs):
        super(PacketMeta, cls).__init__(name, bases, attrs)
        fields = ((fldname, fld) 
                      for fldname, fld in attrs.items()
                      if isinstance(fld, Field))

        cls._fields = sorted(fields, key=lambda field: field[1]._id)

@add_metaclass(PacketMeta)
class PacketBase (dict):
    @classmethod
    def decode(cls, data):
        value = {}
        for fieldname, field in cls._fields:
            value[fieldname], data = field.decode(data)

        return value, data

    @classmethod
    def encode(cls, value):
        data = ''
        for fieldname, field in cls._fields:
            data += field.encode(value[fieldname])

        return data

class Packet (PacketBase):

    id = Field(Varint())
    payload = Field(String())

class Handshake (PacketBase):

    protocol_version = Field(Varint())
    server_address = Field(String())
    server_port = Field(Struct('>H'))
    next_state = Field(Varint())

class Status (PacketBase):

    status = Field(JSONString())

class Ping (PacketBase):

    time = Field(Struct('>Q'))

if __name__ == '__main__':

    orig_value = {'protocol_version': 4,
                  'server_address': 'localhost',
                  'server_port': 25565,
                  'next_state': 1}
    data = Handshake.encode(orig_value)
    decoded_value, leftover = Handshake.decode(data)

    assert(all(orig_value[k] == decoded_value[k]
               for k in orig_value.keys()))

