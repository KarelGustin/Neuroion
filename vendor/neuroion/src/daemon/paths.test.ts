import path from "node:path";
import { describe, expect, it } from "vitest";
import { resolveGatewayStateDir } from "./paths.js";

describe("resolveGatewayStateDir", () => {
  it("uses the default state dir when no overrides are set", () => {
    const env = { HOME: "/Users/test" };
    expect(resolveGatewayStateDir(env)).toBe(path.join("/Users/test", ".neuroion"));
  });

  it("appends the profile suffix when set", () => {
    const env = { HOME: "/Users/test", NEUROION_PROFILE: "rescue" };
    expect(resolveGatewayStateDir(env)).toBe(path.join("/Users/test", ".neuroion-rescue"));
  });

  it("treats default profiles as the base state dir", () => {
    const env = { HOME: "/Users/test", NEUROION_PROFILE: "Default" };
    expect(resolveGatewayStateDir(env)).toBe(path.join("/Users/test", ".neuroion"));
  });

  it("uses NEUROION_STATE_DIR when provided", () => {
    const env = { HOME: "/Users/test", NEUROION_STATE_DIR: "/var/lib/neuroion" };
    expect(resolveGatewayStateDir(env)).toBe(path.resolve("/var/lib/neuroion"));
  });

  it("expands ~ in NEUROION_STATE_DIR", () => {
    const env = { HOME: "/Users/test", NEUROION_STATE_DIR: "~/neuroion-state" };
    expect(resolveGatewayStateDir(env)).toBe(path.resolve("/Users/test/neuroion-state"));
  });

  it("preserves Windows absolute paths without HOME", () => {
    const env = { NEUROION_STATE_DIR: "C:\\State\\neuroion" };
    expect(resolveGatewayStateDir(env)).toBe("C:\\State\\neuroion");
  });
});
