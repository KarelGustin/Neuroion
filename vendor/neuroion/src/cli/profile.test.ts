import path from "node:path";
import { describe, expect, it } from "vitest";
import { formatCliCommand } from "./command-format.js";
import { applyCliProfileEnv, parseCliProfileArgs } from "./profile.js";

describe("parseCliProfileArgs", () => {
  it("leaves gateway --dev for subcommands", () => {
    const res = parseCliProfileArgs([
      "node",
      "neuroion",
      "gateway",
      "--dev",
      "--allow-unconfigured",
    ]);
    if (!res.ok) {
      throw new Error(res.error);
    }
    expect(res.profile).toBeNull();
    expect(res.argv).toEqual(["node", "neuroion", "gateway", "--dev", "--allow-unconfigured"]);
  });

  it("still accepts global --dev before subcommand", () => {
    const res = parseCliProfileArgs(["node", "neuroion", "--dev", "gateway"]);
    if (!res.ok) {
      throw new Error(res.error);
    }
    expect(res.profile).toBe("dev");
    expect(res.argv).toEqual(["node", "neuroion", "gateway"]);
  });

  it("parses --profile value and strips it", () => {
    const res = parseCliProfileArgs(["node", "neuroion", "--profile", "work", "status"]);
    if (!res.ok) {
      throw new Error(res.error);
    }
    expect(res.profile).toBe("work");
    expect(res.argv).toEqual(["node", "neuroion", "status"]);
  });

  it("rejects missing profile value", () => {
    const res = parseCliProfileArgs(["node", "neuroion", "--profile"]);
    expect(res.ok).toBe(false);
  });

  it("rejects combining --dev with --profile (dev first)", () => {
    const res = parseCliProfileArgs(["node", "neuroion", "--dev", "--profile", "work", "status"]);
    expect(res.ok).toBe(false);
  });

  it("rejects combining --dev with --profile (profile first)", () => {
    const res = parseCliProfileArgs(["node", "neuroion", "--profile", "work", "--dev", "status"]);
    expect(res.ok).toBe(false);
  });
});

describe("applyCliProfileEnv", () => {
  it("fills env defaults for dev profile", () => {
    const env: Record<string, string | undefined> = {};
    applyCliProfileEnv({
      profile: "dev",
      env,
      homedir: () => "/home/peter",
    });
    const expectedStateDir = path.join("/home/peter", ".neuroion-dev");
    expect(env.NEUROION_PROFILE).toBe("dev");
    expect(env.NEUROION_STATE_DIR).toBe(expectedStateDir);
    expect(env.NEUROION_CONFIG_PATH).toBe(path.join(expectedStateDir, "neuroion.json"));
    expect(env.NEUROION_GATEWAY_PORT).toBe("19001");
  });

  it("does not override explicit env values", () => {
    const env: Record<string, string | undefined> = {
      NEUROION_STATE_DIR: "/custom",
      NEUROION_GATEWAY_PORT: "19099",
    };
    applyCliProfileEnv({
      profile: "dev",
      env,
      homedir: () => "/home/peter",
    });
    expect(env.NEUROION_STATE_DIR).toBe("/custom");
    expect(env.NEUROION_GATEWAY_PORT).toBe("19099");
    expect(env.NEUROION_CONFIG_PATH).toBe(path.join("/custom", "neuroion.json"));
  });
});

describe("formatCliCommand", () => {
  it("returns command unchanged when no profile is set", () => {
    expect(formatCliCommand("neuroion doctor --fix", {})).toBe("neuroion doctor --fix");
  });

  it("returns command unchanged when profile is default", () => {
    expect(formatCliCommand("neuroion doctor --fix", { NEUROION_PROFILE: "default" })).toBe(
      "neuroion doctor --fix",
    );
  });

  it("returns command unchanged when profile is Default (case-insensitive)", () => {
    expect(formatCliCommand("neuroion doctor --fix", { NEUROION_PROFILE: "Default" })).toBe(
      "neuroion doctor --fix",
    );
  });

  it("returns command unchanged when profile is invalid", () => {
    expect(formatCliCommand("neuroion doctor --fix", { NEUROION_PROFILE: "bad profile" })).toBe(
      "neuroion doctor --fix",
    );
  });

  it("returns command unchanged when --profile is already present", () => {
    expect(
      formatCliCommand("neuroion --profile work doctor --fix", { NEUROION_PROFILE: "work" }),
    ).toBe("neuroion --profile work doctor --fix");
  });

  it("returns command unchanged when --dev is already present", () => {
    expect(formatCliCommand("neuroion --dev doctor", { NEUROION_PROFILE: "dev" })).toBe(
      "neuroion --dev doctor",
    );
  });

  it("inserts --profile flag when profile is set", () => {
    expect(formatCliCommand("neuroion doctor --fix", { NEUROION_PROFILE: "work" })).toBe(
      "neuroion --profile work doctor --fix",
    );
  });

  it("trims whitespace from profile", () => {
    expect(formatCliCommand("neuroion doctor --fix", { NEUROION_PROFILE: "  jbneuroion  " })).toBe(
      "neuroion --profile jbneuroion doctor --fix",
    );
  });

  it("handles command with no args after neuroion", () => {
    expect(formatCliCommand("neuroion", { NEUROION_PROFILE: "test" })).toBe(
      "neuroion --profile test",
    );
  });

  it("handles pnpm wrapper", () => {
    expect(formatCliCommand("pnpm neuroion doctor", { NEUROION_PROFILE: "work" })).toBe(
      "pnpm neuroion --profile work doctor",
    );
  });
});
