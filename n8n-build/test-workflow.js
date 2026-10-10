const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const w = JSON.parse(fs.readFileSync(path.join(__dirname, 'ai-review-request-n8n.json'), 'utf8'));
assert.equal(w.active, false);
const names = new Set(w.nodes.map(n => n.name));
assert.equal(names.size, w.nodes.length);
for (const [source, ports] of Object.entries(w.connections)) {
  assert(names.has(source));
  for (const outputs of Object.values(ports)) for (const output of outputs) for (const edge of output) assert(names.has(edge.node), edge.node);
}
for (const n of w.nodes.filter(n => n.type === 'n8n-nodes-base.code')) new Function(n.parameters.jsCode);
assert(w.nodes.some(n => n.name === '90-Day Dedup (Supabase)'));
assert(w.nodes.some(n => n.name === 'Classify Job Notes - Ministral 3B'));
assert(w.nodes.some(n => n.name === 'Wait 48 Hours'));
assert(w.nodes.some(n => n.name === 'SMS Owner Negative Alert'));
console.log('Review-request n8n workflow: structure, inactive default, code syntax, deduplication, Mistral, routing, and follow-up passed');
