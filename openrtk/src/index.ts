import type { Plugin } from "@opencode-ai/plugin"
import { rewrite } from "./rewrite"

export const rtkPlugin: Plugin = async ({ $ }) => {
  // Check rtk is installed at plugin load time
  try {
    await $`which rtk`.quiet()
  } catch {
    console.warn("[openrtk] rtk binary not found in PATH — plugin disabled")
    return {}
  }
  console.log("[openrtk] Extension RTK chargée et opérationnelle.");

  return {
    "tool.execute.before": async (input, output) => {
      const tool = String(input?.tool ?? "").toLowerCase()
      if (!tool.includes("bash") && !tool.includes("shell")) return

      const args = output?.args
      if (!args || typeof args !== "object") return

      const command = (args as Record<string, unknown>).command
      if (typeof command !== "string") return

      const rewritten = rewrite(command)
      if (rewritten) {
        ;(args as Record<string, unknown>).command = rewritten
      }
    },
  }
}

export default rtkPlugin
