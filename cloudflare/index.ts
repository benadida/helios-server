import { DurableObject } from 'cloudflare:workers';
import { Container } from '@cloudflare/containers';
import { protectRequest, refusal } from './protection';

const BACKEND_NAME = 'voting-backend-v1';
const RECOVERY_NAME = 'verification-recovery-v1';
const RECOVERY_INTERVAL = 60_000;
const REQUEST_LEASE_MS = 10 * 60_000;

function backendOrigin(env: Env): URL {
  const url = new URL(env.PUBLIC_BACKEND_ORIGIN);
  if (url.protocol !== 'https:' || url.username || url.password || url.pathname !== '/' ||
      url.search || url.hash || url.hostname.includes('replace-before-deploy')) {
    throw new Error('Configure the exact HTTPS backend origin before deployment.');
  }
  return url;
}

export class VotingBackend extends Container<Env> {
  defaultPort = 10000;
  sleepAfter = '10m';
  envVars = {
    DJANGO_SETTINGS_MODULE: 'settings_cloudflare',
    DATABASE_URL: this.env.DATABASE_URL,
    SECRET_KEY: this.env.SECRET_KEY,
    EMAIL_OPTOUT_SECRET: this.env.EMAIL_OPTOUT_SECRET,
    ALU_BRIDGE_SECRET: this.env.ALU_BRIDGE_SECRET,
    ALU_BRIDGE_APP_ORIGIN: this.env.ALU_BRIDGE_APP_ORIGIN,
    ALU_BRIDGE_CLIENT_ID: this.env.ALU_BRIDGE_CLIENT_ID,
    ALU_BRIDGE_ELECTIONS: this.env.ALU_BRIDGE_ELECTIONS,
    RECOVERY_SECRET: this.env.RECOVERY_SECRET,
    URL_HOST: backendOrigin(this.env).origin,
    ALU_VOTE_VERIFICATION_BACKEND: 'database',
    WEB_CONCURRENCY: '2',
    VOTE_VERIFIER_CONCURRENCY: '2',
  };
}

// This alarm has its own Durable Object so it cannot interfere with the
// Container SDK's inactivity alarm. It stores scheduling metadata only.
export class VerificationRecovery extends DurableObject<Env> {
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS inflight (id TEXT PRIMARY KEY, expires_at INTEGER NOT NULL)');
    ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS lifecycle_revision (id INTEGER PRIMARY KEY, value INTEGER NOT NULL)');
    ctx.storage.sql.exec('INSERT OR IGNORE INTO lifecycle_revision VALUES (1, 0)');
  }

  private revision(): number {
    return this.ctx.storage.sql.exec<{value:number}>('SELECT value FROM lifecycle_revision WHERE id = 1').one().value;
  }

  async arm(): Promise<string> {
    this.ctx.storage.sql.exec('UPDATE lifecycle_revision SET value = value + 1 WHERE id = 1');
    const id = crypto.randomUUID();
    this.ctx.storage.sql.exec('DELETE FROM inflight WHERE expires_at <= ?', Date.now());
    this.ctx.storage.sql.exec('INSERT INTO inflight VALUES (?, ?)', id, Date.now() + REQUEST_LEASE_MS);
    await this.ensureAlarm();
    return id;
  }

  async finish(id: string): Promise<void> {
    this.ctx.storage.sql.exec('UPDATE lifecycle_revision SET value = value + 1 WHERE id = 1');
    this.ctx.storage.sql.exec('DELETE FROM inflight WHERE id = ?', id);
    await this.ensureAlarm();
  }

  private async ensureAlarm(): Promise<void> {
    const alarm = await this.ctx.storage.getAlarm();
    if (alarm === null || alarm > Date.now() + RECOVERY_INTERVAL) {
      await this.ctx.storage.setAlarm(Date.now() + RECOVERY_INTERVAL);
    }
  }

  async alarm(): Promise<void> {
    // Persist the next check before network I/O so an interrupted alarm still
    // has a recovery path. Healthy empty queues clear it to avoid idle charges.
    await this.ctx.storage.setAlarm(Date.now() + RECOVERY_INTERVAL);
    const revision = this.revision();
    const origin = backendOrigin(this.env);
    const probeUrl = new URL('/internal/verification-state', origin);
    probeUrl.protocol = 'http:';
    const response = await this.env.BACKEND.getByName(BACKEND_NAME).fetch(
      new Request(probeUrl, {
        headers: {
          Host: origin.host,
          'X-Forwarded-Proto': 'https',
          Connection: 'close',
          Authorization: 'Bearer ' + this.env.RECOVERY_SECRET,
        },
      }));
    if (!response.ok) {
      await response.body?.cancel();
      throw new Error('Verification recovery probe unavailable.');
    }
    const state: {pending?: unknown; needs_attention?: unknown; keep_alive?: unknown; next_wake_at?: unknown} = await response.json();
    if (typeof state.pending !== 'boolean' || typeof state.needs_attention !== 'boolean' || typeof state.keep_alive !== 'boolean' || (state.next_wake_at !== null && (!Number.isSafeInteger(state.next_wake_at) || Number(state.next_wake_at) <= 0))) {
      throw new Error('Invalid verification recovery probe.');
    }
    if (state.needs_attention) console.error('Vote verification requires operator review.');
    // An in-flight confirmation may not have committed its job yet. Keep the
    // alarm while its durable lease exists, even if this probe saw an empty queue.
    const active = this.ctx.storage.sql.exec<{total: number}>(
      'SELECT COUNT(*) AS total FROM inflight WHERE expires_at > ?', Date.now()).one().total;
    if (!state.keep_alive && !state.pending && active === 0 && this.revision() === revision) {
      if (state.next_wake_at !== null) await this.ctx.storage.setAlarm(Math.max(Date.now() + 1000, Number(state.next_wake_at)));
      else await this.ctx.storage.deleteAlarm();
    }
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith('/internal/')) {
      return new Response('Not found', {status: 404, headers: {'Cache-Control': 'no-store'}});
    }
    let recovery: DurableObjectStub<VerificationRecovery> | undefined;
    let lease: string | undefined;
    try {
      const origin = backendOrigin(env);
      if (url.hostname !== origin.hostname && !['127.0.0.1', 'localhost'].includes(url.hostname)) {
        return new Response('Not found', {status: 404});
      }
      const checked = await protectRequest(request, env, origin);
      if (checked instanceof Response) return checked;
      if ((/^\/helios\/elections\/[^/]+\/cast_confirm$/.test(url.pathname) &&
          ['GET', 'POST'].includes(request.method)) ||
          url.pathname === '/helios/alu/manage' && request.method === 'POST') {
        // Arm before forwarding: a crash after accepting the vote cannot leave
        // recovery dependent on this request completing or another student.
        recovery = env.RECOVERY.getByName(RECOVERY_NAME);
        lease = await recovery.arm();
      }
      // Cloudflare secures the Worker-to-container connection itself; its
      // container HTTP server does not terminate TLS. Public requests stay HTTPS.
      const containerUrl = new URL(request.url);
      containerUrl.protocol = 'http:';
      const forwarded = new Request(containerUrl, {
        method: request.method, headers: request.headers, body: checked,
        redirect: 'manual',
      });
      forwarded.headers.set('Host', origin.host);
      forwarded.headers.set('X-Forwarded-Proto', 'https');
      forwarded.headers.delete('X-Forwarded-For');
      forwarded.headers.delete('Forwarded');
      forwarded.headers.set('Connection', 'close');
      const response = await env.BACKEND.getByName(BACKEND_NAME).fetch(forwarded);
      if (response.status >= 500) {
        await response.body?.cancel();
        return refusal('Voting is temporarily unavailable. Please try again shortly.', 503, {'Retry-After': '5'});
      }
      const headers = new Headers(response.headers);
      headers.set('Cache-Control', 'no-store');
      return new Response(response.body, {status: response.status, headers});
    } catch {
      return new Response('Voting is temporarily unavailable. Please try again shortly.', {
        status: 503, headers: {'Cache-Control': 'no-store', 'Retry-After': '5'},
      });
    } finally {
      if (recovery && lease) {
        try {
          await recovery.finish(lease);
        } catch {
          // arm() persisted the recovery alarm and a bounded lease first. A
          // failed cleanup must not turn an accepted vote into a failed response.
          console.error('Verification recovery lease cleanup will retry after expiry.');
        }
      }
    }
  },
} satisfies ExportedHandler<Env>;
