import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { normalizeToResult, humanizeText } from "../src/lib/api"
import { defaults } from "../src/lib/model"

describe("api.ts: normalizeToResult", () => {
  it("normalizes a clean HumanizeFastApiResponse with no warnings to passed status", () => {
    const input = "Alex Morgan scored 85% on the assessment."
    const backendData = {
      original: input,
      rewrite: "Alex Morgan achieved a score of 85% on the assessment.",
      warnings: [],
      needs_review: false,
    }

    const res = normalizeToResult(input, backendData, defaults)
    expect(res.original).toBe(input)
    expect(res.revised).toBe(backendData.rewrite)
    expect(res.verification.warnings).toEqual([])
    expect(res.verification.status).toBe("CONTENT INTEGRITY PASSED")
    expect(res.verification.preserved.length).toBeGreaterThan(0)
    expect(res.verification.structural?.numbersPreserved).toBe(true)
  })

  it("normalizes a response with warnings and needs_review to failed/review status", () => {
    const input = "Alex Morgan scored 85% in 2026."
    const backendData = {
      original: input,
      rewrite: "Alex Morgan did well.",
      warnings: ["Number 85% omitted in rewrite.", "Year 2026 omitted."],
      needs_review: true,
    }

    const res = normalizeToResult(input, backendData, defaults)
    expect(res.verification.warnings).toHaveLength(2)
    expect(res.verification.status).toBe("CONTENT INTEGRITY FAILED")
    expect(res.verification.missing.length).toBeGreaterThan(0)
  })

  it("passes through an already complete Result object unchanged", () => {
    const input = "Hello world"
    const fullResult = {
      id: "custom-123",
      timestamp: "2026-03-12T00:00:00.000Z",
      original: input,
      revised: "Hello there world",
      options: defaults,
      findings: [],
      changes: [],
      verification: {
        status: "CONTENT INTEGRITY PASSED",
        preserved: [],
        missing: [],
        added: [],
        warnings: [],
        claims: [],
      },
    }

    const res = normalizeToResult(input, fullResult, defaults)
    expect(res).toBe(fullResult)
  })
})

describe("api.ts: humanizeText", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("rejects empty and whitespace-only text immediately", async () => {
    await expect(humanizeText("   ", defaults)).rejects.toThrow(
      "Paste or type some text to get started.",
    )
  })

  it("rejects text exceeding 12,000 characters", async () => {
    await expect(humanizeText("a".repeat(12001), defaults)).rejects.toThrow(
      "Please keep your text under 12,000 characters.",
    )
  })

  it("successfully calls backend and returns normalized Result", async () => {
    const mockResponse = {
      original: "Test input text",
      rewrite: "Test rewritten text",
      warnings: [],
      needs_review: false,
    }

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    })

    const result = await humanizeText("Test input text", defaults)
    expect(global.fetch).toHaveBeenCalled()
    expect(result.revised).toBe("Test rewritten text")
    expect(result.verification.status).toBe("CONTENT INTEGRITY PASSED")
  })

  it("handles backend error responses with friendly message", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "Please provide non-empty text." }),
    })

    await expect(humanizeText("Valid text", defaults)).rejects.toThrow(
      "Please provide non-empty text.",
    )
  })
})
