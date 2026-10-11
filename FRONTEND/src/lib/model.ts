export const writingModes = [
  "Clarity Improvement",
  "Grammar Correction",
  "Academic Writing",
  "Professional Writing",
  "Conversational Writing",
  "Technical Writing",
  "Concise Writing",
  "Expanded Explanation",
] as const
export type WritingMode = typeof writingModes[number]

export const verificationStatuses = [
  "CONTENT INTEGRITY PASSED",
  "REVIEW RECOMMENDED",
  "CONTENT INTEGRITY FAILED",
  "VERIFICATION UNAVAILABLE",
] as const
export type VerificationStatus = typeof verificationStatuses[number]

export const contexts = [
  "General Communication",
  "Recruiter Email",
  "Interview Feedback",
  "Interview Question",
  "Professional Report",
] as const
export const tones = ["Professional", "Polished", "Conversational"] as const
export const intensities = ["Light", "Balanced", "Strong"] as const

export type Options = {
  writingMode?: WritingMode
  context: typeof contexts[number]
  tone: typeof tones[number]
  intensity: typeof intensities[number]
}

export type Finding = {
  category: string
  phrase: string
  explanation: string
}

export type Change = {
  original: string
  revised: string
  reason: string
}

export type StructuralCheck = {
  paragraphsPreserved: boolean
  listsPreserved: boolean
  negationsPreserved: boolean
  numbersPreserved: boolean
  details: string[]
}

export type Verification = {
  status: VerificationStatus | string
  preserved: string[]
  missing: string[]
  added: string[]
  warnings: string[]
  claims: string[]
  structural?: StructuralCheck
}

export type Result = {
  id: string
  timestamp: string
  original: string
  revised: string
  options: Options
  findings: Finding[]
  changes: Change[]
  verification: Verification
}

export const defaults: Options = {
  writingMode: "Clarity Improvement",
  context: "General Communication",
  tone: "Professional",
  intensity: "Balanced",
}

export const example =
  "I am writing to inform you that Alex Morgan has successfully completed the technical interview on March 12, 2026. The candidate achieved a score of 85 out of 100 and demonstrated proficiency in React and TypeScript. It is important to note that a follow-up interview may be scheduled next week. Please do not hesitate to reach out if you require any additional information."

export const words = (text: string) =>
  text.trim() ? text.trim().split(/\s+/).length : 0

export function readLocal<T>(key: string, fallback: T): T {
  try {
    const value = localStorage.getItem(key)
    return value ? JSON.parse(value) : fallback
  } catch {
    return fallback
  }
}

export function writeLocal(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
    return true
  } catch {
    return false
  }
}

export function entities(text: string): string[] {
  const matches =
    text.match(
      /[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s*\d{4})?|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}\/\d{1,2}\/\d{2,4}\b|(?:\$|€|£|¥)?\b\d+(?:[.,:/-]\d+)*(?:%|°[CF]|\s*(?:AM|PM|kg|lbs|mph|km\/h|ms|px|GB|MB|KB|GHz|MHz|USD|EUR|GBP|INR)\b)?|\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b|\[\d+\]|\([A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4}\)/g,
    ) || []
  return [...new Set(matches.map((v) => v.replace(/\s+/g, " ").trim()))]
}

export function extractNegations(text: string): string[] {
  const matches = text.match(/\b(?:not|never|neither|nor|no|cannot|can't|won't|didn't|doesn't|isn't|aren't|wasn't|weren't)\b/gi) || []
  return [...new Set(matches.map((v) => v.toLowerCase().trim()))]
}

export function extractListItems(text: string): string[] {
  const lines = text.split(/\r?\n/)
  return lines
    .map((l) => l.trim())
    .filter((l) => /^[-*•]\s+|^\d+[.)]\s+/.test(l))
}

export function checkStructuralIntegrity(original: string, revised: string): StructuralCheck {
  const origParagraphs = original.split(/\n\s*\n/).filter((p) => p.trim().length > 0)
  const revParagraphs = revised.split(/\n\s*\n/).filter((p) => p.trim().length > 0)
  const origLists = extractListItems(original)
  const revLists = extractListItems(revised)
  const origNeg = extractNegations(original)
  const revNeg = extractNegations(revised)

  const entityDiff = compareEntities(original, revised)
  const numbersPreserved = !entityDiff.missing.some((v) => /\d/.test(v))
  const negationsPreserved = origNeg.every((neg) => revNeg.includes(neg)) || origNeg.length === 0
  const listsPreserved = origLists.length === 0 || revLists.length >= origLists.length
  // Allow slight paragraph flexibility if length is single paragraph, but flag collapse if multiple paragraphs
  const paragraphsPreserved = origParagraphs.length <= 1 || revParagraphs.length >= Math.floor(origParagraphs.length * 0.8)

  const details: string[] = []
  if (!numbersPreserved) details.push("One or more numerical values or units appear altered or omitted.")
  if (!negationsPreserved) details.push("A negative qualification (e.g. 'not', 'never', 'cannot') may have been inverted.")
  if (!listsPreserved) details.push("List items or bulleted points from the original text may have been compressed.")
  if (!paragraphsPreserved) details.push("Paragraph structure was condensed compared to the original.")

  return {
    paragraphsPreserved,
    listsPreserved,
    negationsPreserved,
    numbersPreserved,
    details,
  }
}

export function compareEntities(original: string, revised: string) {
  const a = entities(original),
    b = entities(revised)
  const normalized = (s: string) => s.toLowerCase().replace(/\s+/g, " ")
  return {
    preserved: a.filter((x) => b.some((y) => normalized(y) === normalized(x))),
    missing: a.filter((x) => !b.some((y) => normalized(y) === normalized(x))),
    added: b.filter((x) => !a.some((y) => normalized(y) === normalized(x))),
  }
}
export function diffWords(original: string, revised: string) {
  const a = original.split(/(\s+)/),
    b = revised.split(/(\s+)/)
  // Bounded LCS, avoiding quadratic work for the maximum input size.
  if (a.length * b.length > 1_000_000)
    return b.map((text) => ({ text, added: !a.includes(text) }))
  const table = Array.from(
    { length: a.length + 1 },
    () => new Uint16Array(b.length + 1),
  )
  for (let i = a.length - 1; i >= 0; i--)
    for (let j = b.length - 1; j >= 0; j--)
      table[i][j] =
        a[i] === b[j]
          ? table[i + 1][j + 1] + 1
          : Math.max(table[i + 1][j], table[i][j + 1])
  let i = 0,
    j = 0
  const output: {
    text: string
    added: boolean
  }[] = []
  while (j < b.length) {
    if (i < a.length && a[i] === b[j]) {
      output.push({ text: b[j++], added: false })
      i++
    } else if (i < a.length && table[i + 1][j] >= table[i][j + 1]) i++
    else output.push({ text: b[j++], added: true })
  }
  return output
}
