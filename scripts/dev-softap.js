#!/usr/bin/env node
/**
 * Start SoftAP (setup mode) for Raspberry Pi/Linux dev.
 * Keeps process alive and restores NetworkManager (normal mode) on exit (Ctrl+C / SIGTERM).
 * Non-fatal: logs a warning and exits 0 on failure to start.
 */
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

if (process.platform !== 'linux') {
  process.exit(0);
}

const root = path.resolve(__dirname, '..');
const installedSetup = '/usr/local/bin/neuroion-switch-to-setup-mode.sh';
const installedNormal = '/usr/local/bin/neuroion-switch-to-normal-mode.sh';
const localSetup = path.join(root, 'infra', 'scripts', 'switch-to-setup-mode.sh');
const localNormal = path.join(root, 'infra', 'scripts', 'switch-to-normal-mode.sh');

const setupScript = fs.existsSync(installedSetup) ? installedSetup : fs.existsSync(localSetup) ? localSetup : null;
const normalScript = fs.existsSync(installedNormal) ? installedNormal : fs.existsSync(localNormal) ? localNormal : null;

if (!setupScript) {
  console.warn('[softap] No setup-mode script found, skipping SoftAP.');
  process.exit(0);
}

const sudoCheck = spawnSync('sudo', ['-n', 'true'], { stdio: 'ignore' });
if (sudoCheck.status !== 0) {
  console.warn('[softap] Sudo requires a password; hotspot not started.');
  console.warn('[softap] To enable: run once from repo root: sudo ./infra/scripts/allow-softap-sudo.sh');
  process.exit(0);
}

let restored = false;
function restoreNetwork() {
  if (restored) return;
  restored = true;
  console.log('[softap] Restoring NetworkManager (WiFi)...');
  if (normalScript) {
    spawnSync('sudo', [normalScript], { stdio: 'inherit' });
  }
  spawnSync('sudo', ['systemctl', 'start', 'NetworkManager'], { stdio: 'inherit' });
}

function onExit() {
  restoreNetwork();
  process.exit(0);
}

process.on('SIGINT', onExit);
process.on('SIGTERM', onExit);

console.log('[softap] Starting setup mode (SoftAP)...');
const result = spawnSync('sudo', [setupScript], {
  encoding: 'utf8',
  maxBuffer: 1024 * 1024,
});
if (result.status !== 0) {
  console.warn('[softap] Failed to start SoftAP (exit code %s), continuing without it.', result.status);
  if (result.stderr && result.stderr.trim()) {
    console.warn('[softap] stderr: %s', result.stderr.trim());
  }
  if (result.stdout && result.stdout.trim()) {
    process.stdout.write(result.stdout);
  }
  process.exit(0);
}
if (result.stdout && result.stdout.trim()) {
  process.stdout.write(result.stdout);
}

// Keep process alive so we can run cleanup on Ctrl+C
process.stdin?.resume();
setInterval(() => {}, 1e9);
