#!/usr/bin/env node
/**
 * Start kiosk mode for Raspberry Pi/Linux dev.
 * Non-fatal: logs a warning and exits 0 on failure.
 */
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

if (process.platform !== 'linux') {
  process.exit(0);
}

const root = path.resolve(__dirname, '..');
const kioskScript = path.join(root, 'infra', 'kiosk', 'start-kiosk.sh');

if (!fs.existsSync(kioskScript)) {
  console.warn('[kiosk] start-kiosk.sh not found, skipping kiosk start.');
  process.exit(0);
}

console.log('[kiosk] Starting kiosk mode...');
const result = spawnSync('bash', [kioskScript], { stdio: 'inherit' });
if (result.status !== 0) {
  console.warn('[kiosk] Failed to start kiosk, continuing without it.');
}
