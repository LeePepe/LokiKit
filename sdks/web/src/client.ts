import { PersistentQueue } from './queue.js';
import { LokiShipper } from './shipper.js';
import type {
  Labels,
  LogLevel,
  Props,
  StorageMode,
  TelemetryEvent,
  TelemetryOptions
} from './types.js';

const DEFAULT_BATCH_SIZE = 20;
const DEFAULT_FLUSH_INTERVAL_MS = 5000;
const DEFAULT_MAX_QUEUE_SIZE = 1000;
const MAX_BACKOFF_MS = 30_000;
const RESERVED_LABELS = new Set(['event', 'level']);

/** Loki-backed telemetry client. Mirrors the Swift `LokiTelemetryService` public API. */
export class LokiTelemetry {
  readonly endpoint: string;
  readonly batchSize: number;
  readonly flushIntervalMs: number;
  readonly maxQueueSize: number;

  private readonly baseLabels: Labels;
  private readonly queue: PersistentQueue;
  private readonly shipper: LokiShipper;

  private timer: ReturnType<typeof setTimeout> | null = null;
  private backoffMs: number;
  private inflight: Promise<void> | null = null;
  private stopped = false;
  private readonly storageMode: StorageMode;

  // Browser lifecycle listeners (retained for removal on shutdown).
  private readonly onPageHide?: () => void;
  private readonly onVisibility?: () => void;

  constructor(opts: TelemetryOptions) {
    if (!opts.endpoint) throw new Error('LokiTelemetry: endpoint is required');
    this.endpoint = opts.endpoint;
    this.batchSize = opts.batchSize ?? DEFAULT_BATCH_SIZE;
    this.flushIntervalMs = opts.flushIntervalMs ?? DEFAULT_FLUSH_INTERVAL_MS;
    this.maxQueueSize = opts.maxQueueSize ?? DEFAULT_MAX_QUEUE_SIZE;
    this.storageMode = opts.storage ?? 'auto';
    this.baseLabels = sanitizeLabels(opts.labels ?? {});
    this.backoffMs = this.flushIntervalMs;

    this.queue = new PersistentQueue(this.maxQueueSize, this.storageMode, (dropped) => {
      // eslint-disable-next-line no-console
      console.warn(`[loki-web] queue overflow — dropped ${dropped} oldest event(s)`);
    });

    this.shipper = new LokiShipper({ endpoint: opts.endpoint, token: opts.token });

    // If we restored persisted events, schedule an immediate flush.
    if (this.queue.size() > 0) {
      this.scheduleTimer(0);
    } else {
      this.scheduleTimer(this.flushIntervalMs);
    }

    // Browser lifecycle hooks.
    const w = (globalThis as unknown as {
      addEventListener?: typeof addEventListener;
      document?: Document;
    });
    if (typeof w.addEventListener === 'function') {
      this.onPageHide = () => {
        this.flushViaBeaconOrFetch();
      };
      this.onVisibility = () => {
        const doc = (globalThis as unknown as { document?: Document }).document;
        if (doc && doc.visibilityState === 'hidden') this.flushViaBeaconOrFetch();
      };
      try {
        w.addEventListener('pagehide', this.onPageHide);
        w.addEventListener('visibilitychange', this.onVisibility);
      } catch {
        /* ignore (non-DOM env) */
      }
    }
  }

  /** Track an event (name becomes `event` stream label). */
  track(name: string, properties?: Props): void {
    if (this.stopped) return;
    const labels: Labels = { ...this.baseLabels, event: name };
    const line = JSON.stringify({
      t: new Date().toISOString(),
      event: name,
      ...(properties ?? {})
    });
    this.enqueue({ labels, tsNanos: nowNanos(), line });
  }

  /** Log a message (level becomes `level` stream label). */
  log(level: LogLevel, message: string, context?: Props): void {
    if (this.stopped) return;
    const labels: Labels = { ...this.baseLabels, level };
    const line = JSON.stringify({
      t: new Date().toISOString(),
      level,
      message,
      ...(context ?? {})
    });
    this.enqueue({ labels, tsNanos: nowNanos(), line });
  }

  /** Manually flush pending events. Resolves when attempt finishes (success or failure). */
  async flush(): Promise<void> {
    if (this.inflight) {
      await this.inflight;
      return;
    }
    const batch = this.queue.takeBatch(this.queue.size());
    if (batch.length === 0) return;
    this.inflight = this.sendBatch(batch);
    try {
      await this.inflight;
    } finally {
      this.inflight = null;
    }
  }

  /** Stop timer, remove listeners, flush once. */
  shutdown(): void {
    if (this.stopped) return;
    this.stopped = true;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    const w = (globalThis as unknown as { removeEventListener?: typeof removeEventListener });
    if (typeof w.removeEventListener === 'function') {
      try {
        if (this.onPageHide) w.removeEventListener('pagehide', this.onPageHide);
        if (this.onVisibility) w.removeEventListener('visibilitychange', this.onVisibility);
      } catch {
        /* ignore */
      }
    }
    // Fire-and-forget final flush.
    void this.flush().catch(() => {
      /* swallow — shutdown must not throw */
    });
  }

  // ------------------------------------------------------------------ private

  private enqueue(ev: TelemetryEvent): void {
    this.queue.enqueue(ev);
    if (this.queue.size() >= this.batchSize) {
      void this.flush().catch(() => {
        /* handled via backoff */
      });
    }
  }

  private async sendBatch(batch: TelemetryEvent[]): Promise<void> {
    try {
      await this.shipper.ship(batch);
      // Success — reset backoff.
      this.backoffMs = this.flushIntervalMs;
      this.scheduleTimer(this.flushIntervalMs);
    } catch (err) {
      // Put events back at the front and back off.
      this.queue.requeueFront(batch);
      this.backoffMs = Math.min(MAX_BACKOFF_MS, Math.max(this.flushIntervalMs, this.backoffMs * 2));
      // eslint-disable-next-line no-console
      console.warn(`[loki-web] flush failed, retrying in ${this.backoffMs}ms`, err);
      this.scheduleTimer(this.backoffMs);
    }
  }

  private scheduleTimer(delay: number): void {
    if (this.stopped) return;
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => {
      this.timer = null;
      void this.flush().catch(() => {
        /* handled */
      });
    }, delay);
    // Node: allow process to exit if this is the only thing pending.
    const t = this.timer as unknown as { unref?: () => void };
    if (typeof t?.unref === 'function') t.unref();
  }

  /** Browser lifecycle handler: prefer sendBeacon, else best-effort fetch. */
  private flushViaBeaconOrFetch(): void {
    const batch = this.queue.takeBatch(this.queue.size());
    if (batch.length === 0) return;
    const sent = this.shipper.shipBeacon(batch);
    if (sent) return;
    // Fallback to normal flush path (fire-and-forget).
    this.queue.requeueFront(batch);
    void this.flush().catch(() => {
      /* ignore */
    });
  }
}

function sanitizeLabels(labels: Labels): Labels {
  const out: Labels = {};
  for (const [k, v] of Object.entries(labels)) {
    if (RESERVED_LABELS.has(k)) {
      // eslint-disable-next-line no-console
      console.warn(`[loki-web] ignoring reserved label "${k}" in constructor labels`);
      continue;
    }
    out[k] = String(v);
  }
  return out;
}

function nowNanos(): string {
  // Millisecond precision is sufficient for Loki; pad to nanoseconds.
  const ms = Date.now();
  return `${ms}000000`;
}
