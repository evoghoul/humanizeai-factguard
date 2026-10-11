import {
  type Options,
  type Result,
  type VerificationStatus,
  compareEntities,
  checkStructuralIntegrity,
} from "./model"

export interface HumanizeFastApiResponse {
  original: string
  rewrite: string
  warnings: string[]
  needs_review: boolean
}

export interface RefineApiResponse extends Result {}

/**
 * Normalizes any valid backend response (whether from standard /humanize or /api/refine)
 * into the complete Result structure required by the UI.
 */
export function normalizeToResult(
  inputText: string,
  data: unknown,
  options: Options,
): Result {
  // If response is already a full Result structure
  if (
    data &&
    typeof data === "object" &&
    "verification" in data &&
    "revised" in data
  ) {
    return data as Result
  }

  // Parse as HumanizeFastApiResponse
  const raw = (data || {}) as Partial<HumanizeFastApiResponse>
  const original = typeof raw.original === "string" && raw.original.trim() ? raw.original : inputText
  const revised = typeof raw.rewrite === "string" ? raw.rewrite : inputText
  const warnings = Array.isArray(raw.warnings) ? raw.warnings : []
  const needsReview = Boolean(raw.needs_review)

  const entityDiff = compareEntities(original, revised)
  const structural = checkStructuralIntegrity(original, revised)

  let status: VerificationStatus
  if (typeof raw.needs_review === "boolean") {
    if (raw.needs_review || warnings.length > 0) {
      status = warnings.length > 0 ? "CONTENT INTEGRITY FAILED" : "REVIEW RECOMMENDED"
    } else {
      status = "CONTENT INTEGRITY PASSED"
    }
  } else {
    if (warnings.length > 0) {
      status = "CONTENT INTEGRITY FAILED"
    } else if (
      entityDiff.missing.length > 0 ||
      !structural.numbersPreserved ||
      !structural.negationsPreserved
    ) {
      status = "REVIEW RECOMMENDED"
    } else {
      status = "CONTENT INTEGRITY PASSED"
    }
  }

  return {
    id: typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `humanize-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    timestamp: new Date().toISOString(),
    original,
    revised,
    options,
    findings: [],
    changes: [
      {
        original: "Original text",
        revised: "Refined with FactGuard verification",
        reason: warnings.length === 0
          ? "Natural humanized rewrite with factual consistency verified."
          : `Rewrite completed with ${warnings.length} FactGuard warning(s) flagged for review.`,
      },
    ],
    verification: {
      status,
      preserved: entityDiff.preserved,
      missing: entityDiff.missing,
      added: entityDiff.added,
      warnings,
      claims: [],
      structural,
    },
  }
}

/**
 * Sends text to the HumanizeAI & FactGuard backend.
 * Uses VITE_API_BASE_URL if configured, falling back to Vite relative endpoints.
 */
export async function humanizeText(
  text: string,
  options: Options,
  timeoutMs = 90000,
): Promise<Result> {
  const trimmed = text.trim()
  if (!trimmed) {
    throw new Error("Paste or type some text to get started.")
  }
  if (trimmed.length > 12000) {
    throw new Error("Please keep your text under 12,000 characters.")
  }

  // Candidate endpoints in priority order
  const configuredBaseUrl = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/\/+$/, "")
  const endpoints: string[] = []
  
  // 1. Relative /humanize (Vite proxy - completely immune to CORS)
  endpoints.push(`${import.meta.env.BASE_URL}humanize`)
  
  // 2. Direct local FastAPI backend (has full CORS headers)
  endpoints.push("http://127.0.0.1:8000/humanize")
  
  // 3. Configured base URL if specified
  if (configuredBaseUrl) {
    if (configuredBaseUrl.endsWith("/humanize") || configuredBaseUrl.endsWith("/api/refine")) {
      endpoints.unshift(configuredBaseUrl)
    } else {
      endpoints.unshift(`${configuredBaseUrl}/humanize`)
    }
  }

  const uniqueEndpoints = Array.from(new Set(endpoints))
  let lastError: Error | null = null

  for (const targetUrl of uniqueEndpoints) {
    try {
      const requestBody = targetUrl.endsWith("/api/refine")
        ? { text: trimmed, options }
        : { text: trimmed }

      const response = await fetch(targetUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
        signal: AbortSignal.timeout(timeoutMs),
      })

      if (!response.ok) {
        let errDetail = `Server returned HTTP ${response.status}`
        try {
          const errJson = await response.json()
          if (errJson && errJson.detail) {
            errDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail)
          }
        } catch {
          // ignore json parse error
        }
        throw new Error(errDetail)
      }

      const data = await response.json()
      return normalizeToResult(trimmed, data, options)
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err))
      continue
    }
  }

  if (lastError && lastError.name === "TimeoutError") {
    throw new Error("This request timed out. Your text has been retained. Please retry.")
  }
  throw new Error(
    lastError ? lastError.message : "Unable to connect to the HumanizeAI backend. Please check your connection."
  )
}

