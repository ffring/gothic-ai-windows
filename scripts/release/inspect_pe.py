import pathlib
import struct
import sys

class PE:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.data = bytearray(self.path.read_bytes())
        self.pe = struct.unpack_from('<I', self.data, 60)[0]
        assert self.data[self.pe:self.pe+4] == b'PE\0\0'
        coff = self.pe + 4
        count = struct.unpack_from('<H', self.data, coff+2)[0]
        optional_size = struct.unpack_from('<H', self.data, coff+16)[0]
        optional = coff+20
        assert struct.unpack_from('<H', self.data, optional)[0] == 0x20b
        self.imagebase = struct.unpack_from('<Q', self.data, optional+24)[0]
        self.sections = []
        sec = optional+optional_size
        for i in range(count):
            off = sec+i*40
            name = bytes(self.data[off:off+8]).split(b'\0')[0].decode()
            vsize, va, rawsize, raw = struct.unpack_from('<IIII', self.data, off+8)
            self.sections.append((name, va, vsize, raw, rawsize))
        import_rva = struct.unpack_from('<I', self.data, optional+112+8)[0]
        self.imports = {}
        desc = self.offset(import_rva)
        while any(self.data[desc:desc+20]):
            lookup, _, _, name, iat = struct.unpack_from('<IIIII', self.data, desc)
            dll = self.cstr(self.offset(name))
            index = 0
            while True:
                value = struct.unpack_from('<Q', self.data, self.offset(lookup or iat)+index*8)[0]
                if not value:
                    break
                if not value >> 63:
                    self.imports[iat+index*8] = (dll, self.cstr(self.offset(value)+2))
                index += 1
            desc += 20

    def offset(self, rva):
        for _, va, vsize, raw, rawsize in self.sections:
            if va <= rva < va+max(vsize, rawsize):
                return raw+rva-va
        raise ValueError(hex(rva))

    def cstr(self, off):
        return bytes(self.data[off:self.data.index(0, off)]).decode(errors='replace')

    def calls(self, symbol):
        targets = {rva for rva, (_, name) in self.imports.items() if name == symbol}
        results = []
        for name, va, vsize, raw, rawsize in self.sections:
            if name != '.text':
                continue
            for off in range(raw, raw+rawsize-6):
                if self.data[off:off+2] != b'\xff\x15':
                    continue
                rva = va+off-raw
                target = rva+6+struct.unpack_from('<i', self.data, off+2)[0]
                if target in targets:
                    results.append((rva, off))
        return results

if __name__ == '__main__':
    for path in sys.argv[1:]:
        pe = PE(path)
        print(path)
        for rva, off in pe.calls('setvbuf'):
            print(f'call RVA 0x{rva:x}, return 0x{rva+6:x}, raw 0x{off:x}')
            print(bytes(pe.data[off-48:off+14]).hex(' '))
