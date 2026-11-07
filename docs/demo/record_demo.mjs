// Records the demo walkthrough with captions (no audio) from a running app.
//   Needs: backend on :8000 and the frontend on :5173 (see README "Running the demo"), plus `npm i playwright`.
//   Run:   node docs/demo/record_demo.mjs                 (live memory; set FIXTURE=1 for a labeled simulated-memory fallback)
//   Output: .local/demo/incento-demo[-fallback-fixture].webm (git-ignored). Add a voiceover from docs/demo/script.md.
// Set CHROMIUM_PATH to a Chromium/Chrome binary if Playwright's own browser is not installed.
import { chromium } from 'playwright';
import fs from 'fs';
import nodePath from 'path';
import { fileURLToPath } from 'url';

const OUT = nodePath.resolve(nodePath.dirname(fileURLToPath(import.meta.url)), '../../.local/demo');
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const ctx = await browser.newContext({ viewport: { width: 1440, height: 810 }, recordVideo: { dir: OUT, size: { width: 1440, height: 810 } } });
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', e => errors.push('pageerror: ' + e.message));
page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
page.on('response', r => { if (r.url().includes('/api/') && r.status() >= 400) errors.push('http ' + r.status() + ' ' + r.url()); });

async function cap(text, ms) {
  await page.evaluate((t) => {
    let d = document.getElementById('demo-cap');
    if (!d) {
      d = document.createElement('div');
      d.id = 'demo-cap';
      d.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:99999;background:rgba(17,24,39,.92);color:#fff;font:600 22px/1.35 system-ui,sans-serif;padding:16px 32px;text-align:center';
      document.body.appendChild(d);
    }
    d.textContent = t;
  }, PFX + text);
  await page.waitForTimeout(ms);
}
async function scrollTo(locator) { await locator.first().scrollIntoViewIfNeeded(); await page.waitForTimeout(400); }

const FIX = process.env.FIXTURE === '1';
const PFX = FIX ? 'FALLBACK RECORDING, simulated memory (fixture), not live Hindsight. ' : '';
const t0 = Date.now();
const stamp = (l) => console.log(((Date.now() - t0) / 1000).toFixed(0).padStart(4) + 's  ' + l);

await page.goto('http://localhost:5173/');
await cap('IncentO: does a sales commission produce poor-fit deals? Synthetic data only.', 5000);
stamp('hook');
await cap('The problem: month-end acquisition bonuses can push heavy discounts, and organizations forget what they already tried.', 6500);
await cap('IncentO links the policy to deals, tickets and cancellations, and remembers past decisions and results with Hindsight.', 6500);

await cap('Step 1: investigate the acquisition bonus policy with Hindsight memory live.', 3000);
await page.getByRole('button', { name: 'Load and investigate' }).click();
await page.getByRole('status').filter({ hasText: /Loaded run/ }).waitFor({ timeout: 120000 });
stamp('investigated');
await page.waitForTimeout(800);
await cap('Calculated by code, not by a model: 120 month-end deals vs 880 others, three flagged gaps of 15 points.', 7000);
await page.getByRole('button', { name: 'Investigation' }).click();
await page.waitForTimeout(1200);
await cap('Every claim cites a source record. Customer text is labeled untrusted and shown as plain text.', 6500);
const ev = page.getByRole('heading', { name: 'Evidence trail' });
await scrollTo(ev);
await cap('The wording avoids causation: the data shows association, not proof.', 5000);
const expl = page.getByRole('heading', { name: 'Proposed action' });
await scrollTo(expl);
await cap('With seeded history, the advice is a guardrail pilot, citing the remembered result HIST-RISK-RESULT.', 7500);
stamp('findings');

await page.evaluate(() => window.scrollTo(0, 0));
await page.getByRole('button', { name: 'Compare memory' }).click();
await cap('Step 2: run the same evidence with memory off to see what memory changes.', 3500);
await page.getByRole('button', { name: /Run with memory off/ }).click();
await page.getByText('WITHOUT MEMORY').waitFor({ timeout: 120000 });
await page.waitForTimeout(1500);
await cap('Same calculated numbers in both runs. Without memory: revert the policy. With memory: pilot a guardrail.', 8000);
await page.mouse.wheel(0, 500);
await cap('The rejected hypothesis is recalled but never cited. Explanation source: labeled template, memory status: live.', 7500);
stamp('compare');

await page.evaluate(() => window.scrollTo(0, 0));
await page.getByRole('button', { name: 'Incident timeline' }).click();
await page.waitForTimeout(1200);
await cap('Step 3: record what management decided. It is saved and retained in Hindsight.', 4500);
const note = 'Approved a one-quarter discount approval pilot for month-end deals.';
await page.locator('select').last().selectOption('decision').catch(() => {});
await page.getByLabel('Note').fill(note);
await page.waitForTimeout(800);
await page.getByRole('button', { name: 'Save outcome' }).click();
await page.getByText(/Retention: retained/).first().waitFor({ timeout: 90000 });
const decisionDate = new Date().toISOString().slice(0, 10);
const nextAsOf = new Date(Date.parse(`${decisionDate}T00:00:00Z`) + 86400000).toISOString().slice(0, 10);
stamp('outcome retained');
await cap('Saved as a management decision, with retention status: retained. A retry button appears if retention ever fails.', 6500);
await cap(FIX ? 'The simulated store answers immediately.' : 'Cloud indexing takes a few seconds, so the next investigation waits before recalling it.', 5500);
await cap('Now investigate again at a later date. History is recalled from Hindsight, not from this page.', 3000);
await page.getByRole('button', { name: 'Overview' }).click();
await page.waitForTimeout(800);
await page.getByLabel('As of').fill(nextAsOf);
await page.getByLabel('Memory').selectOption('live');
await page.waitForTimeout(500);
await page.getByRole('button', { name: 'Load and investigate' }).click();
await page.getByRole('status').filter({ hasText: /Loaded run/ }).waitFor({ timeout: 120000 });
await page.getByRole('button', { name: 'Investigation' }).click();
await page.waitForTimeout(1200);
stamp('later run');
await page.getByRole('button', { name: 'Compare memory' }).click();
await page.waitForTimeout(1500);
const rec = page.getByText(new RegExp(`decision · ${decisionDate}`)).first();
await rec.waitFor({ timeout: 15000 }).catch(() => {});
const found = await rec.isVisible().catch(() => false);
stamp('decision recalled in UI: ' + found);
if (found) await scrollTo(rec);
await cap(found ? 'The decision we just saved (dated today) now appears in recalled history. The loop is closed.' : 'MISSING', 9000);
await cap('IncentO: calculated evidence, remembered outcomes, no causal claims. Powered by Hindsight.', 6000);
stamp('end');

const video = page.video();
await ctx.close();
const path = await video.path();
fs.renameSync(path, OUT + (FIX ? '/incento-demo-fallback-fixture.webm' : '/incento-demo.webm'));
await browser.close();
console.log('errors:', errors);
console.log('saved');
