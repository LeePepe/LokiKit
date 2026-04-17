import { beforeEach, describe, expect, it } from 'vitest';
import { PersistentQueue, STORAGE_KEY } from '../src/queue.js';
import type { TelemetryEvent } from '../src/types.js';

function ev(name: string): TelemetryEvent {
  return {
    labels: { app: 'T', event: name },
    tsNanos: '1700000000000000000',
    line: JSON.stringify({ event: name })
  };
}

describe('PersistentQueue', () => {
  beforeEach(() => {
    try {
      const g = globalThis as unknown as {
        window?: { localStorage?: Storage };
        localStorage?: Storage;
      };
      const ls = g.window?.localStorage ?? g.localStorage;
      if (ls && typeof ls.clear === 'function') ls.clear();
    } catch {
      /* ignore */
    }
  });

  it('memory backend: enqueue/drain roundtrip', () => {
    const q = new PersistentQueue(10, 'memory');
    q.enqueue(ev('a'));
    q.enqueue(ev('b'));
    expect(q.size()).toBe(2);
    const all = q.drain();
    expect(all.map((e) => e.labels.event)).toEqual(['a', 'b']);
    expect(q.size()).toBe(0);
  });

  it('drops oldest when exceeding maxSize', () => {
    const dropped: number[] = [];
    const q = new PersistentQueue(2, 'memory', (n) => dropped.push(n));
    q.enqueue(ev('a'));
    q.enqueue(ev('b'));
    q.enqueue(ev('c'));
    expect(q.size()).toBe(2);
    expect(q.snapshot().map((e) => e.labels.event)).toEqual(['b', 'c']);
    expect(dropped.reduce((a, b) => a + b, 0)).toBe(1);
  });

  it('localStorage: persists and restores across instances', () => {
    // In happy-dom env, window.localStorage is functional; in plain Node's
    // experimental localStorage it isn't. Detect a real backend and skip otherwise.
    const g = globalThis as unknown as {
      window?: { localStorage?: Storage };
      localStorage?: Storage;
    };
    const candidate = g.window?.localStorage ?? g.localStorage;
    if (!candidate || typeof candidate.getItem !== 'function') return;
    // Make sure the queue picks up this exact Storage.
    g.localStorage = candidate;

    const q1 = new PersistentQueue(100, 'localStorage');
    q1.enqueue(ev('persist-1'));
    q1.enqueue(ev('persist-2'));
    expect(candidate.getItem(STORAGE_KEY)).toBeTruthy();

    const q2 = new PersistentQueue(100, 'localStorage');
    expect(q2.size()).toBe(2);
    const drained = q2.drain();
    expect(drained.map((e) => e.labels.event)).toEqual(['persist-1', 'persist-2']);
    expect(candidate.getItem(STORAGE_KEY)).toBeNull();
  });

  it('takeBatch and requeueFront preserve ordering for retries', () => {
    const q = new PersistentQueue(10, 'memory');
    q.enqueue(ev('a'));
    q.enqueue(ev('b'));
    q.enqueue(ev('c'));
    const batch = q.takeBatch(2);
    expect(batch.map((e) => e.labels.event)).toEqual(['a', 'b']);
    expect(q.snapshot().map((e) => e.labels.event)).toEqual(['c']);
    q.requeueFront(batch);
    expect(q.snapshot().map((e) => e.labels.event)).toEqual(['a', 'b', 'c']);
  });
});
