const MAX_BODY = 2 * 1024 * 1024;
const encoder = new TextEncoder();

export function refusal(message: string, status: number, extra: Record<string, string> = {}): Response {
  return new Response(message, {status, headers: {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...extra}});
}

export function authenticatedManagement(request: Request, secret: string): boolean {
  if (!secret) return false;
  const received = encoder.encode(request.headers.get('Authorization') || '');
  const expected = encoder.encode('Bearer ' + secret);
  return received.byteLength === expected.byteLength && crypto.subtle.timingSafeEqual(received, expected);
}

export async function protectRequest(request: Request, env: Env, origin: URL): Promise<Response | ArrayBuffer | undefined> {
  if (!['GET', 'HEAD', 'POST'].includes(request.method)) {
    return refusal('Method not allowed', 405, {Allow: 'GET, HEAD, POST'});
  }
  let path: string;
  try {path = decodeURIComponent(new URL(request.url).pathname);} catch {return refusal('Invalid address', 400);}
  if (path.startsWith('/internal/') || /(?:^|\/)\.(?:env|git)(?:[./]|$)/.test(path)) return refusal('Not found', 404);
  const route = path.split('/')[1];
  if (!['', 'about', 'docs', 'faq', 'privacy', 'helios', 'auth', 'booth', 'verifier', 'static', 'optin', 'optout'].includes(route)) {
    return refusal('Not found', 404);
  }
  if (path === '/helios/alu/manage' && !authenticatedManagement(request, env.ALU_BRIDGE_SECRET)) {
    return refusal('Unauthorized', 401);
  }
  if (request.method !== 'POST') return;
  if (/^\/helios\/elections\/[^/]+\/ui\/submit$/.test(path) &&
      request.headers.get('Origin') !== env.ALU_BRIDGE_APP_ORIGIN) {
    return refusal('Please open the voting link and try again.', 403);
  }
  if (/^\/helios\/elections\/[^/]+\/cast_confirm$/.test(path) &&
      request.headers.get('Origin') !== origin.origin) {
    return refusal('Please return to voting and try again.', 403);
  }
  if (/^\/helios\/elections\/[^/]+\/(?:ui\/submit|cast|cast_confirm)$/.test(path)) {
    const session = (request.headers.get('Cookie') || '').match(/(?:^|;\s*)sessionid=([a-z0-9]{32})(?:;|$)/)?.[1];
    if (session) {
      // This is a browser retry limit, not proof of identity. Django independently
      // checks the real student and its shared database limit. Never group a
      // campus behind one IP address or log the session cookie.
      const digest = await crypto.subtle.digest('SHA-256', encoder.encode(session));
      const key = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
      if (!(await env.VOTE_REQUESTS.limit({key})).success) {
        return refusal('Please wait a moment before trying again.', 429, {'Retry-After': '60'});
      }
    }
  }
  const maximum = path === '/helios/alu/manage' ? 65_536 : MAX_BODY;
  const declared = request.headers.get('Content-Length');
  if (declared !== null) {
    if (!/^\d+$/.test(declared)) return refusal('Invalid request length', 400);
    if (Number(declared) > maximum) return refusal('Request too large', 413);
  }
  // Bound chunked requests too, before starting the backend container.
  const reader = request.body?.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  if (reader) {
    try {
      for (;;) {
        const {done, value} = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > maximum) {await reader.cancel(); return refusal('Request too large', 413);}
        chunks.push(value);
      }
    } finally {reader.releaseLock();}
  }
  const body = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {body.set(chunk, offset); offset += chunk.byteLength;}
  return body.buffer;
}
