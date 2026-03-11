/**
 * API helper function tests — pure logic, no HTTP calls.
 * Tests the browserAgentStreamUrl helper and TypeScript types.
 */
import { describe, it, expect } from "vitest";
import { browserAgentStreamUrl } from "@/lib/api";

describe("browserAgentStreamUrl", () => {
  it("encodes the company name", () => {
    const url = browserAgentStreamUrl("Stripe & Co");
    expect(url).toContain("Stripe%20%26%20Co");
  });

  it("returns a path starting with /api", () => {
    const url = browserAgentStreamUrl("Netflix");
    expect(url).toMatch(/^\/api\//);
  });

  it("includes the company_name query param", () => {
    const url = browserAgentStreamUrl("Netflix");
    expect(url).toContain("company_name=Netflix");
  });

  it("points to the stream endpoint", () => {
    const url = browserAgentStreamUrl("Figma");
    expect(url).toContain("/roles/fetch-browser/stream");
  });
});
