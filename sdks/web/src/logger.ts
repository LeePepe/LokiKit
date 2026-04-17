import type { LogLevel } from './types.js';

/** Minimal logger contract (mirrors Swift `Logger`). */
export interface Logger {
  minimumLevel: LogLevel;
  log(level: LogLevel, message: string, context?: Record<string, unknown>): void;
  debug(message: string, context?: Record<string, unknown>): void;
  info(message: string, context?: Record<string, unknown>): void;
  warning(message: string, context?: Record<string, unknown>): void;
  error(message: string | Error, context?: Record<string, unknown>): void;
  critical(message: string | Error, context?: Record<string, unknown>): void;
}

const LEVEL_ORDER: Record<LogLevel, number> = {
  debug: 0,
  performance: 1,
  info: 2,
  warning: 3,
  error: 4,
  critical: 5
};

const LEVEL_SYMBOL: Record<LogLevel, string> = {
  debug: '🔍',
  performance: '⏱️',
  info: 'ℹ️',
  warning: '⚠️',
  error: '❌',
  critical: '🔥'
};

const LEVEL_NAME: Record<LogLevel, string> = {
  debug: 'DEBUG',
  performance: 'PERF',
  info: 'INFO',
  warning: 'WARNING',
  error: 'ERROR',
  critical: 'CRITICAL'
};

/** Console-based logger. Mirrors Swift `PrintLogger`. */
export class PrintLogger implements Logger {
  public minimumLevel: LogLevel;
  private readonly subsystem: string;

  constructor(subsystem: string = '', minimumLevel: LogLevel = 'debug') {
    this.subsystem = subsystem;
    this.minimumLevel = minimumLevel;
  }

  log(level: LogLevel, message: string, context?: Record<string, unknown>): void {
    if (LEVEL_ORDER[level] < LEVEL_ORDER[this.minimumLevel]) return;

    const ts = new Date().toISOString();
    const prefix = this.subsystem ? `[${this.subsystem}] ` : '';
    const msg = normalize(message);
    const head = `${LEVEL_SYMBOL[level]} ${ts} ${prefix}${LEVEL_NAME[level]} - ${msg}`;

    if (context && Object.keys(context).length > 0) {
      const ctx = Object.entries(context)
        .map(([k, v]) => [k, normalize(stringify(v))] as [string, string])
        .sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
        .map(([k, v]) => `${k}=${v}`)
        .join(', ');
      emit(level, `${head} | ${ctx}`);
    } else {
      emit(level, head);
    }
  }

  debug(message: string, context?: Record<string, unknown>): void {
    this.log('debug', message, context);
  }
  info(message: string, context?: Record<string, unknown>): void {
    this.log('info', message, context);
  }
  warning(message: string, context?: Record<string, unknown>): void {
    this.log('warning', message, context);
  }
  error(message: string | Error, context?: Record<string, unknown>): void {
    const { msg, ctx } = fromError(message, context);
    this.log('error', msg, ctx);
  }
  critical(message: string | Error, context?: Record<string, unknown>): void {
    const { msg, ctx } = fromError(message, context);
    this.log('critical', msg, ctx);
  }
}

function normalize(s: string): string {
  return s.replace(/\n/g, '\\n').replace(/\r/g, '\\r');
}

function stringify(v: unknown): string {
  if (v === null) return 'null';
  if (v === undefined) return 'undefined';
  if (typeof v === 'string') return v;
  if (typeof v === 'number' || typeof v === 'boolean') return String(v);
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

function fromError(
  message: string | Error,
  context?: Record<string, unknown>
): { msg: string; ctx: Record<string, unknown> | undefined } {
  if (message instanceof Error) {
    const ctx: Record<string, unknown> = { ...(context ?? {}) };
    if (message.stack) ctx.stack = message.stack;
    if (message.name) ctx.errorName = message.name;
    return { msg: message.message, ctx };
  }
  return { msg: message, ctx: context };
}

function emit(level: LogLevel, line: string): void {
  switch (level) {
    case 'error':
    case 'critical':
      console.error(line);
      break;
    case 'warning':
      console.warn(line);
      break;
    case 'debug':
      console.debug(line);
      break;
    default:
      console.log(line);
  }
}
