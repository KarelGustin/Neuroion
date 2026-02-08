#!/usr/bin/env node
/**
 * Start SoftAP (setup mode) for Raspberry Pi/Linux dev.
 * Non-fatal: logs a warning and exits 0 on failure.
 */
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

if (process.platform !== 'linux') {
  process.exit(0);
}

const root = path.resolve(__dirname, '..');
const installedScript = '/usr/local/bin/neuroion-switch-to-setup-mode.sh';
const localScript = path.join(root, 'infra', 'scripts', 'switch-to-setup-mode.sh');

const scriptToRun = fs.existsSync(installedScript)
  ? installedScript
  : fs.existsSync(localScript)
    ? localScript
    : null;

if (!scriptToRun) {
  console.warn('[softap] No setup-mode script found, skipping SoftAP.');
  process.exit(0);
}

const sudoCheck = spawnSync('sudo', ['-n', 'true'], { stdio: 'ignore' });
if (sudoCheck.status !== 0) {
  console.warn('[softap] sudo requires a password; skipping SoftAP.');
  process.exit(0);
}

console.log('[softap] Starting setup mode (SoftAP)...');
const result = spawnSync('sudo', [scriptToRun], { stdio: 'inherit' });
if (result.status !== 0) {
  console.warn('[softap] Failed to start SoftAP, continuing without it.');
}
