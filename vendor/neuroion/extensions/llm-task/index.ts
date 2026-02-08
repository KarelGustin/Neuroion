import type { NeuroionPluginApi } from "../../src/plugins/types.js";
import { createLlmTaskTool } from "./src/llm-task-tool.js";

export default function register(api: NeuroionPluginApi) {
  api.registerTool(createLlmTaskTool(api), { optional: true });
}
