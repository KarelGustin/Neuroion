import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";
import {
  resolveDefaultConfigCandidates,
  resolveConfigPath,
  resolveOAuthDir,
  resolveOAuthPath,
  resolveStateDir,
} from "./paths.js";

describe("oauth paths", () => {
  it("prefers NEUROION_OAUTH_DIR over NEUROION_STATE_DIR", () => {
    const env = {
      NEUROION_OAUTH_DIR: "/custom/oauth",
      NEUROION_STATE_DIR: "/custom/state",
    } as NodeJS.ProcessEnv;

    expect(resolveOAuthDir(env, "/custom/state")).toBe(path.resolve("/custom/oauth"));
    expect(resolveOAuthPath(env, "/custom/state")).toBe(
      path.join(path.resolve("/custom/oauth"), "oauth.json"),
    );
  });

  it("derives oauth path from NEUROION_STATE_DIR when unset", () => {
    const env = {
      NEUROION_STATE_DIR: "/custom/state",
    } as NodeJS.ProcessEnv;

    expect(resolveOAuthDir(env, "/custom/state")).toBe(path.join("/custom/state", "credentials"));
    expect(resolveOAuthPath(env, "/custom/state")).toBe(
      path.join("/custom/state", "credentials", "oauth.json"),
    );
  });
});

describe("state + config path candidates", () => {
  it("uses NEUROION_STATE_DIR when set", () => {
    const env = {
      NEUROION_STATE_DIR: "/new/state",
    } as NodeJS.ProcessEnv;

    expect(resolveStateDir(env, () => "/home/test")).toBe(path.resolve("/new/state"));
  });

  it("orders default config candidates in a stable order", () => {
    const home = "/home/test";
    const candidates = resolveDefaultConfigCandidates({} as NodeJS.ProcessEnv, () => home);
    const expected = [
      path.join(home, ".neuroion", "neuroion.json"),
      path.join(home, ".neuroion", "neuroionbot.json"),
      path.join(home, ".neuroion", "neuroionbot.json"),
      path.join(home, ".neuroion", "moldbot.json"),
      path.join(home, ".neuroionbot", "neuroion.json"),
      path.join(home, ".neuroionbot", "neuroionbot.json"),
      path.join(home, ".neuroionbot", "neuroionbot.json"),
      path.join(home, ".neuroionbot", "moldbot.json"),
      path.join(home, ".neuroionbot", "neuroion.json"),
      path.join(home, ".neuroionbot", "neuroionbot.json"),
      path.join(home, ".neuroionbot", "neuroionbot.json"),
      path.join(home, ".neuroionbot", "moldbot.json"),
      path.join(home, ".moldbot", "neuroion.json"),
      path.join(home, ".moldbot", "neuroionbot.json"),
      path.join(home, ".moldbot", "neuroionbot.json"),
      path.join(home, ".moldbot", "moldbot.json"),
    ];
    expect(candidates).toEqual(expected);
  });

  it("prefers ~/.neuroion when it exists and legacy dir is missing", async () => {
    const root = await fs.mkdtemp(path.join(os.tmpdir(), "neuroion-state-"));
    try {
      const newDir = path.join(root, ".neuroion");
      await fs.mkdir(newDir, { recursive: true });
      const resolved = resolveStateDir({} as NodeJS.ProcessEnv, () => root);
      expect(resolved).toBe(newDir);
    } finally {
      await fs.rm(root, { recursive: true, force: true });
    }
  });

  it("CONFIG_PATH prefers existing config when present", async () => {
    const root = await fs.mkdtemp(path.join(os.tmpdir(), "neuroion-config-"));
    const previousHome = process.env.HOME;
    const previousUserProfile = process.env.USERPROFILE;
    const previousHomeDrive = process.env.HOMEDRIVE;
    const previousHomePath = process.env.HOMEPATH;
    const previousNeuroionConfig = process.env.NEUROION_CONFIG_PATH;
    const previousNeuroionState = process.env.NEUROION_STATE_DIR;
    try {
      const legacyDir = path.join(root, ".neuroion");
      await fs.mkdir(legacyDir, { recursive: true });
      const legacyPath = path.join(legacyDir, "neuroion.json");
      await fs.writeFile(legacyPath, "{}", "utf-8");

      process.env.HOME = root;
      if (process.platform === "win32") {
        process.env.USERPROFILE = root;
        const parsed = path.win32.parse(root);
        process.env.HOMEDRIVE = parsed.root.replace(/\\$/, "");
        process.env.HOMEPATH = root.slice(parsed.root.length - 1);
      }
      delete process.env.NEUROION_CONFIG_PATH;
      delete process.env.NEUROION_STATE_DIR;

      vi.resetModules();
      const { CONFIG_PATH } = await import("./paths.js");
      expect(CONFIG_PATH).toBe(legacyPath);
    } finally {
      if (previousHome === undefined) {
        delete process.env.HOME;
      } else {
        process.env.HOME = previousHome;
      }
      if (previousUserProfile === undefined) {
        delete process.env.USERPROFILE;
      } else {
        process.env.USERPROFILE = previousUserProfile;
      }
      if (previousHomeDrive === undefined) {
        delete process.env.HOMEDRIVE;
      } else {
        process.env.HOMEDRIVE = previousHomeDrive;
      }
      if (previousHomePath === undefined) {
        delete process.env.HOMEPATH;
      } else {
        process.env.HOMEPATH = previousHomePath;
      }
      if (previousNeuroionConfig === undefined) {
        delete process.env.NEUROION_CONFIG_PATH;
      } else {
        process.env.NEUROION_CONFIG_PATH = previousNeuroionConfig;
      }
      if (previousNeuroionConfig === undefined) {
        delete process.env.NEUROION_CONFIG_PATH;
      } else {
        process.env.NEUROION_CONFIG_PATH = previousNeuroionConfig;
      }
      if (previousNeuroionState === undefined) {
        delete process.env.NEUROION_STATE_DIR;
      } else {
        process.env.NEUROION_STATE_DIR = previousNeuroionState;
      }
      if (previousNeuroionState === undefined) {
        delete process.env.NEUROION_STATE_DIR;
      } else {
        process.env.NEUROION_STATE_DIR = previousNeuroionState;
      }
      await fs.rm(root, { recursive: true, force: true });
      vi.resetModules();
    }
  });

  it("respects state dir overrides when config is missing", async () => {
    const root = await fs.mkdtemp(path.join(os.tmpdir(), "neuroion-config-override-"));
    try {
      const legacyDir = path.join(root, ".neuroion");
      await fs.mkdir(legacyDir, { recursive: true });
      const legacyConfig = path.join(legacyDir, "neuroion.json");
      await fs.writeFile(legacyConfig, "{}", "utf-8");

      const overrideDir = path.join(root, "override");
      const env = { NEUROION_STATE_DIR: overrideDir } as NodeJS.ProcessEnv;
      const resolved = resolveConfigPath(env, overrideDir, () => root);
      expect(resolved).toBe(path.join(overrideDir, "neuroion.json"));
    } finally {
      await fs.rm(root, { recursive: true, force: true });
    }
  });
});
