from __future__ import division, print_function
from pytelemetry import Pytelemetry
try:
    from queue import Queue  # Python 3
except ImportError:
    from Queue import Queue  # Python 2
    
# For Python 2 compatibility, if unittest.mock is not available
try:
    import unittest.mock as mock
except ImportError:
    try:
        import mock
    except ImportError:
        print("WARNING: mock module not available, some tests may fail")
        mock = None

from pytelemetry.transports.serialtransport import SerialTransport
import six

class driverMock:
    def __init__(self):
        self.queue = Queue()
        self.in_waiting = 0

    def read(self, size=1):
        data = bytearray()
        amount = 0
        while amount < size and not self.queue.empty():
            c = self.queue.get()
            if isinstance(c, str) and six.PY2:
                c = ord(c)  # Convert to int in Python 2
            data.append(c)
            self.in_waiting -= 1
            amount += 1
        return data

    def write(self, data):
        for i in range(len(data)):
            val = data[i]
            if isinstance(val, str) and six.PY2:
                val = ord(val)  # Convert to int in Python 2
            self.queue.put(val)
            self.in_waiting += 1
        return 0


def test_serial_stats():
    # Setup
    t = SerialTransport()
    t.driver = driverMock()
    c = Pytelemetry(t)

    stats = t.stats()

    assert stats['rx_bytes'] == 0
    assert stats['rx_chunks'] == 0
    assert stats['tx_bytes'] == 0
    assert stats['tx_chunks'] == 0

    c.publish('foo','bar','string')

    stats = t.stats()

    assert stats['rx_bytes'] == 0
    assert stats['rx_chunks'] == 0
    assert stats['tx_bytes'] == 13
    assert stats['tx_chunks'] == 1

    c.update()

    stats = t.stats()

    assert stats['rx_bytes'] == 13
    assert stats['rx_chunks'] == 13 # TODO : For now data read byte after byter. To replace by read in bulk
    assert stats['tx_bytes'] == 13
    assert stats['tx_chunks'] == 1

    c.publish('fooqux',-32767,'int16')

    stats = t.stats()

    assert stats['rx_bytes'] == 13
    assert stats['rx_chunks'] == 13
    assert stats['tx_bytes'] == 13 + 15
    assert stats['tx_chunks'] == 2

    c.update()

    stats = t.stats()

    assert stats['rx_bytes'] == 13 + 15
    assert stats['rx_chunks'] == 13 + 15
    assert stats['tx_bytes'] == 13 + 15
    assert stats['tx_chunks'] == 2

    t.resetStats()

    stats = t.stats()
    
    assert stats['rx_bytes'] == 0
    assert stats['rx_chunks'] == 0
    assert stats['tx_bytes'] == 0
    assert stats['tx_chunks'] == 0
