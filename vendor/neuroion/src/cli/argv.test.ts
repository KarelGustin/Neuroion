import { describe, expect, it } from "vitest";
import {
  buildParseArgv,
  getFlagValue,
  getCommandPath,
  getPrimaryCommand,
  getPositiveIntFlagValue,
  getVerboseFlag,
  hasHelpOrVersion,
  hasFlag,
  shouldMigrateState,
  shouldMigrateStateFromPath,
} from "./argv.js";

describe("argv helpers", () => {
  it("detects help/version flags", () => {
    expect(hasHelpOrVersion(["node", "neuroion", "--help"])).toBe(true);
    expect(hasHelpOrVersion(["node", "neuroion", "-V"])).toBe(true);
    expect(hasHelpOrVersion(["node", "neuroion", "status"])).toBe(false);
  });

  it("extracts command path ignoring flags and terminator", () => {
    expect(getCommandPath(["node", "neuroion", "status", "--json"], 2)).toEqual(["status"]);
    expect(getCommandPath(["node", "neuroion", "agents", "list"], 2)).toEqual(["agents", "list"]);
    expect(getCommandPath(["node", "neuroion", "status", "--", "ignored"], 2)).toEqual(["status"]);
  });

  it("returns primary command", () => {
    expect(getPrimaryCommand(["node", "neuroion", "agents", "list"])).toBe("agents");
    expect(getPrimaryCommand(["node", "neuroion"])).toBeNull();
  });

  it("parses boolean flags and ignores terminator", () => {
    expect(hasFlag(["node", "neuroion", "status", "--json"], "--json")).toBe(true);
    expect(hasFlag(["node", "neuroion", "--", "--json"], "--json")).toBe(false);
  });

  it("extracts flag values with equals and missing values", () => {
    expect(getFlagValue(["node", "neuroion", "status", "--timeout", "5000"], "--timeout")).toBe(
      "5000",
    );
    expect(getFlagValue(["node", "neuroion", "status", "--timeout=2500"], "--timeout")).toBe(
      "2500",
    );
    expect(getFlagValue(["node", "neuroion", "status", "--timeout"], "--timeout")).toBeNull();
    expect(getFlagValue(["node", "neuroion", "status", "--timeout", "--json"], "--timeout")).toBe(
      null,
    );
    expect(getFlagValue(["node", "neuroion", "--", "--timeout=99"], "--timeout")).toBeUndefined();
  });

  it("parses verbose flags", () => {
    expect(getVerboseFlag(["node", "neuroion", "status", "--verbose"])).toBe(true);
    expect(getVerboseFlag(["node", "neuroion", "status", "--debug"])).toBe(false);
    expect(getVerboseFlag(["node", "neuroion", "status", "--debug"], { includeDebug: true })).toBe(
      true,
    );
  });

  it("parses positive integer flag values", () => {
    expect(getPositiveIntFlagValue(["node", "neuroion", "status"], "--timeout")).toBeUndefined();
    expect(
      getPositiveIntFlagValue(["node", "neuroion", "status", "--timeout"], "--timeout"),
    ).toBeNull();
    expect(
      getPositiveIntFlagValue(["node", "neuroion", "status", "--timeout", "5000"], "--timeout"),
    ).toBe(5000);
    expect(
      getPositiveIntFlagValue(["node", "neuroion", "status", "--timeout", "nope"], "--timeout"),
    ).toBeUndefined();
  });

  it("builds parse argv from raw args", () => {
    const nodeArgv = buildParseArgv({
      programName: "neuroion",
      rawArgs: ["node", "neuroion", "status"],
    });
    expect(nodeArgv).toEqual(["node", "neuroion", "status"]);

    const versionedNodeArgv = buildParseArgv({
      programName: "neuroion",
      rawArgs: ["node-22", "neuroion", "status"],
    });
    expect(versionedNodeArgv).toEqual(["node-22", "neuroion", "status"]);

    const versionedNodeWindowsArgv = buildParseArgv({
      programName: "neuroion",
      rawArgs: ["node-22.2.0.exe", "neuroion", "status"],
    });
    expect(versionedNodeWindowsArgv).toEqual(["node-22.2.0.exe", "neuroion", "status"]);

    const versionedNodePatchlessArgv = buildParseArgv({
      programName: "neuroion",
      rawArgs: ["node-22.2", "neuroion", "status"],
    });
    expect(versionedNodePatchlessArgv).toEqual(["node-22.2", "neuroion", "status"]);

    const versionedNodeWindowsPatchlessArgv = buildParseArgv({
      programName: "neuroion",
      rawArgs: ["node-22.2.exe", "neuroion", "status"],
    });
    expect(versionedNodeWindowsPatchlessArgv).toEqual(["node-22.2.exe", "neuroion", "status"]);

    const versionedNodeWithPathArgv = buildParseArgv({
      programName: "neuroion",
      rawArgs: ["/usr/bin/node-22.2.0", "neuroion", "status"],
    });
    expect(versionedNodeWithPathArgv).toEqual(["/usr/bin/node-22.2.0", "neuroion", "status"]);

    const nodejsArgv = buildParseArgv({
      programName: "neuroion",
      rawArgs: ["nodejs", "neuroion", "status"],
    });
    expect(nodejsArgv).toEqual(["nodejs", "neuroion", "status"]);

    const nonVersionedNodeArgv = buildParseArgv({
      programName: "neuroion",
      rawArgs: ["node-dev", "neuroion", "status"],
    });
    expect(nonVersionedNodeArgv).toEqual(["node", "neuroion", "node-dev", "neuroion", "status"]);

    const directArgv = buildParseArgv({
      programName: "neuroion",
      rawArgs: ["neuroion", "status"],
    });
    expect(directArgv).toEqual(["node", "neuroion", "status"]);

    const bunArgv = buildParseArgv({
      programName: "neuroion",
      rawArgs: ["bun", "src/entry.ts", "status"],
    });
    expect(bunArgv).toEqual(["bun", "src/entry.ts", "status"]);
  });

  it("builds parse argv from fallback args", () => {
    const fallbackArgv = buildParseArgv({
      programName: "neuroion",
      fallbackArgv: ["status"],
    });
    expect(fallbackArgv).toEqual(["node", "neuroion", "status"]);
  });

  it("decides when to migrate state", () => {
    expect(shouldMigrateState(["node", "neuroion", "status"])).toBe(false);
    expect(shouldMigrateState(["node", "neuroion", "health"])).toBe(false);
    expect(shouldMigrateState(["node", "neuroion", "sessions"])).toBe(false);
    expect(shouldMigrateState(["node", "neuroion", "memory", "status"])).toBe(false);
    expect(shouldMigrateState(["node", "neuroion", "agent", "--message", "hi"])).toBe(false);
    expect(shouldMigrateState(["node", "neuroion", "agents", "list"])).toBe(true);
    expect(shouldMigrateState(["node", "neuroion", "message", "send"])).toBe(true);
  });

  it("reuses command path for migrate state decisions", () => {
    expect(shouldMigrateStateFromPath(["status"])).toBe(false);
    expect(shouldMigrateStateFromPath(["agents", "list"])).toBe(true);
  });
});
