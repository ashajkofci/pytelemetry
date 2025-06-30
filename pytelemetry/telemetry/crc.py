from __future__ import absolute_import, division, print_function, unicode_literals
# From : https://en.wikipedia.org/wiki/Computation_of_cyclic_redundancy_checks
#
# Most significant bit first (big-endian)
# x^16+x^12+x^5+1 = (1) 0001 0000 0010 0001 = 0x1021

def crc16(data):
    rem = 0
    n = 16
    for d in data:
        # In Python 2, the elements of a bytes/str object are one-character strings.
        if not isinstance(d, int):
            d = ord(d)
        rem = rem ^ (d << (n - 8))
        # Process 7 iterations as in the original code
        for j in range(1, 8):
            if rem & 0x8000:  # if leftmost (most significant) bit is set
                rem = (rem << 1) ^ 0x1021
            else:
                rem = rem << 1
            rem = rem & 0xffff  # Trim to 16 bits after each bit shift
    return rem