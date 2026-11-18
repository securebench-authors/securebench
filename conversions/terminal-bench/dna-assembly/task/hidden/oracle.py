"""Oracle for terminal-bench/dna-assembly.

The candidate's only deliverable is /app/primers.fasta. The artifact check
`primers` reads it as UTF-8 text, and `judge` repeats upstream's
`test_primers` (tests/test_outputs.py) on it, with each `assert` turned into
a failed judgment carrying the assertion's message.

Upstream computes melting temperatures by running primer3's `oligotm`
(Ubuntu 24.04 package primer3 2.6.1). The Evaluation has no network and the
baseline has no primer3, and a Tm computed inside the Evaluation would be
candidate-controlled anyway, so `_oligotm` below reimplements the one code
path upstream's flags reach (`-tp 1 -sc 1 -mv 50 -dv 2 -n 0.8 -d 500`): the
SantaLucia 1998 nearest-neighbour model with SantaLucia salt correction, as
in primer3 2.6.1 src/oligotm.c. CONVERSION.md records how it was checked
against the native binary on every input it can ever receive.

The template and target sequences are upstream's test literals and live in
hidden/templates.json.
"""

import math

from securebench.core.evidence import ArtifactEvidence, CaseEvidence, FileStatus, HiddenResources, Judgment, Plan, Text
from securebench.core.jsondata import JsonValue

REQUIRED = ("input_fwd", "input_rev", "egfp_fwd", "egfp_rev", "flag_fwd", "flag_rev", "snap_fwd", "snap_rev")

# SantaLucia 1998 nearest-neighbour parameters, keyed by the 5'->3' pair on
# one strand, in the units primer3 uses: delta H in 100 cal/mol (DH_X_Y in
# oligotm.c) and delta S in 0.1 cal/(K mol) (DS_X_Y), both as disruption
# energies (positive).
_DH = {
    "aa": 79, "ac": 84, "ag": 78, "at": 72,
    "ca": 85, "cc": 80, "cg": 106, "ct": 78,
    "ga": 82, "gc": 98, "gg": 80, "gt": 84,
    "ta": 72, "tc": 82, "tg": 85, "tt": 79,
}  # fmt: skip
_DS = {
    "aa": 222, "ac": 224, "ag": 210, "at": 204,
    "ca": 227, "cc": 199, "cg": 272, "ct": 210,
    "ga": 222, "gc": 244, "gg": 199, "gt": 224,
    "ta": 213, "tc": 222, "tg": 227, "tt": 222,
}  # fmt: skip


class _Fail(Exception):
    """An upstream assertion failed; the argument is its message."""


def plan(resources: HiddenResources, seed: int) -> Plan:
    return Plan(artifact_contexts={"primers": resources.read_json("templates.json")}, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != "primers" or not isinstance(evidence, ArtifactEvidence) or len(evidence.files) != 1:
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(context, dict) or any(not isinstance(context.get(k), str) for k in ("input", "egfp", "flag", "snap", "output")):
        return Judgment(False, {"reason": "malformed context"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        return Judgment(False, {"reason": f"/app/primers.fasta is {found.status.value}"})
    try:
        _test_primers(found.value.text, context)
    except _Fail as failure:
        return Judgment(False, {"reason": str(failure)})
    return Judgment(True, None)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise _Fail(message)


def _file_lines(text: str) -> list[str]:
    """The lines upstream gets from `[line.rstrip() for line in open(path, "r")]`.

    Text mode uses universal newlines: `\\r\\n` and a lone `\\r` both end a
    line, and nothing else does. The parser's own `lines` split on `\\n` only,
    so we split the raw text here instead.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines[-1] == "":
        lines.pop()
    return [line.rstrip() for line in lines]


def _rc(seq: str) -> str:
    return seq.translate(str.maketrans("acgt", "tgca"))[::-1]


def _oligotm(seq: str) -> float:
    """`oligotm -tp 1 -sc 1 -mv 50 -dv 2 -n 0.8 -d 500 <seq>`, as the test parses it.

    `seq` is a lowercase a/c/g/t template substring of 15 to 45 bases (the
    only inputs upstream's test can pass). The arithmetic follows oligotm.c
    operation by operation so that the doubles agree bit for bit; the DMSO
    and formamide terms are omitted because with their zero defaults they
    add exactly zero.
    """
    dh = 0
    ds = 0
    symmetric = len(seq) % 2 == 0 and seq == _rc(seq)
    if symmetric:
        ds += 14
    for end in (seq[0], seq[-1]):
        if end in ("a", "t"):
            ds += -41
            dh += -23
        else:
            ds += 28
            dh += -1
    for i in range(len(seq) - 1):
        pair = seq[i : i + 2]
        dh += _DH[pair]
        ds += _DS[pair]
    delta_h = dh * -100.0
    delta_s = ds * -0.1
    k_mm = 50.0 + 120 * math.sqrt(2.0 - 0.8)
    delta_s = delta_s + 0.368 * (len(seq) - 1) * math.log(k_mm / 1000.0)
    dna_nm = 500.0
    if symmetric:
        tm = delta_h / (delta_s + 1.987 * math.log(dna_nm / 1000000000.0)) - 273.15
    else:
        tm = delta_h / (delta_s + 1.987 * math.log(dna_nm / 4000000000.0)) - 273.15
    # oligotm prints "%f\n" and the test reads it back with float().
    return float(f"{tm:.6f}")


def _parse_bsai_primer(primer: str) -> tuple[str, str]:
    """Primer (5'->3'): [clamp] ggtctc [n] [oooo] [binding]"""
    site = "ggtctc"
    i = primer.find(site)
    _require(i != -1, "BsaI site ggtctc not found in primer")
    _require(i >= 1, "Primer must have clamp of at least 1 nucleotide before BsaI site.")
    j = i + len(site) + 1
    _require(
        len(primer) >= j + 5,
        "Primer must have 4 nucleotide overhang + 1 nucleotide padding +annealing site after ggtctc.",
    )
    overhang = primer[j : j + 4]
    binding = primer[j + 4 :]
    return overhang, binding


def _make_fragment(template: str, fwd_primer: str, rev_primer: str, circular: bool = False) -> tuple[str, str, str]:
    f_oh, f_bind = _parse_bsai_primer(fwd_primer)
    r_oh, r_bind = _parse_bsai_primer(rev_primer)
    r_bind_rc = _rc(r_bind)

    if circular:
        template += template

    s = template.find(f_bind)
    _require(s != -1, "Forward primer must match an annealing site.")
    start_after = s + len(f_bind)

    e = template.find(r_bind_rc, start_after)
    _require(e != -1, "Reverse primer must match an annealing site downstream of the forward primer.")

    kfmax = min(4, s)
    kf = next((k for k in range(kfmax, 0, -1) if template[s - k : s] == f_oh[-k:]), 0)
    extra_f = template[s - kf : s + len(f_bind)]

    pos_right = e + len(r_bind_rc)
    krmax = min(4, len(template) - pos_right)
    kr = next(
        (k for k in range(krmax, 0, -1) if template[pos_right : pos_right + k] == _rc(r_oh[-k:])),
        0,
    )
    extra_r = template[e : pos_right + kr]

    _require(15 <= len(extra_f) <= 45, "Forward primer annealing (incl. overhang match) must be 15–45 nt.")
    _require(15 <= len(extra_r) <= 45, "Reverse primer annealing (incl. overhang match) must be 15–45 nt.")

    fwd_tm = _oligotm(extra_f)
    rev_tm = _oligotm(extra_r)
    _require(58 <= fwd_tm <= 72, "Forward primer must have a Tm between 58 and 72 degrees C.")
    _require(58 <= rev_tm <= 72, "Reverse primer must have a Tm between 58 and 72 degrees C.")
    _require(abs(fwd_tm - rev_tm) <= 5, "Tm of forward and reverse primers must be within 5 degrees C of each other.")

    between = template[start_after:e]
    internal = f_bind + between + r_bind_rc
    return f_oh, internal, r_oh


def _test_primers(text: str, templates: dict[str, JsonValue]) -> None:
    lines = _file_lines(text)
    _require(len(lines) == 16, "Invalid number of lines in primers.fasta.")

    primers: dict[str, str] = {}
    for i in range(0, len(lines), 2):
        primer = lines[i + 1].lower()
        _require(lines[i].startswith(">"), "Headers must start with >.")
        # Upstream: re.fullmatch(r"[atcg]+", primer).
        _require(primer != "" and all(c in "atcg" for c in primer), "Primer must contain only A, T, C, G.")
        primers[lines[i][1:]] = lines[i + 1].lower()

    _require(all(k in primers for k in REQUIRED), "primers.fasta file is missing a primer for a valid solution.")

    vector, egfp, flag, snap, output = (str(templates[k]) for k in ("input", "egfp", "flag", "snap", "output"))
    vector_left, vector_internal, vector_right = _make_fragment(vector, primers["input_fwd"], primers["input_rev"], circular=True)
    egfp_left, egfp_internal, egfp_right = _make_fragment(egfp, primers["egfp_fwd"], primers["egfp_rev"])
    flag_left, flag_internal, flag_right = _make_fragment(flag, primers["flag_fwd"], primers["flag_rev"])
    snap_left, snap_internal, snap_right = _make_fragment(snap, primers["snap_fwd"], primers["snap_rev"])

    _require(egfp_left == _rc(vector_right), "Overhang mismatch: egfp.left != rc(vector.right)")
    _require(flag_left == _rc(egfp_right), "Overhang mismatch: flag.left != rc(egfp.right)")
    _require(snap_left == _rc(flag_right), "Overhang mismatch: snap.left != rc(flag.right)")
    _require(vector_left == _rc(snap_right), "Overhang mismatch: vector.left != rc(snap.right) (closure)")

    _require(len({vector_right, egfp_right, flag_right, snap_right}) == 4, "Junction overhangs must be unique.")

    assembled = vector_left + vector_internal + egfp_left + egfp_internal + flag_left + flag_internal + snap_left + snap_internal
    _require(assembled in output + output, "Assembled sequence does not match expected output.")
