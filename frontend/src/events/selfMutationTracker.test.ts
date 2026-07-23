import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { markSelfMutated, wasSelfMutated } from './selfMutationTracker'

describe('selfMutationTracker', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(0)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('reports an id as self-mutated right after marking it', () => {
    markSelfMutated('node-1')
    expect(wasSelfMutated('node-1')).toBe(true)
  })

  it('reports unmarked ids as not self-mutated', () => {
    expect(wasSelfMutated('never-marked')).toBe(false)
  })

  it('expires after the TTL window', () => {
    markSelfMutated('node-2')
    vi.setSystemTime(5001)
    expect(wasSelfMutated('node-2')).toBe(false)
  })

  it('stays true just under the TTL window', () => {
    markSelfMutated('node-3')
    vi.setSystemTime(4999)
    expect(wasSelfMutated('node-3')).toBe(true)
  })
})
