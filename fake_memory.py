""" Fake memory module
"""
from __future__ import print_function
import types
import hexdump
import logging

import srec_util as SRec
import helpers


class FakeMemoryUnit(object):
    """A Fake memory unit: represent a single continuous range of fake memory
    """
    def __init__(self, addr_start, length, description=''):
        """
        :param addr_start: start address of the range
        :param length: length of the range, in bytes
        :param description: an optional friendly name
        """
        self._addr_start = addr_start
        self.length = length
        self._data = None
        self.clear()
        self.range = helpers.CustomRange(self.start(), self.end())
        self.description = description

    def start(self):
        """Returns the start address of the memory unit on the bus"""
        return self._addr_start

    def end(self):
        """Returns the end address of the memory unit on the bus"""
        return self.start() + self.length - 1

    def _get_address(self, address):
        """Return the adress in the data[] array from a 32bit address.
        Raise IOError if the adress is out of range"""
        if address in self.range:
            return address - self.start()
        else:
            raise IOError("Address {} out of range.".format(address))

    def read(self, address, no_error=False):
        """return the byte located at the given adress in the memory
        :param address: address to start reading from
        :param no_error: if set to True, will not raise an error when
        attempting reading from an out of bound area (will return zero)
        :return: an integer
        """
        try:
            return self._data[self._get_address(address)]
        except IOError as e:
            if no_error:
                return 0x00
            else:
                raise e

    def read32(self, address, no_error=False):
        """
        :param address: address to start reading from
        :param no_error: if set to True, will not raise an error when
        attempting reading from an out of bound area (will return zeroes)
        :return: a 32 integer long array
        """
        return [self.read(x, no_error) for x in range(address, address+32)]

    def write(self, address, value, no_error=False):
        """ Write value at the given address """
        try:
            address = self._get_address(address)
            if type(value) is list:
                self._data[address:address+len(value)] = value
            else:
                self._data[address] = value
        except (IOError, ValueError) as e:
            if no_error:
                return
            else:
                raise e

    def clear(self):
        """Erase the content of the memory module"""
        #  Initialize the memory unit with zeroes
        self._data = bytearray(self.length * '\x00')

    def __str__(self):
        """Print a nice hexdump representation of the memory array"""
        return hexdump.hexdump(str(self._data), result='return')


class FakeMemory(object):
    """ A fake memory. Contains one or several fake memory units (or ranges)
    """
    def __init__(self):
        self._mu = list()  # Memory units

        #  Dirty, but avoids repeating code that is always the same otherwise
        self.read = types.MethodType(self._read_write_method, "read")
        self.read32 = types.MethodType(self._read_write_method, "read32")
        self.write = types.MethodType(self._read_write_method, "write")

    def add_range(self, addr_start, length, description = ""):
        """Adds a range to the fake memory
        :param addr_start: start address of the range
        :param length: length of the range, in bytes
        :param description: an optional friendly name
        """
        def overlap_error():
            raise ValueError("The provided range overlaps with an existing one.")

        new_mu = FakeMemoryUnit(addr_start, length, description)

        # try inserting the range in the ranges
        #  1. find the good position
        pos_idx = 0
        for fmu in self._mu:
            if new_mu.start() in fmu.range or new_mu.end() in fmu.range:
                overlap_error()

            if new_mu.start() < fmu.start():
                break
            pos_idx += 1

        # 2. Check that we will not overlap with the next range
        try:
            next_mu = self._mu[pos_idx+1]
            if new_mu.end() >= next_mu.start():
                overlap_error()
        except IndexError:
            # No next mu ==> no risk of overlapping
            pass

        # 3. Insert it
        self._mu.insert(pos_idx, new_mu)

    def _find_mu(self, address):
        """Find the FakeMemoryUnit that contains the given address"""
        for mu in self._mu:
            if address in mu.range:
                return mu
        raise IOError("No adress {} in the ranges".format(address))

    def _read_write_method(self, method_name, address, val=None, no_error=False):
        """ Read or write a byte at a given address
        """
        try:
            mu = self._find_mu(address)
            if method_name.startswith('read'):
                return getattr(mu, method_name)(address, no_error)
            elif method_name.startswith('write'):
                return getattr(mu, method_name)(address, val, no_error)
        except IOError as e:
            if not no_error:
                raise e

    def clear(self):
        """Clear all the modules of the memory"""
        for mu in self._mu:
            mu.clear()

    def __str__(self):
        """Return a printable representation of the memory arrays"""
        o = ""
        for mu in self._mu:
            s  = '********************************\n'
            s += 'Description: {descr}\n' if mu.description != '' else ''
            s += 'Start:       {start}\n'
            s += 'End:         {end}\n'
            s += 'Length:      {length}\n' \
                 '             d{dlength}\n'
            s = s.format(start=hex(mu.start()), end=hex(mu.end()),
                         length=hex(mu.length), dlength=mu.length,
                         descr=mu.description)
            o += s
            o += str(mu)
            o += '\n'
        return o

    def dump(self, filename):
        with open(filename, "w") as f:
            f.write(str(self))


class FakeMemoryItf:
    """ An interface between the fake memory class and the programmer's command
    parser.
    """
    def __init__(self):
        self._m = FakeMemory()
        self.log = logging.getLogger('FakeMem')

        # Initialize it as it is on the standard UPC
        self._m.add_range(0x10000000, 1024*1024, "Flash")

    def cmd_erase_memory(self):
        """ Clear the memory from all the data
        :return: True (means success)
        """
        self.log.info('Erasing memory.')
        self._m.clear()
        return True

    def cmd_write_srec(self, srec):
        """Execute the command in a given SREC line.
        Return True if ok, false otherwise"""

        rtype, rlen, addr, data, chk = SRec.parse_srec(srec)
        addr = int(addr, 16)  # convert from string to integer
        # print(addr,hex(addr), data)
        if not SRec.validate_srec_checksum(srec.strip()):
            self.log.error('Unable to validate SREC: {}'.format(srec))
            return False

        if rtype == 'S0':
            self.log.debug('Received start of SREC file')
        elif rtype == 'S3':
            """ Write data into memory """
            data = [int(x, 16) for x in helpers.chunker(data, 2)]
            self._m.write(addr, data)
        elif rtype == 'S7':
            pass
        else:
            raise NotImplementedError('Not implemented SREC Command {}'.format(rtype))
        return True
