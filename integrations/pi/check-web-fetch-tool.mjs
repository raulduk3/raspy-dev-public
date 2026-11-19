/** Offline checks for web_fetch: address refusal at every hop, redirects, text extraction.
 *  A fake resolver and a fake fetch stand in for the network; nothing leaves this machine. */
import assert from 'node:assert/strict';
import { checkUrl, fetchPage, isPrivateAddress, readable, webFetchExtension } from './web-fetch-tool.mjs';

for (const address of ['127.0.0.1', '10.1.2.3', '172.20.0.1', '192.168.1.5', '169.254.169.254', '100.100.1.1',
                       '0.0.0.0', '::1', 'fd12::1', 'fe80::1', '::ffff:127.0.0.1']) {
  assert.equal(isPrivateAddress(address), true, address);
}
for (const address of ['93.184.216.34', '8.8.8.8', '2606:4700::1111']) assert.equal(isPrivateAddress(address), false, address);

const dns = { 'example.org': ['93.184.216.34'], 'rebind.example': ['127.0.0.1'], 'mixed.example': ['93.184.216.34', '10.0.0.1'] };
const lookup = async (host) => { if (!dns[host]) throw new Error('ENOTFOUND'); return dns[host].map(address => ({ address })); };

for (const [url, reason] of [
  ['file:///etc/passwd', /Only http and https/], ['http://localhost:7433/api', /Local addresses/],
  ['http://127.0.0.1:7433/healthz', /private network/], ['http://[::1]/', /private network/],
  ['http://rebind.example/', /private network/], ['http://mixed.example/', /private network/],
  ['https://user:secret@example.org/', /credentials/], ['not a url', /valid URL/],
]) await assert.rejects(() => checkUrl(url, lookup), reason, url);
assert.equal((await checkUrl('https://example.org/docs', lookup)).href, 'https://example.org/docs');

const page = readable('<html><head><title> Fixture  page </title><style>x{}</style></head><body>' +
  '<script>steal()</script><h1>Heading</h1><p>One &amp; two&nbsp;&#8212; three</p><!-- hidden --><p>Next</p></body></html>');
assert.equal(page.title, 'Fixture page');
assert.equal(page.text, 'Fixture page Heading\nOne & two — three\nNext');

const reply = (status, headers, body = '') => new Response(body, { status, headers });
const site = {
  'https://example.org/start': () => reply(302, { location: '/final' }),
  'https://example.org/final': () => reply(200, { 'content-type': 'text/html; charset=utf-8' }, '<title>Final</title><p>' + 'word '.repeat(5000) + '</p>'),
  'https://example.org/escape': () => reply(301, { location: 'http://rebind.example/admin' }),
  'https://example.org/binary': () => reply(200, { 'content-type': 'application/octet-stream' }, 'x'),
  'https://example.org/missing': () => reply(404, { 'content-type': 'text/html' }, 'no'),
  'https://example.org/loop': () => reply(302, { location: '/loop' }),
};
const fetchImpl = async (url) => site[String(url)]();
const final = await fetchPage('https://example.org/start', { lookup, fetchImpl, maxChars: 1000 });
assert.equal(final.url, 'https://example.org/final');
assert.equal(final.title, 'Final');
assert.equal(final.text.length, 1000);
assert.equal(final.truncated, true);
await assert.rejects(() => fetchPage('https://example.org/escape', { lookup, fetchImpl }), /private network/);
await assert.rejects(() => fetchPage('https://example.org/binary', { lookup, fetchImpl }), /Not a text page/);
await assert.rejects(() => fetchPage('https://example.org/missing', { lookup, fetchImpl }), /HTTP 404/);
await assert.rejects(() => fetchPage('https://example.org/loop', { lookup, fetchImpl }), /Too many redirects/);

let registered;
webFetchExtension()({ registerTool: (tool) => { registered = tool; } });
assert.equal(registered.name, 'web_fetch');
assert.deepEqual(registered.parameters.required, ['url']);

console.log(JSON.stringify({ passed: true, checks: ['private and local addresses at every hop', 'redirects',
  'text extraction', 'refused content types and statuses', 'tool registration'],
  scope: 'Offline: a fake resolver and fake fetch; no live page is read.' }, null, 2));
