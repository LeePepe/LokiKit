# @leepepe/loki-web

TypeScript Web SDK for Grafana Loki telemetry. Mirrors the
[Swift LokiKit](../swift) API. Zero runtime dependencies; works in evergreen
browsers and Node 18+.

## Install

    npm install @leepepe/loki-web

## Quick Start

    import { LokiTelemetry, PrintLogger } from '@leepepe/loki-web';

    const t = new LokiTelemetry({
      endpoint: 'http://localhost:3100/loki/api/v1/push',
      labels:   { app: 'Financial', env: 'dev' },
      token:    undefined,        // Grafana Cloud: "<user>:<apikey>" base64
      batchSize: 20,
      flushIntervalMs: 5000,
      maxQueueSize: 1000,
      storage: 'auto',            // 'auto' | 'localStorage' | 'memory'
    });

    t.track('recording.started', { provider: 'whisper' });
    t.log('info', 'app.started', { user: 'tianpli' });

    await t.flush();
    t.shutdown();

    const log = new PrintLogger('MyApp');
    log.info('hello', { k: 'v' });
    log.error(new Error('boom'));

## API

    LokiTelemetry(options)
      options.endpoint         string  required    Loki push URL
      options.labels           Labels  optional    attached to every stream
      options.token            string  optional    Bearer token (Authorization)
      options.batchSize        number  20          events per batch
      options.flushIntervalMs  number  5000        timer interval
      options.maxQueueSize     number  1000        drop-oldest ceiling
      options.storage          mode    'auto'      'auto'|'localStorage'|'memory'

    t.track(name, props?)                emits stream label event=name
    t.log(level, message, context?)      emits stream label level=<level>
    t.flush(): Promise<void>             manual flush
    t.shutdown()                         stop timer + flush once

    PrintLogger(subsystem?, minimumLevel?='debug')
      .debug / .info / .warning / .error / .critical

LogLevel: debug | performance | info | warning | error | critical

## Behavior

- In-memory FIFO queue up to `maxQueueSize`; overflow drops oldest and logs a
  console warning.
- Flush triggers: `batchSize` reached, `flushIntervalMs` timer, manual
  `flush()`, `shutdown()`, and — in browsers — `pagehide` /
  `visibilitychange→hidden`. The lifecycle handlers prefer
  `navigator.sendBeacon` when available (falls back to the regular fetch path
  when a Bearer token is configured, since Beacon cannot set Authorization).
- Retry: failed POST → events are put back at the front of the queue; the
  timer backs off exponentially, capped at 30s.
- Persistence: `storage: 'auto'` uses `localStorage` in browsers and memory in
  Node. Persisted events are replayed on construction.
- Reserved labels `event` and `level` cannot be set via constructor `labels`.

## Node vs Browser

- Uses global `fetch` (Node 18+ / evergreen browsers). No `node-fetch`.
- Persistence defaults to memory in Node. Pass `storage: 'localStorage'` only
  in browser environments.
- Lifecycle flush (`pagehide`) is a no-op when there's no `window`/DOM.

## Grafana Cloud

Set `endpoint` to your Grafana Cloud push URL and pass `token` as the base64
encoded `<user>:<apikey>` string. The wire format is identical to self-hosted
Loki.

## Repo

Part of [LokiKit](../..).
