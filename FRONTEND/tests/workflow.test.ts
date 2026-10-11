import { beforeEach, afterEach, describe, it, expect, vi } from 'vitest'
import {
  compareEntities,
  checkStructuralIntegrity,
  extractNegations,
  extractListItems,
  defaults,
  diffWords,
  readLocal,
  writeLocal,
  words,
  writingModes,
} from '../src/lib/model'

const { generate } = vi.hoisted(() => ({ generate: vi.fn() }))
vi.mock('@google/genai', () => ({ GoogleGenAI: class { models = { generateContent: generate } } }))

import { refine, requestSchema } from '../server/refine'

const original = 'Alex Morgan scored 85% on March 12, 2026. The temperature was 24°C and cost was $450. They did not submit the code [1]. Unless authorized, do not proceed.'
const output = { revised: original, findings: [], changes: [] }
const passed = { warnings: [], claims: [], criticalFailures: [], materialIssue: false }

function response(data: unknown) {
  return { text: JSON.stringify(data) }
}

beforeEach(() => {
  vi.stubEnv('GEMINI_API_KEY', 'mock-test-key')
  generate.mockReset()
})

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('Part 3 & 4: Input, Modes, and Deterministic Integrity Checks', () => {
  it('rejects empty and whitespace-only input', () => {
    expect(requestSchema.safeParse({ text: ' ', options: defaults }).success).toBe(false)
  })

  it('rejects overly long input exceeding character limits', () => {
    expect(requestSchema.safeParse({ text: 'x'.repeat(12001), options: defaults }).success).toBe(false)
  })

  it('accepts all 8 official writing modes', () => {
    for (const mode of writingModes) {
      const res = requestSchema.safeParse({
        text: 'Valid sentence for refinement.',
        options: { ...defaults, writingMode: mode },
      })
      expect(res.success).toBe(true)
    }
  })

  it('counts words accurately across whitespace variants', () => {
    expect(words('')).toBe(0)
    expect(words('   ')).toBe(0)
    expect(words('Hello world')).toBe(2)
    expect(words('  Hello    world  from  HumanizeAI  ')).toBe(4)
  })

  it('preserves names, dates, percentages, currencies, and citations', () => {
    const c = compareEntities(original, original)
    expect(c.preserved).toContain('Alex Morgan')
    expect(c.preserved).toContain('March 12, 2026')
    expect(c.preserved).toContain('85%')
    expect(c.preserved).toContain('$450')
    expect(c.preserved).toContain('[1]')
    expect(c.missing).toEqual([])
  })

  it('flags changed or omitted numerical values', () => {
    const altered = original.replace('85%', '95%')
    const c = compareEntities(original, altered)
    expect(c.missing).toContain('85%')
    expect(c.added).toContain('95%')
  })

  it('extracts and flags altered negations', () => {
    const origNegs = extractNegations(original)
    expect(origNegs).toContain('not')

    const inverted = 'Alex Morgan scored 85%. They did submit the code [1].'
    const invertedNegs = extractNegations(inverted)
    expect(invertedNegs.includes('not')).toBe(false)

    const structural = checkStructuralIntegrity(original, inverted)
    expect(structural.negationsPreserved).toBe(false)
  })

  it('checks structural preservation of bulleted and numbered lists', () => {
    const listDoc = `Requirements:
- First item
- Second item
- Third item`

    const items = extractListItems(listDoc)
    expect(items.length).toBe(3)

    const condensedDoc = 'Requirements: First item, second item, third item.'
    const check = checkStructuralIntegrity(listDoc, condensedDoc)
    expect(check.listsPreserved).toBe(false)
  })

  it('checks structural preservation of multi-paragraph documents', () => {
    const multiPara = `Paragraph one explaining background.

Paragraph two detailing the method.

Paragraph three summarizing findings.`

    const singlePara = 'Paragraph one explaining background. Paragraph two detailing the method. Paragraph three summarizing findings.'
    const check = checkStructuralIntegrity(multiPara, singlePara)
    expect(check.paragraphsPreserved).toBe(false)
  })

  it('highlights additions and deletions with word diff', () => {
    const diff = diffWords('The quick brown fox', 'The fast brown fox')
    expect(diff.some((d) => d.text.trim() === 'fast' && d.added)).toBe(true)
  })
})

describe('Part 4 & 5: Mocked Pipeline and Verification Engine', () => {
  it('reports missing credentials (503) without dispatching model calls', async () => {
    vi.stubEnv('GEMINI_API_KEY', '')
    await expect(refine({ text: original, options: defaults })).rejects.toMatchObject({ status: 503 })
    expect(generate).not.toHaveBeenCalled()
  })

  it('returns CONTENT INTEGRITY PASSED when all deterministic and semantic checks succeed', async () => {
    generate
      .mockResolvedValueOnce(response(output))
      .mockResolvedValueOnce(response(passed))

    const r = await refine({ text: original, options: defaults })
    expect(r.revised).toBe(original)
    expect(r.verification.status).toBe('CONTENT INTEGRITY PASSED')
    expect(r.original).toBe(original)
    expect(generate).toHaveBeenCalledTimes(2)
  })

  it('preserves already-natural text without inventing phantom edits', async () => {
    const naturalText = 'The team finalized the technical roadmap yesterday.'
    generate
      .mockResolvedValueOnce(response({ revised: naturalText, findings: [], changes: [] }))
      .mockResolvedValueOnce(response(passed))

    const res = await refine({ text: naturalText, options: defaults })
    expect(res.changes).toEqual([])
    expect(res.revised).toBe(naturalText)
  })

  it('triggers correction loop when initial rewrite drops a number and successfully restores it', async () => {
    const flawedRewrite = {
      revised: original.replace('85%', 'high score'),
      findings: [],
      changes: [{ original: '85%', revised: 'high score', reason: 'generalization' }],
    }
    const correctedRewrite = {
      revised: original,
      findings: [],
      changes: [],
    }

    // Call 1: Flawed rewrite
    // Call 2: Semantic verify of flawed rewrite
    // Call 3: Correction attempt prompt
    // Call 4: Re-verification after correction
    generate
      .mockResolvedValueOnce(response(flawedRewrite))
      .mockResolvedValueOnce(response({ ...passed, warnings: ['Dropped percentage score'] }))
      .mockResolvedValueOnce(response(correctedRewrite))
      .mockResolvedValueOnce(response(passed))

    const r = await refine({ text: original, options: defaults })
    expect(r.revised).toBe(original)
    expect(r.verification.status).toBe('CONTENT INTEGRITY PASSED')
    expect(generate).toHaveBeenCalledTimes(4)
  })

  it('marks CONTENT INTEGRITY FAILED if critical claims or material issues remain', async () => {
    generate
      .mockResolvedValueOnce(response(output))
      .mockResolvedValueOnce(response({ ...passed, claims: ['Added unverified certification'], materialIssue: true }))

    const r = await refine({ text: original, options: defaults })
    expect(r.verification.status).toBe('CONTENT INTEGRITY FAILED')
    expect(r.original).toBe(original)
  })

  it('marks CONTENT INTEGRITY FAILED if numerical values are altered and correction fails', async () => {
    const altered = original.replace('85%', '95%')
    generate
      .mockResolvedValueOnce(response({ revised: altered, findings: [], changes: [] }))
      .mockResolvedValueOnce(response(passed))
      .mockResolvedValueOnce(response({ revised: altered, findings: [], changes: [] }))
      .mockResolvedValueOnce(response(passed))

    const r = await refine({ text: original, options: defaults })
    expect(r.verification.status).toBe('CONTENT INTEGRITY FAILED')
  })

  it('marks REVIEW RECOMMENDED when minor warnings or stylistic nuances are flagged', async () => {
    generate
      .mockResolvedValueOnce(response(output))
      .mockResolvedValueOnce(response({ ...passed, warnings: ['Slight change in conversational emphasis'] }))

    const r = await refine({ text: original, options: defaults })
    expect(r.verification.status).toBe('REVIEW RECOMMENDED')
  })

  it('marks VERIFICATION UNAVAILABLE when semantic verification fails or times out', async () => {
    generate
      .mockResolvedValueOnce(response(output))
      .mockRejectedValueOnce(new Error('verification timeout'))

    const r = await refine({ text: original, options: defaults })
    expect(r.verification.status).toBe('VERIFICATION UNAVAILABLE')
    expect(r.verification.warnings[0]).toContain('Semantic verification could not complete')
  })

  it('handles API rate limits with status 429', async () => {
    generate.mockRejectedValue({ status: 429 })
    await expect(refine({ text: original, options: defaults })).rejects.toMatchObject({ status: 429 })
  })

  it('handles general service errors with status 502 and retains original text guarantee', async () => {
    generate.mockRejectedValue(new Error('connection refused'))
    await expect(refine({ text: original, options: defaults })).rejects.toMatchObject({ status: 502 })
  })

  it('rejects malformed model outputs with status 502', async () => {
    generate.mockResolvedValue(response({ unexpectedKey: 12345 }))
    await expect(refine({ text: original, options: defaults })).rejects.toMatchObject({ status: 502 })
  })

  it('filters out hallucinated change entries not present in original text', async () => {
    generate
      .mockResolvedValueOnce(
        response({
          revised: original,
          findings: [],
          changes: [{ original: 'fabricated text string', revised: 'test', reason: 'none' }],
        }),
      )
      .mockResolvedValueOnce(response(passed))

    const r = await refine({ text: original, options: defaults })
    expect(r.changes).toEqual([])
  })
})

describe('Browser Storage Persistence and Error Handling', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('saves and restores history sessions', () => {
    const memory = new Map()
    vi.stubGlobal('localStorage', {
      setItem: (k: string, v: string) => memory.set(k, v),
      getItem: (k: string) => memory.get(k),
    })

    const sample = {
      id: 'test-id',
      timestamp: new Date().toISOString(),
      original: 'Sample text',
      revised: 'Refined sample text',
      options: defaults,
      findings: [],
      changes: [],
      verification: {
        status: 'CONTENT INTEGRITY PASSED',
        preserved: [],
        missing: [],
        added: [],
        warnings: [],
        claims: [],
      },
    }

    expect(writeLocal('humanize-history', [sample])).toBe(true)
    expect(readLocal('humanize-history', [])).toEqual([sample])
  })

  it('handles malformed localStorage JSON safely without throwing', () => {
    vi.stubGlobal('localStorage', { getItem: () => '{corrupted-json' })
    expect(readLocal('history', ['fallback'])).toEqual(['fallback'])
  })

  it('handles restricted or disabled localStorage gracefully', () => {
    vi.stubGlobal('localStorage', {
      setItem: () => {
        throw new Error('quota or permission denied')
      },
    })
    expect(writeLocal('history', [])).toBe(false)
  })
})
