import json
import struct
import sys

with open(sys.argv[1], "rb") as f:
    data = f.read()

# 64-bit little-endian ELF only, which is what gcc produces in this image.
shoff = struct.unpack_from("<Q", data, 0x28)[0]
shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 0x3A)
sections = []
for i in range(shnum):
    name, kind, flags, addr, offset, size = struct.unpack_from("<IIQQQQ", data, shoff + i * shentsize)
    sections.append((name, addr, offset, size))
names_offset = sections[shstrndx][2]

memory = {}
for name, addr, offset, size in sections:
    end = data.index(b"\0", names_offset + name)
    if data[names_offset + name:end].decode() not in (".text", ".data", ".rodata"):
        continue
    for i in range(0, size - 3, 4):
        memory[str(addr + i)] = float(struct.unpack_from("<I", data, offset + i)[0])
json.dump(memory, sys.stdout)
