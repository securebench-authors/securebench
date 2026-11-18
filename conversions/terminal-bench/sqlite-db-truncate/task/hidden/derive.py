"""Rederive hidden/expected.json from the baseline's /app/trunc.db.

Usage: python3 -I -B derive.py <trunc.db> <upstream tests/test_outputs.py> <expected.json>

trunc.db is a single 4,096-byte table b-tree leaf page (page type 0x0d at
offset 0), without the database header. This script decodes every cell on
it by the SQLite file format (https://www.sqlite.org/fileformat2.html,
Sections 1.6 and 2.1): cell pointer array, payload length and rowid varints,
record header of serial types, then the record body. It prints every row it
decodes and exits non-zero unless all of these hold:

- every cell decodes to a record of three columns (rowid alias, word, value);
- the eight pairs of `soln` in upstream's test are among the decoded rows;
- expected.json holds exactly those eight pairs, in upstream's order.

Nothing here runs at grading time; the Oracle reads only expected.json.
"""

import ast
import json
import struct
import sys

PAGE_SIZE = 4096
LEAF_TABLE = 0x0D


def varint(page: bytes, offset: int) -> tuple[int, int]:
    value = 0
    for index in range(9):
        byte = page[offset + index]
        if index == 8:
            return (value << 8) | byte, offset + 9
        value = (value << 7) | (byte & 0x7F)
        if byte < 0x80:
            return value, offset + index + 1
    raise AssertionError("unreachable")


def column(serial: int, body: bytes, offset: int) -> tuple[object, int]:
    if serial == 0:
        return None, offset
    if 1 <= serial <= 6:
        width = {1: 1, 2: 2, 3: 3, 4: 4, 5: 6, 6: 8}[serial]
        return int.from_bytes(body[offset : offset + width], "big", signed=True), offset + width
    if serial == 7:
        return struct.unpack(">d", body[offset : offset + 8])[0], offset + 8
    if serial in (8, 9):
        return serial - 8, offset
    if serial >= 13 and serial % 2 == 1:
        width = (serial - 13) // 2
        return body[offset : offset + width].decode("utf-8"), offset + width
    raise SystemExit(f"unexpected serial type {serial}")


def rows(page: bytes) -> list[tuple[int, list[object]]]:
    if len(page) != PAGE_SIZE or page[0] != LEAF_TABLE:
        raise SystemExit("trunc.db is not one table leaf page")
    count = int.from_bytes(page[3:5], "big")
    decoded: list[tuple[int, list[object]]] = []
    for index in range(count):
        cell = int.from_bytes(page[8 + 2 * index : 10 + 2 * index], "big")
        length, offset = varint(page, cell)
        rowid, offset = varint(page, offset)
        payload = page[offset : offset + length]
        if len(payload) != length:
            raise SystemExit(f"cell {index} overflows the page")
        header_size, cursor = varint(payload, 0)
        serials: list[int] = []
        while cursor < header_size:
            serial, cursor = varint(payload, cursor)
            serials.append(serial)
        values: list[object] = []
        position = header_size
        for serial in serials:
            value, position = column(serial, payload, position)
            values.append(value)
        if position != length or len(values) != 3:
            raise SystemExit(f"cell {index} is not a three-column record")
        decoded.append((rowid, values))
    return decoded


def upstream_soln(test_path: str) -> list[dict[str, object]]:
    with open(test_path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and [getattr(t, "id", None) for t in node.targets] == ["soln"]:
            return ast.literal_eval(node.value)
    raise SystemExit("no soln in the upstream test")


def main() -> None:
    db_path, test_path, expected_path = sys.argv[1:]
    with open(db_path, "rb") as handle:
        page = handle.read()
    decoded = rows(page)
    pairs = set()
    for rowid, (alias, word, value) in decoded:
        print(f"rowid {rowid}: alias={alias!r} word={word!r} value={value!r}")
        pairs.add((word, value))
    soln = upstream_soln(test_path)
    missing = [item for item in soln if (item["word"], item["value"]) not in pairs]
    if missing:
        raise SystemExit(f"upstream pairs not in trunc.db: {missing}")
    with open(expected_path, encoding="utf-8") as handle:
        expected = json.load(handle)
    if expected != {"pairs": soln, "threshold": 7}:
        raise SystemExit("expected.json differs from upstream soln")
    print(f"expected.json matches upstream: {len(soln)} pairs, all in trunc.db")


if __name__ == "__main__":
    main()
