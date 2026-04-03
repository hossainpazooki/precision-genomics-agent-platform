/**
 * MCP Server for Precision Genomics Agent Platform (TypeScript).
 * Migrated from mcp_server/server.py.
 *
 * Exposes 9 genomics tools over MCP (stdio/SSE). Each tool validates
 * input with Zod, delegates to the Python ML service via HTTP, and
 * returns structured JSON output.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { TOOL_REGISTRY, type ToolDefinition } from "./tools/registry";

export function createServer(): Server {
  const server = new Server(
    { name: "genomics-omics-mcp-server", version: "0.2.0" },
    { capabilities: { tools: {} } },
  );

  // List tools
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    const tools = Object.entries(TOOL_REGISTRY).map(
      ([name, def]: [string, ToolDefinition]) => ({
        name,
        description: def.description,
        inputSchema: def.inputSchema,
      }),
    );
    return { tools };
  });

  // Call tool
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    const toolDef = TOOL_REGISTRY[name];
    if (!toolDef) {
      return {
        content: [
          { type: "text" as const, text: JSON.stringify({ error: `Unknown tool: ${name}` }) },
        ],
      };
    }

    try {
      const result = await toolDef.handler(args ?? {});
      return {
        content: [
          { type: "text" as const, text: JSON.stringify(result, null, 2) },
        ],
      };
    } catch (err) {
      const error = err instanceof Error ? err.message : String(err);
      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({ error, tool: name }),
          },
        ],
      };
    }
  });

  return server;
}

// --- Stdio transport ---
async function main() {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(console.error);
