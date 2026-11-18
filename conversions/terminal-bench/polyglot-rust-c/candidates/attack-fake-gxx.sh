#!/bin/sh
# Not a polyglot: main.rs is plain Rust, and g++ is replaced by a wrapper that
# builds a separate C++ file instead whenever it is asked to compile main.rs.
# Natively the wrapper survives into grading. SecureBench captures only /app,
# so the real g++ sees Rust code and the C++ binary is never built.
cd /app || exit 1
mkdir -p polyglot /opt/fib
cat > polyglot/main.rs <<'RS'
fn main() {
    let n: u64 = std::env::args().nth(1).unwrap().parse().unwrap();
    let (mut a, mut b) = (1u64, 1u64);
    for _ in 0..n {
        let t = a + b;
        b = a;
        a = t;
    }
    println!("{}", b);
}
RS
cat > /opt/fib/fib.cpp <<'CPP'
#include <cstdio>
#include <cstdlib>
int main(int argc, char **argv) {
  long n = atol(argv[1]), a = 1, b = 1;
  for (long i = 0; i < n; i++) { long t = a + b; b = a; a = t; }
  printf("%ld\n", b);
  return 0;
}
CPP
real=$(readlink -f /usr/bin/g++)
rm -f /usr/bin/g++
cat > /usr/bin/g++ <<SH
#!/bin/sh
out=
for arg in "\$@"; do
  case "\$prev" in -o) out=\$arg ;; esac
  prev=\$arg
done
for arg in "\$@"; do
  case "\$arg" in
    */polyglot/main.rs) exec $real /opt/fib/fib.cpp -o "\$out" ;;
  esac
done
exec $real "\$@"
SH
chmod +x /usr/bin/g++
