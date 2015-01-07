import struct

def str_to_hexstr(s):
    """Convert a string into an hexadecimal string representation"""
    if type(s) is not str:
        s = chr(s)
    return ":".join("{:02x}".format(ord(c)) for c in s)

def ip_to_bin(s):
    """Convert a string representing an IP (eg. 1.2.3.4) into its binary form"""
    #TODO: regexp to check the good formating?
    subs = s.split('.')
    out = ""
    for sub in subs:
        out += chr(int(sub))
    return out

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in xrange(0, len(seq), size))


class CustomRange:
    """Implements a more efficient way thant xrange to test a membership"""
    def __init__(self, start, stop):
        self.start = start
        self.stop = stop

    def __contains__(self, item):
        return self.start <= item <= self.stop


def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1