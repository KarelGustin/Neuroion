import { createRequire } from "node:module";

declare const __NEUROION_VERSION__: string | undefined;

function readVersionFromPackageJson(): string | null {
  try {
    const require = createRequire(import.meta.url);
    const pkg = require("../package.json") as { version?: string };
    return pkg.version ?? null;
  } catch {
    return null;
  }
}

function readVersionFromBuildInfo(): string | null {
  try {
    const require = createRequire(import.meta.url);
    const candidates = ["../build-info.json", "./build-info.json"];
    for (const candidate of candidates) {
      try {
        const info = require(candidate) as { version?: string };
        if (info.version) {
          return info.version;
        }
      } catch {
        // ignore missing candidate
      }
    }
    return null;
  } catch {
    return null;
  }
}

// Single source of truth for the current Neuroion version.
// - Embedded/bundled builds: injected define or env var.
// - Dev/npm builds: package.json.
export const VERSION =
  (typeof __NEUROION_VERSION__ === "string" && __NEUROION_VERSION__) ||
  process.env.NEUROION_BUNDLED_VERSION ||
  readVersionFromPackageJson() ||
  readVersionFromBuildInfo() ||
  "0.0.0";
