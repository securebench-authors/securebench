"""Oracle for terminal-bench/dna-insert.

One artifact check reads /app/primers.fasta, and `judge` repeats upstream's
`test_primers` step by step on its text. The expected sequences and bounds
come from hidden/expected.json. Melting temperatures come from
hidden/oligotm.json, the output of primer3's real oligotm for every sequence
the test can pass it (see derive_oligotm.py), so nothing here reimplements
oligotm.
"""

from securebench.core.evidence import ArtifactEvidence, CaseEvidence, FileStatus, HiddenResources, Judgment, Plan, Text
from securebench.core.jsondata import JsonValue

NUCLEOTIDES = frozenset("atcg")


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    table = resources.read_json("oligotm.json")
    if not isinstance(expected, dict) or not isinstance(table, dict):
        raise ValueError("hidden data is malformed")
    tm = {
        strand: {length: row["tm"] for length, row in table[strand].items()}
        for strand in ("forward", "reverse")
    }
    return Plan(artifact_contexts={"primers": {"expected": expected, "tm": tm}}, cases={})


def rc(seq: str) -> str:
    return seq.translate(str.maketrans("atcg", "tagc"))[::-1]


def file_lines(text: str) -> list[str]:
    # Upstream reads the file with Python's universal newlines and iterates
    # it: "\r\n" and "\r" end lines as "\n" does, and a final terminator does
    # not start an empty line. Each line is then rstripped.
    pieces = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if pieces[-1] == "":
        pieces.pop()
    return [piece.rstrip() for piece in pieces]


def fail(reason: str, **details: JsonValue) -> Judgment:
    return Judgment(False, {"reason": reason, **details})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != "primers" or not isinstance(evidence, ArtifactEvidence) or len(evidence.files) != 1:
        return fail("unexpected evidence")
    if not isinstance(context, dict):
        return fail("malformed context")
    expected = context["expected"]
    tm_table = context["tm"]
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        return fail(f"primers.fasta is {found.status.value}")

    lines = file_lines(found.value.text)
    if len(lines) != expected["line_count"]:
        return fail("Invalid number of lines in primers.fasta.", lines=len(lines))
    fwd_primer = lines[1].lower()
    rev_primer = lines[3].lower()
    for primer in (fwd_primer, rev_primer):
        if primer == "" or not set(primer) <= NUCLEOTIDES:
            return fail("Primer must contain only A, T, C, G.")

    primers_concat = rc(rev_primer) + fwd_primer
    insert = expected["insert"]
    insert_start = primers_concat.find(insert)
    if insert_start == -1:
        return fail("Primer must contain inserted DNA.")
    insert_end = insert_start + len(insert)
    annealed_rev = primers_concat[:insert_start]
    annealed_fwd = primers_concat[insert_end:]
    lengths = {"annealed_fwd": len(annealed_fwd), "annealed_rev": len(annealed_rev)}

    low, high = expected["anneal_min"], expected["anneal_max"]
    if not low <= len(annealed_fwd) <= high:
        return fail("Annealed part of forward primer must be between 15 and 45 nucleotides.", **lengths)
    if not low <= len(annealed_rev) <= high:
        return fail("Annealed part of reverse must be between 15 and 45 nucleotides.", **lengths)

    if expected["vector1"][-len(annealed_rev) :] != annealed_rev:
        return fail("Reverse primer must overlap vector.", **lengths)
    if expected["vector2"][: len(annealed_fwd)] != annealed_fwd:
        return fail("Forward primer must overlap vector.", **lengths)

    # Past the overlap checks, annealed_fwd is vector2's prefix and
    # rc(annealed_rev) the reverse complement of vector1's suffix of these
    # lengths: exactly the sequences hidden/oligotm.json was computed for.
    fwd_tm = tm_table["forward"].get(str(len(annealed_fwd)))
    rev_tm = tm_table["reverse"].get(str(len(annealed_rev)))
    if not isinstance(fwd_tm, float) or not isinstance(rev_tm, float):
        return fail("no melting temperature recorded for these lengths", **lengths)
    temperatures = {**lengths, "fwd_tm": fwd_tm, "rev_tm": rev_tm}
    if not expected["tm_min"] <= fwd_tm <= expected["tm_max"]:
        return fail("Forward primer must have a Tm between 58 and 72 degrees C.", **temperatures)
    if not expected["tm_min"] <= rev_tm <= expected["tm_max"]:
        return fail("Reverse primer must have a Tm between 58 and 72 degrees C.", **temperatures)
    if not abs(fwd_tm - rev_tm) <= expected["tm_max_difference"]:
        return fail("Tm of forward and reverse primers must be within 5 degrees C of each other.", **temperatures)
    return Judgment(True, temperatures)
