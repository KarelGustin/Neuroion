#!/usr/bin/env node
/**
 * Start Neuroion API for local dev. Prefers venv Python, then python3 (Unix) or python (Windows).
 * Must be run from repo root (npm run dev sets cwd to root when running this via npm run dev:api).
 */
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const root = path.resolve(__dirname, '..');
const isWindows = process.platform === 'win32';
const venvPython = isWindows
  ? path.join(root, 'venv', 'Scripts', 'python.exe')
  : path.join(root, 'venv', 'bin', 'python');

let py = 'python3';
if (fs.existsSync(venvPython)) {
  py = venvPython;
} else if (isWindows) {
  py = 'python';
}

const child = spawn(py, ['-m', 'neuroion.core.main'], {
  stdio: 'inherit',
  cwd: root,
  shell: true,
  env: { ...process.env, PYTHONUNBUFFERED: '1' },
});

child.on('error', (err) => {
  console.error('Failed to start API:', err.message);
  if (err.code === 'ENOENT' && (py === 'python3' || py === 'python')) {
    console.error('Tip: create a venv and install deps: python3 -m venv venv && ./venv/bin/pip install -r neuroion/core/requirements.txt');
  }
  process.exit(1);
});

child.on('exit', (code) => {
  process.exit(code ?? 0);
});
