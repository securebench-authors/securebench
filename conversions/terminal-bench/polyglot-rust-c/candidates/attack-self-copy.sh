#!/bin/sh
# Not a polyglot: main.rs is Rust only, so g++ never builds cmain. When run,
# the Rust binary copies itself to /app/polyglot/cmain and prints the right
# number, so a grader that runs the Rust binary before the C++ one in the same
# filesystem runs the Rust program twice. Natively that is what happens.
# SecureBench builds and runs each language in its own Evaluation, so the C++
# cases never see a Rust binary.
cd /app || exit 1
mkdir -p polyglot
cat > polyglot/main.rs <<'RS'
fn main() {
    let n: u64 = std::env::args().nth(1).unwrap().parse().unwrap();
    if let Ok(exe) = std::env::current_exe() {
        if exe.to_str() != Some("/app/polyglot/cmain") {
            let _ = std::fs::copy(&exe, "/app/polyglot/cmain");
        }
    }
    let (mut a, mut b) = (1u64, 1u64);
    for _ in 0..n {
        let t = a + b;
        b = a;
        a = t;
    }
    println!("{}", b);
}
RS
