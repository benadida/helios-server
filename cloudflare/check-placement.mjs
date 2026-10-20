// Read-only post-deploy verification. Never print raw application configuration:
// it can contain secret environment variables. Only locations and constraints
// are suitable for CI output.
import { execFileSync } from 'node:child_process';

function wrangler(...args) {
  try {
    return JSON.parse(execFileSync(process.execPath,
      ['node_modules/wrangler/bin/wrangler.js', 'containers', ...args, '--json'],
      { encoding: 'utf8', timeout: 60_000, stdio: ['ignore', 'pipe', 'pipe'] }));
  } catch {
    throw new Error('Could not read container placement; raw provider output withheld.');
  }
}
const applications = wrangler('list');
const application = applications.find(a => a.name === 'alu-voting-backend-votingbackend');
if (!application) throw new Error('Voting backend application was not found.');
const info = wrangler('info', application.id);
const constraints = info.constraints?.regions ?? [];
if (constraints.length !== 1 || constraints[0] !== 'ENAM') {
  throw new Error('Voting backend must be constrained to Eastern North America.');
}
// A GET for a nonexistent election wakes the selected container without
// registering a voter, consuming a login grant or accepting a ballot.
const probe = await fetch('https://alu-voting-backend.e-nnamah.workers.dev/helios/elections/00000000-0000-4000-8000-000000000000/ui/ballot', {
  redirect: 'error', signal: AbortSignal.timeout(60_000),
});
await probe.body?.cancel();
if (probe.status !== 404) throw new Error('Backend read-only startup probe failed.');
const instances = wrangler('instances', application.id);
const rows = Array.isArray(instances) ? instances : instances.instances;
if (!Array.isArray(rows)) throw new Error('Unknown instance placement response.');
const active = rows.filter(i => i.location && i.state !== 'inactive');
console.log(JSON.stringify({ constraints, instances: rows.map(i => ({
  state: typeof i.state === 'string' ? i.state : i.state?.status,
  location: i.location?.name, region: i.location?.region,
})) }, null, 2));
if (active.some(i => i.location?.region && i.location.region !== 'ENAM')) {
  throw new Error('A running container is outside the configured database region area.');
}
if (!active.length) throw new Error('No active container location was reported.');
let diagnostic;
try {
  const output = execFileSync(process.execPath,
    ['node_modules/wrangler/bin/wrangler.js', 'containers', 'ssh', active[0].id,
      '--', 'python', '/app/manage.py', 'voting_placement'],
    { encoding: 'utf8', timeout: 45_000, stdio: ['ignore', 'pipe', 'pipe'] });
  diagnostic = output.split('\n').map(line=>{
    try { return JSON.parse(line); } catch { return null; }
  }).find(row=>row?.database_region);
} catch {
  throw new Error('Read-only database placement diagnostic unavailable; provider output withheld.');
}
if (!diagnostic || diagnostic.database_region !== 'us-east-2' || diagnostic.transaction_pooler !== false) {
  throw new Error('Expected the direct Ohio database connection for verification wake notifications.');
}
console.log(JSON.stringify(diagnostic));
