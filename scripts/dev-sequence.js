#!/usr/bin/env node
/**
 * Sequential dev launcher for Pi: start services one by one and emit progress.
 * Progress is written to a JSON file for the touchscreen boot loader.
 */
const { spawn } = require('child_process')
const fs = require('fs')
const path = require('path')
const net = require('net')
const http = require('http')
const os = require('os')

const root = path.resolve(__dirname, '..')
const statusPath = process.env.NEUROION_DEV_STATUS_PATH || '/tmp/neuroion-dev-status.json'
const totalGb = os.totalmem() / (1024 ** 3)
const isArm = process.arch.startsWith('arm')
const lightMode = process.env.NEUROION_DEV_LIGHT === '1' || (process.platform === 'linux' && isArm && totalGb <= 3.5)

const children = []

function writeStatus(progress, stage) {
  const payload = {
    progress: Math.max(0, Math.min(100, Math.round(progress))),
    stage,
    updated_at: new Date().toISOString(),
  }
  try {
    fs.writeFileSync(statusPath, JSON.stringify(payload))
  } catch (err) {
    console.warn('[dev-sequence] Could not write status:', err.message)
  }
}

function spawnCommand(command, args, extraEnv = {}) {
  const child = spawn(command, args, {
    cwd: root,
    shell: true,
    stdio: 'inherit',
    env: { ...process.env, ...extraEnv, NEUROION_DEV_STATUS_PATH: statusPath },
  })
  children.push(child)
  return child
}

function waitForPort(port, host = '127.0.0.1', timeoutMs = 60000) {
  const started = Date.now()
  return new Promise((resolve, reject) => {
    const attempt = () => {
      const socket = net.createConnection({ port, host })
      socket.on('connect', () => {
        socket.end()
        resolve(true)
      })
      socket.on('error', () => {
        socket.destroy()
        if (Date.now() - started > timeoutMs) {
          reject(new Error(`Timeout waiting for ${host}:${port}`))
          return
        }
        setTimeout(attempt, 500)
      })
    }
    attempt()
  })
}

function waitForHttp(url, timeoutMs = 60000) {
  const started = Date.now()
  return new Promise((resolve, reject) => {
    const attempt = () => {
      const req = http.get(url, (res) => {
        res.resume()
        resolve(true)
      })
      req.on('error', () => {
        if (Date.now() - started > timeoutMs) {
          reject(new Error(`Timeout waiting for ${url}`))
          return
        }
        setTimeout(attempt, 700)
      })
      req.setTimeout(5000, () => {
        req.destroy()
      })
    }
    attempt()
  })
}

function cleanupAndExit(code = 0) {
  children.forEach((child) => {
    try {
      child.kill('SIGTERM')
    } catch (_) {}
  })
  process.exit(code)
}

process.on('SIGINT', () => cleanupAndExit(0))
process.on('SIGTERM', () => cleanupAndExit(0))

async function run() {
  writeStatus(5, 'starting')

  console.log('[dev-sequence] Starting API...')
  const apiPort = process.env.API_PORT || '8000'
  spawnCommand('npm', ['run', 'dev:api'], { API_PORT: apiPort })
  try {
    await waitForHttp(`http://127.0.0.1:${apiPort}/setup/status`)
    writeStatus(30, 'api-ready')
  } catch (err) {
    console.warn('[dev-sequence] API did not respond:', err.message)
  }

  console.log('[dev-sequence] Starting setup-ui...')
  spawnCommand('npm', ['run', 'dev', '--prefix', 'apps/setup-ui'], {
    NODE_OPTIONS: process.env.NODE_OPTIONS || '--max_old_space_size=512',
  })
  try {
    await waitForPort(3000)
    writeStatus(55, 'setup-ui-ready')
  } catch (err) {
    console.warn('[dev-sequence] setup-ui not ready:', err.message)
  }

  console.log('[dev-sequence] Starting touchscreen-ui...')
  spawnCommand('npm', ['run', 'dev', '--prefix', 'apps/touchscreen-ui'], {
    NODE_OPTIONS: process.env.NODE_OPTIONS || '--max_old_space_size=512',
  })
  try {
    await waitForPort(3001)
    writeStatus(80, 'touchscreen-ui-ready')
  } catch (err) {
    console.warn('[dev-sequence] touchscreen-ui not ready:', err.message)
  }

  if (lightMode) {
    console.log('[dev-sequence] Low-memory mode: skipping SoftAP and kiosk.')
    writeStatus(90, 'softap-skipped')
    writeStatus(95, 'kiosk-skipped')
  } else {
    console.log('[dev-sequence] Starting SoftAP...')
    spawnCommand('npm', ['run', 'dev:softap'])
    writeStatus(90, 'softap-started')

    console.log('[dev-sequence] Starting kiosk...')
    spawnCommand('npm', ['run', 'dev:kiosk'])
    writeStatus(95, 'kiosk-started')
  }

  writeStatus(100, 'ready')
}

run().catch((err) => {
  console.error('[dev-sequence] Failed:', err.message)
  writeStatus(100, 'ready')
})
