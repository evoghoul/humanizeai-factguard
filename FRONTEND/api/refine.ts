import { ApiError, refine } from "../server/refine"

const FASTAPI_URL = process.env.FASTAPI_URL || process.env.BACKEND_URL

async function forwardToFastApi(input: unknown) {
  if (!FASTAPI_URL) return null
  const response = await fetch(`${FASTAPI_URL}/api/refine`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal: AbortSignal.timeout(45000),
  })
  if (!response.ok) {
    const errorData = (await response.json().catch(() => ({}))) as { detail?: string; error?: string }
    throw new ApiError(response.status, errorData.detail || errorData.error || "FastAPI backend error.")
  }
  return await response.json()
}

export default async function handler(
  req: { method?: string; body: unknown },
  res: { status: (code: number) => typeof res; json: (data: unknown) => void },
) {
  if (req.method !== "POST") return res.status(405).json({ error: "Use POST." })

  if (process.env.AI_PROVIDER?.toLowerCase() === "fastapi" && FASTAPI_URL) {
    try {
      const fastApiResult = await forwardToFastApi(req.body)
      return res.status(200).json(fastApiResult)
    } catch (e) {
      return res
        .status(e instanceof ApiError ? e.status : 500)
        .json({ error: e instanceof ApiError ? e.message : "FastAPI backend error." })
    }
  }

  try {
    return res.status(200).json(await refine(req.body))
  } catch (e) {
    if (FASTAPI_URL) {
      try {
        const fastApiResult = await forwardToFastApi(req.body)
        if (fastApiResult) return res.status(200).json(fastApiResult)
      } catch {
        // Fall back to original error
      }
    }
    return res
      .status(e instanceof ApiError ? e.status : 500)
      .json({
        error:
          e instanceof ApiError ? e.message : "Unable to process this request.",
      })
  }
}

