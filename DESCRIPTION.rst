Pytelemetry
===========

First class data visualization and communication protocol for your IoT and embedded devices.

A minimal, portable communication protocol designed for robustness:

* Implemented in your favorite language (C, Python, Java, C# is coming)
* Easy to use, data-oriented API (publish/subscribe)
* Type-safe messages with automatic serialization/deserialization
* Frame delimiter for serial transmission (either real or emulated)
* Data integrity through CRC validation
* Tested

Main motivations
---------------
* First-class device monitoring and in-system parameter configuration
* Focus on implementing features, not communication protocols
* Easy integration in your favorite framework or GUI
* Free yourself from USB connectivity and go wireless
* Work with binary data directly from your embedded device (integers, floats, etc)

Who should use Pytelemetry
--------------------------
Python users working with IoT and embedded devices.

The Python API can be used to communicate with your device or in a test bench for automated testing. 

Library versions
--------------
Library versions are available for different programming languages/platforms:
* [pytelemetry][pytelemetry] - Python
* [telemetry][telemetry] - C
* [OpenTelemetry][OpenTelemetry] - C# (.NET 4.0+,  4.5+)
* [jtelemetry][jtelemetry] - Java (>= 7)
* [Node-telemetry][Node-telemetry] - NodeJS

Usage example
------------
```python
import pytelemetry, time

# Create your transport (Serial, TCP, custom, etc.)
# The transport need to implement 4 simple methods (read, readable, write, writeable)
from pytelemetry.transports.serialtransport import SerialTransport
transport = SerialTransport()

# Create the telemetry instance
tl = pytelemetry.Pytelemetry(transport)

# Connect transport to your device
port = "COM8"
baudrate = 115200
# Port and baudrate are mandatory options, timeout is not
transport.connect({"port":port, "baudrate":baudrate})

# Callback function for received messages
def on_message(topic, msg, opts):
    print(topic)
    print(msg)

# Subscribe to messages
# By default, all messages not explicitly subscribed will call None callback
# In this case, let's use the same function for all
tl.subscribe(None, on_message)

# Subscribe to specific topics
tl.subscribe("temperature", on_message)
tl.subscribe("barometer", on_message)
tl.subscribe("pressure", on_message)
tl.subscribe("acceleration", on_message)

# Let's publish data to the device
# Important: the datatype is mandatory for proper framing and parsing
# Pay also attention to the max size value depending on the datatype
tl.publish("setPoint", 3.14159, "float32")
tl.publish("calibrate", True, "uint8")

# Main application loop
try:
    while 1:
        # Call update() to process incoming data and frame them
        tl.update()
        time.sleep(0.01)
except KeyboardInterrupt:
    pass

# Disconnect transport
transport.disconnect()
```

Framing diagram
--------------

Framing is used to delimit messages for serial port transmission.

```
SOF | HEADER | TOPIC | EOL | PAYLOAD | CRC | EOF
```

* SOF : Start of frame delimiter
* HEADER : Data type (u8, u16, i8, string, etc.) and other options
* TOPIC : ASCII data designating the data. Topic is terminated by the EOL zero byte.
* EOL : Zero byte marking End Of string (the Topic)
* PAYLOAD : The actual data. Size may vary depending on the type.
* CRC : 16 bit data integrity check (CRC-CCITT)
* EOF : End of frame delimiter

Language C implementation
=========================

Telemetry is the same protocol implemented in C language.

-  `Project page <https://github.com/Overdrivr/Telemetry>`__


Command Line Interface (CLI)
============================

Pytelemetry CLI is a powerful command interface perfectly suited for fast prototyping with this protocol.
It allows for plotting embedded device's data on-the-fly, publishing values on any topics, listing serial ports and much more.

-  `Project page <https://github.com/Overdrivr/pytelemetrycli>`__


Centralized documentation
=========================

The documentation for all three projects is centralized `here <https://github.com/Overdrivr/Telemetry/wiki>`_.

MIT License, (C) 2015-2016 Rémi Bèges (remi.beges@gmail.com)
