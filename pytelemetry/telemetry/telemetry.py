# -*- coding: utf-8 -*-

from __future__ import division, print_function
from .crc import crc16
from .framing import Delimiter
from struct import pack, unpack, unpack_from, calcsize
from logging import getLogger
import struct
import six

# For Python 2 compatibility when dealing with bytes/strings
if six.PY3:
    from binascii import hexlify
else:
    # Python 2 implementation
    def hexlify(data):
        if isinstance(data, bytearray):
            return ''.join('{:02x}'.format(b) for b in data)
        return ''.join('{:02x}'.format(ord(c)) for c in data)

class Telemetry:
    """
    Low level telemetry protocol (github.com/Overdrivr/Telemetry) implemented in python
    """
    def __init__(self, transport, callback):
        self.transport = transport
        self.on_frame_callback = callback
        self.delimiter = Delimiter(self._on_frame_detected)
        self.types = {'float32' : 0,
                      'uint8'   : 1,
                      'uint16'  : 2,
                      'uint32'  : 3,
                      'int8'    : 4,
                      'int16'   : 5,
                      'int32'   : 6,
                      'string'  : 7}

        self.sizes = {'float32' : 4,
                      'uint8'   : 1,
                      'uint16'  : 2,
                      'uint32'  : 4,
                      'int8'    : 1,
                      'int16'   : 2,
                      'int32'   : 4}

        self.rtypes = dict(zip(self.types.values(), self.types.keys()))

        self.formats = {'float32' : "f",
                        'uint8'   : "B",
                        'uint16'  : "H",
                        'uint32'  : "L",
                        'int8'    : "b",
                        'int16'   : "h",
                        'int32'   : "l"}

        self.log_rx = getLogger('telemetry.rx')
        self.log_tx = getLogger('telemetry.tx')

        self.resetStats()

    def resetStats(self):
        self.rx_decoded_frames = 0
        self.rx_corrupted_crc = 0
        self.rx_corrupted_header = 0
        self.rx_corrupted_eol = 0
        self.rx_corrupted_topic = 0
        self.rx_corrupted_payload = 0
        self.tx_encoded_frames = 0

    def stats(self):
        return {
            "rx_decoded_frames" : self.rx_decoded_frames,
            "rx_corrupted_crc" : self.rx_corrupted_crc,
            "rx_corrupted_header" : self.rx_corrupted_header,
            "rx_corrupted_eol" : self.rx_corrupted_eol,
            "rx_corrupted_topic" : self.rx_corrupted_topic,
            "rx_corrupted_payload" : self.rx_corrupted_payload,
            "tx_encoded_frames" : self.tx_encoded_frames
        }

    def _encode_frame(self, topic, data, datatype):
        # Ensure topic is bytes for both Python 2 and 3
        if isinstance(topic, six.text_type):
            topic = topic.encode('utf8')

        if datatype == "string":
            # Handle string data for both Python versions
            if isinstance(data, six.text_type):
                data = data.encode("utf8")
            payload_fmt = "%ds" % len(data)
        else:
            payload_fmt = self.formats[datatype]

        frame = pack("<H%dsB%s" % (len(topic), payload_fmt),
                        self.types[datatype],
                        topic, 0,
                        data)
        frame = bytearray(frame)

        # crc
        _crc = crc16(frame)
        _crc = pack("<H", _crc)
        frame.extend(_crc)

        # Log sent frame
        hex_frame = hexlify(frame)
        if isinstance(hex_frame, six.binary_type):
            hex_frame = hex_frame.decode('ascii')
        self.log_tx.info(hex_frame)

        self.tx_encoded_frames += 1

        return frame

    def _decode_frame(self, frame):
        if len(frame) < 2:
            return

        # compute local crc
        local_crc = crc16(frame[:-2])

        # unpack frame crc
        try:
            frame_crc, = unpack("<H", frame[-2:])
        except struct.error as e:
            hex_frame = hexlify(frame)
            if isinstance(hex_frame, six.binary_type):
                hex_frame = hex_frame.decode('ascii')
            self.log_rx.error("Could not unpack CRC. %s %s" % (e, hex_frame))
            return

        if local_crc != frame_crc:
            hex_frame = hexlify(frame)
            if isinstance(hex_frame, six.binary_type):
                hex_frame = hex_frame.decode('ascii')
            self.log_rx.warn("CRC local {0} vs frame {1} for {2}"
                             .format(local_crc, frame_crc, hex_frame))
            self.rx_corrupted_crc += 1
            return

        # unpack header
        try:
            header, = unpack_from("<H", frame)
        except struct.error as e:
            hex_frame = hexlify(frame)
            if isinstance(hex_frame, six.binary_type):
                hex_frame = hex_frame.decode('ascii')
            self.log_rx.error("Could not unpack header in frame {1} : {0}".format(e, hex_frame))
            self.rx_corrupted_header += 1
            return

        if not header in self.rtypes:
            hex_frame = hexlify(frame)
            if isinstance(hex_frame, six.binary_type):
                hex_frame = hex_frame.decode('ascii')
            self.log_rx.warn("Header not found in frame {0}".format(hex_frame))
            self.rx_corrupted_header += 1
            return

        # locate EOL
        try:
            i = frame.index(0, 2, -2)
        except:
            hex_frame = hexlify(frame)
            if isinstance(hex_frame, six.binary_type):
                hex_frame = hex_frame.decode('ascii')
            self.log_rx.warn("topic EOL not found for {0}"
                             .format(hex_frame))
            self.rx_corrupted_eol += 1
            return

        # decode topic
        try:
            topic = frame[2:i].decode("utf8")
        except UnicodeError as e:
            self.log_rx.warning("Decoding error for topic. %s. Using 'replace' option." % e)
            self.rx_corrupted_topic += 1
            topic = frame[2:i].decode("utf8", errors='replace')

        # Find type from header
        _type = self.rtypes[header]

        # decode data
        if _type == "string":
            # start at i+1 to remove EOL zero
            try:
                data = frame[i+1:-2].decode("utf8")
            except UnicodeError:
                data = frame[i+1:-2].decode("utf8", errors='replace')
        else:
            # Find format
            fmt = self.formats[_type]
            # Check actual sizes matches the one expected by unpack
            # (start at i+1 to remove EOL zero)
            expected_size = self.sizes[_type]
            actual_size = len(frame[i+1:-2])
            if actual_size != expected_size:
                hex_frame = hexlify(frame)
                if isinstance(hex_frame, six.binary_type):
                    hex_frame = hex_frame.decode('ascii')
                self.log_rx.warn("Payload size {0} not matching {1} for {2}"
                        .format(actual_size,
                                expected_size,
                                hex_frame))
                self.rx_corrupted_payload += 1
                return

            # Unpack payload
            try:
                data, = unpack_from("<%s" % fmt, frame, i+1)
            except struct.error as e:
                hex_frame = hexlify(frame)
                if isinstance(hex_frame, six.binary_type):
                    hex_frame = hex_frame.decode('ascii')
                self.log_rx.error("Could not unpack payload in frame {0} : {1}".format(hex_frame, e))
                self.rx_corrupted_payload += 1
                return

        hex_frame = hexlify(frame)
        if isinstance(hex_frame, six.binary_type):
            hex_frame = hex_frame.decode('ascii')
        self.log_rx.info(hex_frame)
        self.rx_decoded_frames += 1

        return topic, data

    def publish(self, topic, data, datatype):
        # header
        if not datatype in self.types:
            self.log_rx.error("Provided datatype {0} not found for ({1}, {2})".format(datatype, topic, data))
            raise IndexError("Provided datatype {0} not found for ({1}, {2})".format(datatype, topic, data))
            return

        frame = self._encode_frame(topic, data, datatype)

        # bytestuff
        frame = self.delimiter.encode(frame)

        # send
        if self.transport.writeable():
            self.transport.write(frame)

    def update(self):
        amount = self.transport.readable()
        for i in range(amount):
            c = self.transport.read(maxbytes=1)
            if c:  # Handle None or empty data
                self.delimiter.decode(c)

    def _on_frame_detected(self, frame):
        topic_data = self._decode_frame(frame)
        if topic_data is None:
            return
        topic, data = topic_data
        self.on_frame_callback(topic, data)
