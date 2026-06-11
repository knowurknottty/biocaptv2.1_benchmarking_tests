#!/usr/bin/env node
// Deterministic WASM kernel benchmark: bioCAPT v2.1 sealed artifacts vs bioCAPT v2.2 sealed artifacts.
// Usage: node scripts/benchmark_v21_v22_wasm.mjs [steps]
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const resultsDir = resolve(root, 'results');
mkdirSync(resultsDir, { recursive: true });

const steps = Number(process.argv[2] || 250);
const artifacts = {
  v21: {
    label: 'bioCAPT v2.1 sealed',
    capt: '/Users/knowurknot/2clean4u/CAPTLang_WASM/versions/2.1/wasm/capt_core.sealed.opt.wasm',
    biocapt: '/Users/knowurknot/2clean4u/CAPTLang_WASM/versions/2.1/wasm/biocapt_core.sealed.opt.wasm'
  },
  v22: {
    label: 'bioCAPT v2.2 CAPTLang upgrade',
    capt: '/Users/knowurknot/biocaptv2.2-upgrade-kit/source/biocaptv2.1/build/wasm/capt_core.sealed.wasm',
    biocapt: '/Users/knowurknot/biocaptv2.2-upgrade-kit/source/biocaptv2.1/build/wasm/biocapt_core.sealed.wasm'
  }
};

function fp(text) {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 100000) / 100000;
}

function readState(exportsObj) {
  const call = (name) => (typeof exportsObj[name] === 'function' ? Number(exportsObj[name]()) : null);
  const out = {
    call_count: call('get_call_count'),
    metrics: call('get_metrics'),
    active_modules: call('get_active_modules')
  };
  if (exportsObj.get_bio_load) out.bio_load = call('get_bio_load');
  if (exportsObj.get_recovery_balance) out.recovery_balance = call('get_recovery_balance');
  return out;
}

async function runProduct(product) {
  const rows = [];
  const summary = {};
  const entries = product === 'biocapt' ? ['process', 'process_embedding'] : ['process'];
  for (const [version, files] of Object.entries(artifacts)) {
    const wasmPath = files[product];
    const bytes = readFileSync(wasmPath);
    const module = await WebAssembly.instantiate(bytes, {});
    const exportsObj = module.instance.exports;
    exportsObj.reset_all();

    const versionRows = [];
    for (let i = 0; i < steps; i += 1) {
      const inputs = entries.map((entry, idx) => Math.sin(i * 0.37 + idx) + fp(`${product}:${version}:${i}:${idx}`));
      const outputs = inputs.map((input, idx) => Number(exportsObj[entries[idx]](input)));
      const state = readState(exportsObj);
      versionRows.push({
        version,
        product,
        step: i + 1,
        entries,
        inputs,
        outputs,
        ...state
      });
    }

    const numericAverage = (key) => versionRows.reduce((acc, row) => acc + row[key], 0) / steps;
    summary[version] = {
      label: files.label,
      wasm_path: wasmPath,
      wasm_bytes: bytes.length,
      steps,
      final_state: readState(exportsObj),
      average_metrics: numericAverage('metrics'),
      average_active_modules: numericAverage('active_modules')
    };
    rows.push(...versionRows);
  }

  const delta = {};
  for (const key of ['metrics', 'active_modules']) {
    delta[key] = summary.v22[`average_${key}`] - summary.v21[`average_${key}`];
  }
  for (const key of ['bio_load', 'recovery_balance']) {
    if (summary.v22.final_state[key] !== null && summary.v21.final_state[key] !== null) {
      delta[key] = summary.v22.final_state[key] - summary.v21.final_state[key];
    }
  }
  delta.call_count = summary.v22.final_state.call_count - summary.v21.final_state.call_count;

  return { product, entries, summary, delta, rows };
}

(async () => {
  const results = [];
  for (const product of ['capt', 'biocapt']) results.push(await runProduct(product));
  const report = {
    generated_at: new Date().toISOString(),
    benchmark: 'deterministic sealed wasm kernel replay',
    steps_per_version_per_product: steps,
    products: results
  };
  const jsonPath = resolve(resultsDir, 'v21_v22_wasm_direct_benchmark.json');
  writeFileSync(jsonPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(jsonPath);
  for (const product of results) {
    console.log(product.product);
    console.log(JSON.stringify(product.summary, null, 2));
    console.log(JSON.stringify(product.delta, null, 2));
  }
})();
