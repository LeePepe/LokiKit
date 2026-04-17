import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PrintLogger } from '../src/logger.js';

describe('PrintLogger', () => {
  let logSpy: ReturnType<typeof vi.fn>;
  let errSpy: ReturnType<typeof vi.fn>;
  let warnSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    logSpy = vi.spyOn(console, 'log').mockImplementation(() => {}) as unknown as ReturnType<typeof vi.fn>;
    errSpy = vi.spyOn(console, 'error').mockImplementation(() => {}) as unknown as ReturnType<typeof vi.fn>;
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {}) as unknown as ReturnType<typeof vi.fn>;
    vi.spyOn(console, 'debug').mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('emits info with context', () => {
    const log = new PrintLogger('MyApp');
    log.info('hello', { k: 'v' });
    expect(logSpy).toHaveBeenCalledTimes(1);
    const line = logSpy.mock.calls[0]![0] as string;
    expect(line).toContain('INFO');
    expect(line).toContain('[MyApp]');
    expect(line).toContain('hello');
    expect(line).toContain('k=v');
  });

  it('honors minimumLevel', () => {
    const log = new PrintLogger('', 'warning');
    log.info('skip');
    log.warning('keep');
    expect(logSpy).not.toHaveBeenCalled();
    expect(warnSpy).toHaveBeenCalledTimes(1);
  });

  it('error(Error) captures message and stack', () => {
    const log = new PrintLogger();
    log.error(new Error('boom'));
    expect(errSpy).toHaveBeenCalledTimes(1);
    const line = errSpy.mock.calls[0]![0] as string;
    expect(line).toContain('ERROR');
    expect(line).toContain('boom');
    expect(line).toMatch(/stack=/);
  });

  it('sorts context keys alphabetically', () => {
    const log = new PrintLogger();
    log.info('m', { z: 1, a: 2 });
    const line = logSpy.mock.calls[0]![0] as string;
    expect(line.indexOf('a=2')).toBeLessThan(line.indexOf('z=1'));
  });
});
