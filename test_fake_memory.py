""" Test module for the FakeMemory module
"""
import pytest

#Tested Module:
import fake_memory as fm

class TestFakeMemoryUnit:
    @pytest.fixture
    def fmu(self):
        return fm.FakeMemoryUnit(addr_start=0x10,
                                 length=1024)

    @pytest.fixture
    def blank_32(self):
        """generate a blank array"""
        return [0x00 for x in range(32)]

    def test_init(self, fmu):
        assert fmu.start() == 0x10
        assert fmu.end() == 0x10 + 1024 - 1
        assert fmu._get_address(0x10) == 0x00
        assert fmu._get_address(0x11) == 0x01

        for addr in [0x01, 0x2000]:
            with pytest.raises(IOError) as err:
                fmu._get_address(addr)
            assert "out of range" in str(err.value)

    def test_read(self, fmu):
        #read out of range
        with pytest.raises(IOError):
            fmu.read(0x00)

        #except to get 0x00 (memory not initialized)
        assert fmu.read(0x10) == 0x00

        #write at 0x11:
        fmu._data[1] = 0xAA
        assert fmu.read(0x11) == 0xAA

        #read at end of range:
        end = 0x10 + 1024 - 1
        assert fmu.read(end) == 0x00

        fmu._data[1024-1] = 0x55
        assert fmu.read(end) == 0x55

    def test_read_noerror(self, fmu):
        #Out of bound reads
        assert fmu.read(0x00, True) == 0x00
        assert fmu.read(0x1000, True) == 0x00

        fmu._data[0] = 0xAA
        assert fmu.read(0x10, True) == 0xAA

    def test_read32(self, fmu, blank_32):
        with pytest.raises(IOError):
            fmu.read32(0x00)

        # Test the no_error flag
        assert fmu.read32(0x00, True) == blank_32

    def test_write(self, fmu):
        with pytest.raises(IOError):
            fmu.write(0x00, 0xAA)

        fmu.write(0x10, 0xAA)
        assert fmu.read(0x10) == 0xAA

        with pytest.raises(ValueError):
            fmu.write(0x10, 256)

        #Test no error write
        fmu.write(0x00, 0xAA, True)
        fmu.write(0x10, 256, True)

    def test_write32(self, fmu, blank_32):
        #test wrong address
        with pytest.raises(IOError):
            fmu.write(0x00, blank_32)

        #test no_error flag
        fmu.write(0x00, blank_32, True)

        #test good writing
        data = range(32)
        fmu.write(0x10, data)
        assert fmu.read32(0x10) == data

    def test_clear(self,fmu, blank_32):
        data = range(32)
        fmu.write(0x10, data)

        fmu.clear()
        assert fmu.read32(0x10) == blank_32

class TestFakeMemory:
    @pytest.fixture
    def fmem(self):
        return fm.FakeMemory()

    def test_add_range(self, fmem):
        #No MU should be present:
        assert len(fmem._mu) == 0

        fmem.add_range(0x10, 32)

        assert len(fmem._mu) == 1
        assert fmem._mu[0].start() == 0x10
        assert fmem._mu[0].end() == 0x10 + 32 - 1

        #Test overlapping

        with pytest.raises(ValueError) as e:
            fmem.add_range(0x10, 10)
        assert "overlap" in str(e.value)
        assert len(fmem._mu) == 1

        with pytest.raises(ValueError) as e:
            fmem.add_range(0x30-2, 10)
        assert "overlap" in str(e.value)
        assert len(fmem._mu) == 1

        #Test ordering
        # when adding at the end
        fmem.add_range(0x50, 10)
        assert len(fmem._mu) == 2
        assert fmem._mu[0].start() == 0x10
        assert fmem._mu[1].start() == 0x50
        assert fmem._mu[1].end() == 0x50 + 10 - 1

        # when adding in the middle
        fmem.add_range(0x40, 10)
        assert len(fmem._mu) == 3
        assert fmem._mu[0].start() == 0x10
        assert fmem._mu[1].start() == 0x40
        assert fmem._mu[1].end() == 0x40 + 10 - 1
        assert fmem._mu[2].start() == 0x50

        with pytest.raises(ValueError):
            #Should overlap with the first element
            fmem.add_range(0x00, 16+1)

        # when adding at the start
        fmem.add_range(0x00, 0x10)
        assert len(fmem._mu) == 4
        assert fmem._mu[0].start() == 0x00
        assert fmem._mu[0].end() == 0x10 - 1
        assert fmem._mu[1].start() == 0x10
        assert fmem._mu[2].start() == 0x40
        assert fmem._mu[3].start() == 0x50

