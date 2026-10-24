import { describe, expect, it } from "vitest";
import { notificationTaskIdToPath, notificationUrlToAppPath } from "./notificationPaths";

describe("Flind Studio notification paths", () => {
  it.each([
    ["/task/task-123", "/task/task-123"],
    ["/report/report_123?source=push", "/report/report_123?source=push"],
    ["flind-studio://task/task-123", "/task/task-123"],
    ["flind-studio://report/report-42?x=1", "/report/report-42?x=1"],
  ])("accepts owned app route %s", (url, expected) => {
    expect(notificationUrlToAppPath(url)).toBe(expected);
  });

  it.each([
    "posthog://task/task-123",
    "mobilehog://task/task-123",
    "https://example.com/task/task-123",
    "javascript:alert(1)",
    "//attacker.example/task/task-123",
    "/settings",
    "/task/../settings",
    "/task/task-123/extra",
    "/task/task%2Fsecret",
    "flind-studio://settings",
    "flind-studio://task/task-123#fragment",
    "flind-studio://user:pass@task/task-123",
  ])("rejects unrelated or unsafe notification destination %s", (url) => {
    expect(notificationUrlToAppPath(url)).toBeNull();
  });

  it("uses the safe legacy taskId fallback without accepting path traversal", () => {
    expect(notificationTaskIdToPath("task-123")).toBe("/task/task-123");
    expect(notificationTaskIdToPath("../settings")).toBeNull();
    expect(notificationTaskIdToPath("")).toBeNull();
    expect(notificationTaskIdToPath(123)).toBeNull();
  });
});
