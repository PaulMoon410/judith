/* End-to-end test against a temporary local database, using the existing Puppeteer dependency. */
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const puppeteer = require('puppeteer');

async function main() {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'judith-browser-'));
  const password = crypto.randomBytes(24).toString('hex');
  const python = process.env.JUDITH_TEST_PYTHON || path.join(__dirname, '..', '.venv', 'bin', 'python');
  const server = spawn(python, ['-u', '-c', `
from estimator.workspace_web import create_app
from werkzeug.serving import make_server
server = make_server("127.0.0.1", 0, create_app())
print("READY:" + str(server.server_port), flush=True)
server.serve_forever()
`], {cwd: path.join(__dirname, '..'), env: {...process.env,
    JUDITH_WORKSPACE_PASSWORD: password, JUDITH_JOBS_DB: path.join(directory, 'test.sqlite3'),
    JUDITH_SECURE_COOKIE: '0'}});
  let browser;
  const errors = [];
  let serverOutput = '';
  server.stderr.on('data', chunk => { serverOutput += chunk.toString(); });
  try {
    const port = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Test server did not start. ' + serverOutput)), 15000);
      server.once('error', error => { clearTimeout(timer); reject(error); });
      server.once('exit', code => { clearTimeout(timer); reject(new Error(`Test server exited (${code}). ${serverOutput}`)); });
      server.stdout.on('data', chunk => {
        const match = chunk.toString().match(/READY:(\d+)/);
        if (match) { clearTimeout(timer); resolve(Number(match[1])); }
      });
    });
    const origin = `http://127.0.0.1:${port}`;
    assert.equal((await fetch(origin + '/workspace')).status, 200);
    browser = await puppeteer.launch({headless: true});
    const page = await browser.newPage();
    page.on('pageerror', error => errors.push(error.message));
    page.on('dialog', dialog => dialog.accept(dialog.type() === 'prompt' ? 'Saved outlet assembly' : undefined));
    await page.emulateTimezone('America/New_York');
    await page.setViewport({width: 1280, height: 900});
    await page.goto(origin + '/workspace', {waitUntil: 'networkidle0'});
    await page.type('#password', password);
    await page.click('#login-form button');
    await page.waitForSelector('#workspace:not([hidden])');
    await page.click('#templates button');
    await page.waitForSelector('#editor:not([hidden])');

    await page.evaluate(() => {
      const form = document.getElementById('estimate-form');
      const values = {
        title: 'Browser-tested outlet job', customer: 'Browser Customer', address: '10 Test Street',
        scope: 'Replace ten outlets.', notes: 'PRIVATE CREW NOTE', labor_rate: '10',
        permits: '2', equipment: '3', other_costs: '4', consumables_percent: '10',
        overhead_percent: '10', contingency_percent: '5', pricing_percent: '25',
        tax_percent: '6', tax_mode: 'all', labor_confirmed: true,
        tax_confirmed: true, scope_confirmed: true
      };
      for (const [name, value] of Object.entries(values)) {
        const input = form.elements.namedItem(name);
        if (input.type === 'checkbox') input.checked = value;
        else input.value = value;
        input.dispatchEvent(new Event('input', {bubbles: true}));
      }
      const cards = Array.from(document.querySelectorAll('#items .item'));
      cards.slice(1).forEach(card => card.remove());
      const item = {description: 'Outlet', quantity: '10', unit: 'ea', unit_cost: '.105',
        hours_per_unit: '.5', waste_percent: '10', supplier: 'Quote 123', specification: 'Exact SKU'};
      for (const [name, value] of Object.entries(item)) {
        const input = cards[0].querySelector(`[data-field="${name}"]`);
        input.value = value;
        input.dispatchEvent(new Event('input', {bubbles: true}));
      }
      const verified = cards[0].querySelector('[data-field="verified_on"]');
      const now = new Date();
      verified.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
      verified.dispatchEvent(new Event('input', {bubbles: true}));
    });
    await page.click('#preview');
    await page.waitForFunction(() => document.getElementById('totals-label').textContent.startsWith('Preview'));
    assert.match(await page.$eval('#totals', element => element.textContent), /\$91\.85/);
    assert.equal(await page.$eval('#quote', element => element.disabled), true);
    await page.click('#save-estimate');
    await page.waitForFunction(() => document.getElementById('message').textContent === 'Draft saved.');
    await page.click('#quote');
    await page.waitForFunction(() => document.getElementById('job-status').textContent.startsWith('quoted'));
    assert.equal(await page.$eval('#estimate-fields', element => element.disabled), true);
    await page.evaluate(() => { window.print = () => { window.printRequested = true; }; });
    await page.click('#print');
    await page.waitForFunction(() => window.printRequested === true);
    const printText = await page.$eval('#print-sheet', element => element.textContent);
    assert.match(printText, /Total: \$91\.85/);
    assert.doesNotMatch(printText, /PRIVATE CREW NOTE|Profit allowance|Burdened labor/);
    await page.click('#accept');
    await page.waitForFunction(() => document.getElementById('job-status').textContent.startsWith('accepted'));
    await page.evaluate(() => {
      const form = document.getElementById('schedule-form');
      const values = {start: '2030-01-07T22:00', crew: 'Paul, Alex', ready_on: '2030-01-08',
        travel_hours: '.5', buffer_hours: '.25'};
      for (const [name, value] of Object.entries(values)) form.elements.namedItem(name).value = value;
      form.dispatchEvent(new Event('input', {bubbles: true}));
    });
    await page.click('#schedule-form button');
    await page.waitForFunction(() => document.getElementById('message').textContent.includes('before materials'));
    // At 22:00 New York, the UTC date is already the following day. It must still be rejected.
    await page.evaluate(() => { document.getElementById('schedule-form').elements.namedItem('ready_on').value = '2030-01-07'; });
    await page.click('#schedule-form button');
    await page.waitForFunction(() => document.getElementById('job-status').textContent.startsWith('scheduled'));
    assert.match(await page.$eval('#scheduled-summary', element => element.textContent), /195 minutes/);
    await page.evaluate(() => {
      const form = document.getElementById('actual-form');
      const values = {labor_hours: '6', labor_cost: '60', materials: '2', permits: '2', equipment: '3', other_costs: '4'};
      for (const [name, value] of Object.entries(values)) form.elements.namedItem(name).value = value;
    });
    await page.click('#actual-form button');
    await page.waitForFunction(() => document.getElementById('comparison').textContent.includes('$10.72'));
    await page.click('#complete');
    await page.waitForFunction(() => document.getElementById('job-status').textContent.startsWith('completed'));
    await page.click('#invoice');
    assert.match(await page.$eval('#print-sheet h1', element => element.textContent), /Invoice/);
    await page.click('#save-template');
    await page.waitForFunction(() => document.getElementById('message').textContent.startsWith('Template saved'));
    await page.click('#back');
    await page.waitForSelector('#dashboard:not([hidden])');
    await page.reload({waitUntil: 'networkidle0'});
    await page.waitForSelector('#dashboard:not([hidden])');
    assert.match(await page.$eval('#job-list', element => element.textContent), /completed/);
    assert.match(await page.$eval('#templates', element => element.textContent), /Saved outlet assembly/);
    const exported = await page.evaluate(async () => (await fetch('/workspace/api/export')).text());
    assert.match(exported, /Browser-tested outlet job/);
    assert.match(exported, /71\.00,10\.72/);

    await page.setViewport({width: 390, height: 844});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await page.click('#job-list button');
    await page.waitForSelector('#editor:not([hidden])');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await page.click('#revision');
    await page.waitForFunction(() => document.getElementById('job-status').textContent.startsWith('draft'));
    assert.equal(await page.$eval('[name="labor_confirmed"]', element => element.checked), false);
    assert.deepEqual(errors, []);
    console.log('PASS: browser estimate -> quote -> acceptance -> schedule -> actual costs -> invoice; persistence, templates, CSV, timezone readiness, revisions, and mobile layout.');
  } finally {
    if (browser) await browser.close();
    if (server.exitCode === null) {
      const stopped = new Promise(resolve => server.once('exit', resolve));
      server.kill('SIGTERM');
      await stopped;
    }
    for (const filename of fs.readdirSync(directory)) fs.unlinkSync(path.join(directory, filename));
    fs.rmdirSync(directory);
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
