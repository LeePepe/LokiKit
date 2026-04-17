import type { Labels, LokiPushBody, LokiStream, TelemetryEvent } from './types.js';

export interface ShipperOptions {
  endpoint: string;
  token?: string;
}

export class LokiShipper {
  constructor(private readonly opts: ShipperOptions) {}

  /** POST events via fetch. Throws on network failure or non-2xx. */
  async ship(events: TelemetryEvent[]): Promise<void> {
    if (events.length === 0) return;
    const body = buildPushBody(events);
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    if (this.opts.token) headers.Authorization = `Bearer ${this.opts.token}`;

    const res = await fetch(this.opts.endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      keepalive: false
    });
    if (!res.ok) {
      throw new Error(`Loki HTTP error: ${res.status}`);
    }
  }

  /** Best-effort fire-and-forget used from pagehide. Returns true if sent. */
  shipBeacon(events: TelemetryEvent[]): boolean {
    if (events.length === 0) return true;
    const nav = (globalThis as { navigator?: Navigator }).navigator;
    if (!nav || typeof nav.sendBeacon !== 'function') return false;
    if (this.opts.token) {
      // sendBeacon cannot set Authorization headers — skip to let fetch path handle it.
      return false;
    }
    try {
      const body = JSON.stringify(buildPushBody(events));
      const blob = new Blob([body], { type: 'application/json' });
      return nav.sendBeacon(this.opts.endpoint, blob);
    } catch {
      return false;
    }
  }
}

export function buildPushBody(events: TelemetryEvent[]): LokiPushBody {
  // Group events by canonical label signature so same-label events share a stream.
  const groups = new Map<string, { labels: Labels; values: [string, string][] }>();
  for (const ev of events) {
    const key = canonicalKey(ev.labels);
    let g = groups.get(key);
    if (!g) {
      g = { labels: ev.labels, values: [] };
      groups.set(key, g);
    }
    g.values.push([ev.tsNanos, ev.line]);
  }
  const streams: LokiStream[] = [];
  for (const g of groups.values()) {
    streams.push({ stream: g.labels, values: g.values });
  }
  return { streams };
}

function canonicalKey(labels: Labels): string {
  const keys = Object.keys(labels).sort();
  return keys.map((k) => `${k}=${labels[k]}`).join('\u0001');
}
