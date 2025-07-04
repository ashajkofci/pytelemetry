from __future__ import absolute_import, division, print_function, unicode_literals
import six

def translate(topic):
    opts = None
    t = topic
    try:
        if isinstance(topic, six.string_types):
            split = str.split(topic,":")

            if len(split) > 1:
                t = split[0]
                opts = dict()
                opts['index'] = int(split[1])
    except ValueError:
        t = topic
        opts = None

    return t, opts
