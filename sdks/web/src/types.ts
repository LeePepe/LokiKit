export type LogLevel =
  | 'debug'
  | 'performance'
  | 'info'
  | 'warning'
  | 'error'
  | 'critical';

export type Labels = Record<string, string>;

export type Props = Record<string, unknown>;

/** Storage backend selection. 'auto' uses localStorage when available, memory otherwise. */
export type StorageMode = 'auto' | 'localStorage' | 'memory';

/** A buffered telemetry event. */
export interface TelemetryEvent {
  /** Stream labels (merged over constructor labels). */
  labels: Labels;
  /** Epoch nanoseconds (string, to avoid precision loss). */
  tsNanos: string;
  /** The Loki log line (JSON-encoded string). */
  line: string;
}

export interface TelemetryOptions {
  endpoint: string;
  labels?: Labels;
  token?: string;
  batchSize?: number;
  flushIntervalMs?: number;
  maxQueueSize?: number;
  storage?: StorageMode;
}

/** Loki push wire format types. */
export interface LokiStream {
  stream: Labels;
  values: [string, string][];
}

export interface LokiPushBody {
  streams: LokiStream[];
}
