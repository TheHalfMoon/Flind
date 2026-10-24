import { describe, expect, it } from "vitest";
import { isStdioMcpServer } from "./presentation";

describe("isStdioMcpServer", () => {
  it.each([
    [null, false],
    [undefined, false],
    [false, false],
    [42, false],
    ["stdio", false],
    [{}, false],
    [{ name: "Flind MCP" }, false],
    [{ transport_type: null }, false],
    [{ transport_type: "sse" }, false],
    [{ transport_type: "stdio" }, true],
    [{ transport_type: "stdio", name: "Flind MCP" }, true],
  ])("safely tests optional transport on %j", (value, expected) => {
    expect(isStdioMcpServer(value)).toBe(expected);
  });
});
