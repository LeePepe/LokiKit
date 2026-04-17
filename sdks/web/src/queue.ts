import type { StorageMode, TelemetryEvent } from './types.js';

export const STORAGE_KEY = 'loki-web:queue';

interface StorageBackend {
  load(): TelemetryEvent[];
  save(events: TelemetryEvent[]): void;
  clear(): void;
}

class MemoryBackend implements StorageBackend {
  load(): TelemetryEvent[] {
    return [];
  }
  save(_events: TelemetryEvent[]): void {
    /* no-op */
  }
  clear(): void {
    /* no-op */
  }
}

class LocalStorageBackend implements StorageBackend {
  constructor(private readonly storage: Storage, private readonly key: string) {}
  load(): TelemetryEvent[] {
    try {
      const raw = this.storage.getItem(this.key);
      if (!raw) return [];
      const parsed = JSON.parse(raw) as unknown;
      if (!Array.isArray(parsed)) return [];
      return parsed as TelemetryEvent[];
    } catch {
      return [];
    }
  }
  save(events: TelemetryEvent[]): void {
    try {
      if (events.length === 0) {
        this.storage.removeItem(this.key);
      } else {
        this.storage.setItem(this.key, JSON.stringify(events));
      }
    } catch {
      /* quota or disabled — ignore */
    }
  }
  clear(): void {
    try {
      this.storage.removeItem(this.key);
    } catch {
      /* ignore */
    }
  }
}

function getLocalStorage(): Storage | null {
  try {
    const w = globalThis as unknown as {
      window?: { localStorage?: Storage };
      localStorage?: Storage;
    };
    const candidate = w.window?.localStorage ?? w.localStorage;
    if (!candidate) return null;
    if (typeof candidate.getItem !== 'function' || typeof candidate.setItem !== 'function') {
      return null;
    }
    return candidate;
  } catch {
    return null;
  }
}

function hasLocalStorage(): boolean {
  return getLocalStorage() !== null;
}
void hasLocalStorage; // keep for potential external reuse

function resolveBackend(mode: StorageMode): StorageBackend {
  if (mode === 'memory') return new MemoryBackend();
  const ls = getLocalStorage();
  if (mode === 'localStorage') {
    if (!ls) return new MemoryBackend();
    return new LocalStorageBackend(ls, STORAGE_KEY);
  }
  // auto
  if (ls) return new LocalStorageBackend(ls, STORAGE_KEY);
  return new MemoryBackend();
}

/** Bounded FIFO queue with optional persistence. */
export class PersistentQueue {
  private buf: TelemetryEvent[] = [];
  private readonly backend: StorageBackend;

  constructor(
    private readonly maxSize: number,
    mode: StorageMode,
    private readonly onDrop?: (count: number) => void
  ) {
    this.backend = resolveBackend(mode);
    this.buf = this.backend.load();
    this.enforceLimit();
    this.persist();
  }

  size(): number {
    return this.buf.length;
  }

  enqueue(event: TelemetryEvent): void {
    this.buf.push(event);
    this.enforceLimit();
    this.persist();
  }

  /** Put events back at the front (retry path). */
  requeueFront(events: TelemetryEvent[]): void {
    this.buf = events.concat(this.buf);
    this.enforceLimit();
    this.persist();
  }

  /** Remove and return up to `n` events from the head. */
  takeBatch(n: number): TelemetryEvent[] {
    const take = Math.min(n, this.buf.length);
    const out = this.buf.splice(0, take);
    this.persist();
    return out;
  }

  /** Remove and return all events. */
  drain(): TelemetryEvent[] {
    const out = this.buf;
    this.buf = [];
    this.backend.clear();
    return out;
  }

  /** Snapshot without removing. */
  snapshot(): TelemetryEvent[] {
    return this.buf.slice();
  }

  private enforceLimit(): void {
    if (this.buf.length <= this.maxSize) return;
    const drop = this.buf.length - this.maxSize;
    this.buf.splice(0, drop);
    this.onDrop?.(drop);
  }

  private persist(): void {
    this.backend.save(this.buf);
  }
}
