/** Pi's native tools with Harbor transport, following Pi's official SSH example.
 * Host-side inference; every model-accessible file/shell operation runs remotely.
 * No fallback to host filesystem or shell when transport fails.
 */
import {
  createReadTool, createWriteTool, createEditTool, createBashTool,
  type ExtensionAPI,
} from "@earendil-works/pi-coding-agent";
import { mapRemotePath } from "./remote_paths.mjs";

export default function (pi: ExtensionAPI) {
  const endpoint = process.env.BIOTASKS_TOOL_ENDPOINT;
  const token = process.env.BIOTASKS_TOOL_TOKEN;
  const cwd = process.env.BIOTASKS_REMOTE_CWD;
  if (!endpoint || !token || !cwd) throw new Error("Remote tool configuration required");
  const remote = (path: string) => mapRemotePath(path, process.cwd(), cwd);
  const call = async (payload: object, signal?: AbortSignal) => {
    const response = await fetch(endpoint, {
      method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload), signal,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `Tool transport failed: ${response.status}`);
    return result;
  };
  const read = {
    readFile: async (path: string) => Buffer.from((await call({ operation: "read", path: remote(path) })).data, "base64"),
    access: async (path: string) => { await call({ operation: "access", path: remote(path) }); },
    detectImageMimeType: async (_path: string) => null,
  };
  const write = {
    writeFile: async (path: string, content: string | Uint8Array) => {
      await call({ operation: "write", path: remote(path), data: Buffer.from(content).toString("base64") });
    },
    mkdir: async (path: string) => { await call({ operation: "mkdir", path: remote(path) }); },
  };
  const bash = {
    exec: async (command: string, workdir: string, options: any) => {
      const result = await call({ operation: "bash", command, cwd: remote(workdir),
        timeout: options.timeout ?? 120 }, options.signal);
      options.onData(Buffer.from(result.stdout + result.stderr));
      return { exitCode: result.exitCode };
    },
  };
  const names = ["sandbox_read", "sandbox_write", "sandbox_edit", "sandbox_bash"];
  for (const tool of [
    createReadTool(cwd, { operations: read }),
    createWriteTool(cwd, { operations: write }),
    createEditTool(cwd, { operations: { ...read, ...write } }),
    createBashTool(cwd, { operations: bash }),
  ]) pi.registerTool({ ...tool, name: `sandbox_${tool.name}` });
  pi.on("session_start", () => { pi.setActiveTools(names); });
  pi.on("user_bash", () => ({ operations: bash }));
  pi.on("before_agent_start", async (event) => {
    const active = pi.getActiveTools();
    if (active.length !== names.length || active.some(name => !names.includes(name))) {
      throw new Error("Unexpected active tools; refusing host execution fallback");
    }
    return { systemPrompt: event.systemPrompt.replaceAll(process.cwd(), cwd) };
  });
}
