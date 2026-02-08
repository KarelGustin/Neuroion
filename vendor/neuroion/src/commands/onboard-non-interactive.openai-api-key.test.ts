import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";
import { OPENAI_DEFAULT_MODEL } from "./openai-model-default.js";

describe("onboard (non-interactive): OpenAI API key", () => {
  it("stores OPENAI_API_KEY and configures the OpenAI default model", async () => {
    const prev = {
      home: process.env.HOME,
      stateDir: process.env.NEUROION_STATE_DIR,
      configPath: process.env.NEUROION_CONFIG_PATH,
      skipChannels: process.env.NEUROION_SKIP_CHANNELS,
      skipGmail: process.env.NEUROION_SKIP_GMAIL_WATCHER,
      skipCron: process.env.NEUROION_SKIP_CRON,
      skipCanvas: process.env.NEUROION_SKIP_CANVAS_HOST,
      token: process.env.NEUROION_GATEWAY_TOKEN,
      password: process.env.NEUROION_GATEWAY_PASSWORD,
    };

    process.env.NEUROION_SKIP_CHANNELS = "1";
    process.env.NEUROION_SKIP_GMAIL_WATCHER = "1";
    process.env.NEUROION_SKIP_CRON = "1";
    process.env.NEUROION_SKIP_CANVAS_HOST = "1";
    delete process.env.NEUROION_GATEWAY_TOKEN;
    delete process.env.NEUROION_GATEWAY_PASSWORD;

    const tempHome = await fs.mkdtemp(path.join(os.tmpdir(), "neuroion-onboard-openai-"));
    process.env.HOME = tempHome;
    process.env.NEUROION_STATE_DIR = tempHome;
    process.env.NEUROION_CONFIG_PATH = path.join(tempHome, "neuroion.json");
    vi.resetModules();

    const runtime = {
      log: () => {},
      error: (msg: string) => {
        throw new Error(msg);
      },
      exit: (code: number) => {
        throw new Error(`exit:${code}`);
      },
    };

    try {
      const { runNonInteractiveOnboarding } = await import("./onboard-non-interactive.js");
      await runNonInteractiveOnboarding(
        {
          nonInteractive: true,
          authChoice: "openai-api-key",
          openaiApiKey: "sk-openai-test",
          skipHealth: true,
          skipChannels: true,
          skipSkills: true,
          json: true,
        },
        runtime,
      );

      const { CONFIG_PATH } = await import("../config/config.js");
      const cfg = JSON.parse(await fs.readFile(CONFIG_PATH, "utf8")) as {
        agents?: { defaults?: { model?: { primary?: string } } };
      };
      expect(cfg.agents?.defaults?.model?.primary).toBe(OPENAI_DEFAULT_MODEL);
    } finally {
      await fs.rm(tempHome, { recursive: true, force: true });
      process.env.HOME = prev.home;
      process.env.NEUROION_STATE_DIR = prev.stateDir;
      process.env.NEUROION_CONFIG_PATH = prev.configPath;
      process.env.NEUROION_SKIP_CHANNELS = prev.skipChannels;
      process.env.NEUROION_SKIP_GMAIL_WATCHER = prev.skipGmail;
      process.env.NEUROION_SKIP_CRON = prev.skipCron;
      process.env.NEUROION_SKIP_CANVAS_HOST = prev.skipCanvas;
      process.env.NEUROION_GATEWAY_TOKEN = prev.token;
      process.env.NEUROION_GATEWAY_PASSWORD = prev.password;
    }
  }, 60_000);
});
