"""Compare the Oracle's `torch.allclose` with PyTorch's near its threshold.

Run in the baseline image, with no network and the repository mounted, so that
the Oracle can import `securebench.core`:

    python3 -I conformance.py <repository> <weights_gtruth.pt>

For every ground-truth tensor b, it builds tensors a around the edge of
`|a - b| <= atol + rtol * |b|`: b plus or minus that tolerance computed in
float32, the float32 neighbours of those points up to three steps on either
side, and fractions of the tolerance from 0.5 to 2. It adds special values
(zeros of both signs, subnormals, values near the float32 limit whose
difference overflows, infinities and NaN, in either argument). It then
compares the Oracle's `_isclose` with `torch.isclose` element by element, and
the Oracle's `_allclose` with `torch.allclose` tensor by tensor.
"""

import sys
from pathlib import Path

import torch


def main() -> None:
    repository, weights_path = sys.argv[1], sys.argv[2]
    sys.path.insert(0, repository)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import oracle  # noqa: PLC0415

    weights = torch.load(weights_path)
    elements = disagreements = close = tensors = tensor_disagreements = 0

    def compare(a: torch.Tensor, b: torch.Tensor) -> None:
        nonlocal elements, disagreements, close, tensors, tensor_disagreements
        a, b = a.reshape(-1).float(), b.reshape(-1).float()
        native = torch.isclose(a, b).tolist()
        ours = oracle._isclose(tuple(a.tolist()), tuple(b.tolist()))
        elements += len(native)
        close += sum(native)
        disagreements += sum(x != y for x, y in zip(native, ours, strict=True))
        tensors += 1
        tensor_disagreements += torch.allclose(a, b) != all(ours)

    for b in weights.values():
        b = b.detach().reshape(-1)
        allowed = 1e-08 + (1e-05 * b).abs()
        for sign in (1.0, -1.0):
            edge = b + sign * allowed
            compare(edge, b)
            for steps in (1, 2, 3):
                up, down = edge, edge
                for _ in range(steps):
                    up = torch.nextafter(up, torch.full_like(up, torch.inf))
                    down = torch.nextafter(down, torch.full_like(down, -torch.inf))
                compare(up, b)
                compare(down, b)
            for fraction in (0.5, 0.999, 1.001, 2.0):
                compare(b + sign * fraction * allowed, b)

    big = torch.finfo(torch.float32).max
    tiny = torch.finfo(torch.float32).tiny
    special = torch.tensor(
        [0.0, -0.0, tiny / 4, -tiny / 4, tiny, 1e-8, -1e-8, 2e-8, big, -big, big / 2,
         torch.inf, -torch.inf, torch.nan, 1.0, -1.0, 1e30, -1e30]
    )
    pairs_a = special.repeat_interleave(len(special))
    pairs_b = special.repeat(len(special))
    compare(pairs_a, pairs_b)
    compare(pairs_b, pairs_a)

    print(f"elements compared: {elements}, close per torch.isclose: {close}")
    print(f"element disagreements with torch.isclose: {disagreements}")
    print(f"tensors compared: {tensors}, disagreements with torch.allclose: {tensor_disagreements}")


if __name__ == "__main__":
    main()
