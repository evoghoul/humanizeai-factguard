import { useEffect, useState, useRef } from "react"
import {
  ArrowUpRight,
  ArrowRight,
  ArrowDown,
  Sparkles,
  ShieldCheck,
  Check,
  ChevronDown,
  Menu,
  X,
  ScanText,
  SlidersHorizontal,
  Columns2,
  Fingerprint,
  Feather,
  Copy,
  Download,
  RotateCcw,
  Trash2,
  FileText,
  Clock,
  AlertCircle,
  LoaderCircle,
  CheckCheck,
  Settings2,
  WandSparkles,
  Plus,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"
import {
  writingModes,
  contexts,
  tones,
  intensities,
  defaults,
  example,
  words,
  readLocal,
  writeLocal,
  diffWords,
} from "./lib/model"
import type { Options, Result, WritingMode } from "./lib/model"
import { humanizeText } from "./lib/api"

type Page = "home" | "workspace" | "history" | "settings"

const modeDescriptions: Record<string, string> = {
  "Clarity Improvement": "Default. Eliminates stiff/robotic phrasing while preserving exact meaning and length.",
  "Grammar Correction": "Strictly fixes grammar, punctuation, and mechanics without altering voice or structure.",
  "Academic Writing": "Elevates tone to scholarly, objective prose with complete preservation of citations.",
  "Professional Writing": "Direct, executive clarity for business correspondence, proposals, and reports.",
  "Conversational Writing": "Warm, natural human flow while preserving every factual detail and number.",
  "Technical Writing": "Unambiguous precision, step-by-step clarity, and strict terminology integrity.",
  "Concise Writing": "Eliminates wordiness and redundancy without dropping any unique facts or conditions.",
  "Expanded Explanation": "Deepens clarity and flow for complex or dense ideas without altering conclusions.",
}

const descriptions = {
  Light: "Small edits. Your words, a little smoother.",
  Balanced: "A natural balance of clarity, flow, and your voice.",
  Strong: "A fresh structure. The same meaning and facts.",
}
function Brand({ onClick }: { onClick: () => void }) {
  return (
    <button className="brand" onClick={onClick} aria-label="HumanizeAI home">
      <span className="brand-icon">
        <span />
        <span />
        <span />
      </span>
      HUMANIZE<span className="brand-ai">AI</span>
    </button>
  )
}
function Button({
  children,
  onClick,
  secondary = false,
  disabled = false,
  className = "",
  type = "button",
}: {
  children: React.ReactNode
  onClick?: () => void
  secondary?: boolean
  disabled?: boolean
  className?: string
  type?: "button" | "submit"
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`button ${secondary ? "secondary" : "primary"} ${className}`}
    >
      {children}
    </button>
  )
}
function Select({
  label,
  value,
  items,
  onChange,
}: {
  label: string
  value: string
  items: readonly string[]
  onChange: (value: string) => void
}) {
  return (
    <label className="select-field">
      <span>{label}</span>
      <div>
        <select value={value} onChange={(e) => onChange(e.target.value)}>
          {items.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <ChevronDown size={14} />
      </div>
    </label>
  )
}
function FeatureIcon({ icon: Icon }: { icon: LucideIcon }) {
  return (
    <span className="feature-icon">
      <Icon size={21} strokeWidth={1.6} />
    </span>
  )
}

export default function App() {
  const appRef = useRef<HTMLDivElement>(null)
  const [page, setPage] = useState<Page>(
    (["workspace", "history", "settings"].includes(location.hash.slice(1))
      ? location.hash.slice(1)
      : "home") as Page,
  )

  useEffect(() => {
    let targetX = 0
    let targetY = 0
    let targetPxX = typeof window !== "undefined" ? window.innerWidth / 2 : 0
    let targetPxY = typeof window !== "undefined" ? window.innerHeight * 0.35 : 0
    let currentX = 0
    let currentY = 0
    let currentPxX = targetPxX
    let currentPxY = targetPxY
    let animId: number

    const handleMouseMove = (e: MouseEvent) => {
      const centerX = window.innerWidth / 2
      const centerY = window.innerHeight / 2
      targetX = Math.max(-1, Math.min(1, (e.clientX - centerX) / (centerX || 1)))
      targetY = Math.max(-1, Math.min(1, (e.clientY - centerY) / (centerY || 1)))
      targetPxX = e.clientX
      targetPxY = e.clientY
    }

    const animate = () => {
      currentX += (targetX - currentX) * 0.08
      currentY += (targetY - currentY) * 0.08
      currentPxX += (targetPxX - currentPxX) * 0.09
      currentPxY += (targetPxY - currentPxY) * 0.09

      if (appRef.current) {
        const root = appRef.current
        root.style.setProperty("--mouse-x", `${currentPxX.toFixed(1)}px`)
        root.style.setProperty("--mouse-y", `${currentPxY.toFixed(1)}px`)
        root.style.setProperty("--mouse-nx", currentX.toFixed(4))
        root.style.setProperty("--mouse-ny", currentY.toFixed(4))
      }

      animId = requestAnimationFrame(animate)
    }

    window.addEventListener("mousemove", handleMouseMove, { passive: true })
    animId = requestAnimationFrame(animate)

    return () => {
      window.removeEventListener("mousemove", handleMouseMove)
      cancelAnimationFrame(animId)
    }
  }, [])
  const [mobile, setMobile] = useState(false)
  const [input, setInput] = useState("")
  const [preferences, setPreferences] = useState<Options>(() => {
    const p = readLocal<Options>("verba-preferences", defaults)
    return p &&
      contexts.includes(p.context) &&
      tones.includes(p.tone) &&
      intensities.includes(p.intensity)
      ? {
          ...p,
          writingMode: p.writingMode && writingModes.includes(p.writingMode) ? p.writingMode : "Clarity Improvement",
        }
      : defaults
  })
  const [options, setOptions] = useState<Options>(preferences)
  const [history, setHistory] = useState<Result[]>(() => {
    const h = readLocal<Result[]>("verba-history", [])
    return Array.isArray(h)
      ? h.filter(
          (r) =>
            r &&
            typeof r.id === "string" &&
            typeof r.original === "string" &&
            typeof r.revised === "string" &&
            r.options &&
            Array.isArray(r.findings) &&
            Array.isArray(r.changes) &&
            r.verification &&
            Array.isArray(r.verification.preserved) &&
            Array.isArray(r.verification.missing) &&
            Array.isArray(r.verification.added) &&
            Array.isArray(r.verification.warnings) &&
            Array.isArray(r.verification.claims),
        )
      : []
  })
  const [result, setResult] = useState<Result | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [tab, setTab] = useState("Refined text")
  const [toast, setToast] = useState("")
  const [confirmClear, setConfirmClear] = useState(false)
  useEffect(() => {
    if (!confirmClear) return
    const previous = document.activeElement as HTMLElement | null
    const dialog = document.querySelector<HTMLElement>('[role="dialog"]')
    const controls = dialog?.querySelectorAll<HTMLButtonElement>('button')
    controls?.[0]?.focus()
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setConfirmClear(false)
      if (event.key === 'Tab' && controls?.length) {
        const first = controls[0], last = controls[controls.length - 1]
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => { document.removeEventListener('keydown', handleKey); previous?.focus() }
  }, [confirmClear])
  useEffect(() => {
    const f = () => {
      const hash = location.hash.slice(1)
      if (["home", "workspace", "history", "settings"].includes(hash))
        setPage(hash as Page)
    }
    window.addEventListener("hashchange", f)
    return () => window.removeEventListener("hashchange", f)
  }, [])
  useEffect(() => {
    if (!toast) return
    const id = setTimeout(() => setToast(""), 3500)
    return () => clearTimeout(id)
  }, [toast])
  function navigate(p: Page) {
    setPage(p)
    location.hash = p
    setMobile(false)
    window.scrollTo({ top: 0, behavior: "smooth" })
  }
  function section(id: string) {
    if (page !== "home") navigate("home")
    setMobile(false)
    setTimeout(
      () => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }),
      50,
    )
  }
  function updateOptions(key: keyof Options, value: string) {
    setOptions((o) => ({ ...o, [key]: value }))
  }
  function saveHistory(next: Result[]) {
    setHistory(next)
    if (!writeLocal("verba-history", next))
      setToast("Browser storage is unavailable. This session is not saved.")
  }
  async function process(conservative = false) {
    if (loading) return
    if (!input.trim()) {
      setError("Paste or type some text to get started.")
      return
    }
    if (input.length > 12000) {
      setError("Please keep your text under 12,000 characters.")
      return
    }
    setLoading(true)
    setError("")
    setResult(null)
    try {
      const activeOptions = conservative
        ? { ...options, intensity: "Light" as const }
        : options
      const data = await humanizeText(input, activeOptions)
      setResult(data)
      setTab("Refined text")
      saveHistory([data, ...history].slice(0, 100))
    } catch (e) {
      setError(
        e instanceof Error && e.name === "TimeoutError"
          ? "This request timed out. Your text has been retained. Please retry."
          : e instanceof Error
            ? e.message
            : "Unable to connect. Please try again.",
      )
    } finally {
      setLoading(false)
    }
  }
  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text)
      setToast("Copied to clipboard")
    } catch {
      setToast("Clipboard unavailable. Select the text and copy it manually.")
    }
  }
  function download(text: string) {
    try {
      const url = URL.createObjectURL(
        new Blob([text], { type: "text/plain;charset=utf-8" }),
      )
      const a = document.createElement("a")
      a.href = url
      a.download = "humanize-ai-refined.txt"
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      setToast("Text downloaded")
    } catch {
      setToast("Download unavailable in this browser.")
    }
  }
  const openResult = (r: Result) => {
    setResult(r)
    setInput(r.original)
    setOptions(r.options)
    setError("")
    setTab("Refined text")
    navigate("workspace")
  }

  return (
    <div ref={appRef} className={`app ${page === "home" ? "landing" : "interior"}`}>
      <div className="film-grain" aria-hidden="true" />
      <header className="nav-wrap">
        <nav className="navigation" aria-label="Main navigation">
          <Brand onClick={() => navigate("home")} />
          <div className={`nav-links ${mobile ? "mobile-open" : ""}`}>
            <button
              onClick={() => section("product")}
              className={page === "home" ? "active" : ""}
            >
              Product
            </button>
            <button onClick={() => section("how-it-works")}>
              How it works
            </button>
            <button
              onClick={() => navigate("workspace")}
              className={page === "workspace" ? "active" : ""}
            >
              Workspace
            </button>
            <button
              onClick={() => navigate("history")}
              className={page === "history" ? "active" : ""}
            >
              History
            </button>
            <button
              onClick={() => navigate("settings")}
              className={page === "settings" ? "active" : ""}
            >
              Settings
            </button>
          </div>
          <button className="nav-cta" onClick={() => navigate("workspace")}>
            Start writing <ArrowUpRight size={15} />
          </button>
          <button
            className="mobile-toggle"
            aria-label={mobile ? "Close menu" : "Open menu"}
            onClick={() => setMobile(!mobile)}
          >
            {mobile ? <X /> : <Menu />}
          </button>
        </nav>
      </header>
      {page === "home" ? (
        <>
          <main>
            <section className="hero">
              <div className="hero-ambient-glow orb-1" aria-hidden="true" />
              <div className="hero-ambient-glow orb-2" aria-hidden="true" />
              <div className="hero-ambient-glow orb-3" aria-hidden="true" />
              <div className="hero-cursor-spotlight" aria-hidden="true" />
              <div className="hero-grid" />
              <div className="hero-content">
                <div className="eyebrow hero-eyebrow">
                  <span className="status-dot" /> A LITTLE MORE HUMAN. A LOT
                  MORE YOU.
                </div>
                <h1>
                  Make every word
                  <br />
                  feel{" "}
                  <span className="human-word">
                    human
                  <svg
                    aria-hidden="true"
                      viewBox="0 0 390 22"
                      fill="none"
                      preserveAspectRatio="none"
                    >
                      <path
                        d="M3 15C100 1 225 0 386 10M37 20C157 6 267 5 347 12"
                        stroke="currentColor"
                        strokeWidth="3"
                        strokeLinecap="round"
                      />
                    </svg>
                  </span>
                  .
                </h1>
                <p className="hero-description">
                  Your ideas. Your voice. Just a little more natural.
                  <br />
                  Refine AI-generated writing without losing the facts that
                  matter.
                </p>
                <div className="hero-actions">
                  <Button onClick={() => navigate("workspace")}>
                    Start writing <ArrowUpRight size={18} />
                  </Button>
                  <button
                    className="text-link"
                    onClick={() => section("product")}
                  >
                    Explore the possibilities <ArrowRight size={16} />
                  </button>
                </div>
                <div className="hero-editor">
                  <div className="hero-editor-sheen" aria-hidden="true" />
                  <div className="preview-label">
                    <span>
                      <Sparkles size={14} /> A better way to put it
                    </span>
                    <span className="preview-tag">INPUT PREVIEW</span>
                  </div>
                  <textarea
                    aria-label="Your text"
                    placeholder="Paste your text here and let your words flow naturally…"
                    value={input}
                    maxLength={12000}
                    onChange={(e) => setInput(e.target.value)}
                  />
                  <div className="preview-bottom">
                    <button
                      className="sample-button"
                      onClick={() => setInput(example)}
                    >
                      <Plus size={14} /> Try an example
                    </button>
                    <span className="input-hint">
                      Your next great sentence starts here.
                    </span>
                    <button
                      className="submit-circle"
                      aria-label="Open text in writing workspace"
                      onClick={() => navigate("workspace")}
                    >
                      <ArrowUpRight size={23} />
                    </button>
                  </div>
                </div>
                <div className="hero-assurance">
                  <span>
                    <ShieldCheck size={14} /> Facts stay intact
                  </span>
                  <span className="tiny-divider" />
                  <span>
                    <Fingerprint size={14} /> Your voice, not a template
                  </span>
                  <span className="tiny-divider" />
                  <span>
                    <Check size={14} /> No sign-up needed
                  </span>
                </div>
                <button
                  className="scroll-indicator"
                  onClick={() => section("product")}
                  aria-label="Discover HumanizeAI"
                >
                  <ArrowDown size={17} />
                </button>
              </div>
            </section>
            <section id="product" className="product-section">
              <div className="section-topline">
                <span className="eyebrow">
                  <span className="small-square" /> INTELLIGENT WRITING.
                  INTENTIONALLY HUMAN.
                </span>
                <span className="section-number">01 / THE DIFFERENCE</span>
              </div>
              <div className="section-heading-row">
                <h2>
                  Better expression.
                  <br />
                  <span>The same meaning.</span>
                </h2>
                <p>
                  Good writing isn’t just about sounding human.
                  <br />
                  It’s about saying what you mean—and keeping
                  <br />
                  every important detail along the way.
                </p>
              </div>
              <div className="features-grid">
                {[
                  {
                    icon: ScanText,
                    name: "Understand the words.",
                    text: "Spot repetitive phrases, stiff language, and the things that don’t quite sound like you.",
                    tag: "THOUGHTFUL ANALYSIS",
                  },
                  {
                    icon: Feather,
                    name: "Find your natural voice.",
                    text: "Fine-tune your tone and context. Turn robotic sentences into writing that feels right.",
                    tag: "CONTEXT-AWARE REFINEMENT",
                  },
                  {
                    icon: ShieldCheck,
                    name: "Keep the facts intact.",
                    text: "A separate verification step checks the details, so clarity doesn’t come at a cost.",
                    tag: "INDEPENDENT VERIFICATION",
                  },
                ].map((f, i) => (
                  <article className="feature" key={f.name}>
                    <div className="feature-top">
                      <FeatureIcon icon={f.icon} />
                      <span>0{i + 1}</span>
                    </div>
                    <h3>{f.name}</h3>
                    <p>{f.text}</p>
                    <span className="feature-tag">
                      {f.tag}
                      <ArrowUpRight size={13} />
                    </span>
                  </article>
                ))}
              </div>
              <div className="compare-strip">
                <div>
                  <Columns2 size={20} />
                  <span>Nothing hidden. Every change explained.</span>
                </div>
                <p>Compare the original. Understand the edit. Make it yours.</p>
                <button onClick={() => navigate("workspace")}>
                  Meet your workspace <ArrowUpRight size={16} />
                </button>
              </div>
            </section>
            <section id="how-it-works" className="how-section">
              <div className="section-topline">
                <span className="eyebrow">
                  <span className="small-square" /> LESS FRICTION. BETTER
                  WRITING.
                </span>
                <span className="section-number">02 / THE PROCESS</span>
              </div>
              <div className="section-heading-row">
                <h2>
                  From almost right
                  <br />
                  to <span>just like you.</span>
                </h2>
                <Button secondary onClick={() => navigate("workspace")}>
                  Let’s write something <ArrowUpRight size={16} />
                </Button>
              </div>
              <div className="steps">
                {[
                  ["Paste your text", "Bring a draft, an email, or a thought."],
                  [
                    "Make it your own",
                    "Choose a context, tone, and intensity.",
                  ],
                  [
                    "Refine & verify",
                    "Natural words. Carefully checked details.",
                  ],
                  [
                    "Review & share",
                    "Compare the changes. Copy with confidence.",
                  ],
                ].map(([title, subtitle], i) => (
                  <div className="step" key={title}>
                    <div className="step-num">
                      0{i + 1}
                      <span />
                    </div>
                    <h3>{title}</h3>
                    <p>{subtitle}</p>
                  </div>
                ))}
              </div>
            </section>
            <section className="closing">
              <span className="eyebrow">SAME IDEAS. A MORE HUMAN TOUCH.</span>
              <h2>
                Your words.
                <br />
                Their best version.
              </h2>
              <Button onClick={() => navigate("workspace")}>
                Find your flow <ArrowUpRight size={19} />
              </Button>
              <p>No account. No extra steps. Just better writing.</p>
            </section>
          </main>
        </>
      ) : (
        <main className="workspace-main">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span className="status-dot" />
                {page === "workspace"
                  ? "YOUR WORDS, REFINED"
                  : page === "history"
                    ? "YOUR WRITING JOURNEY"
                    : "MAKE YOURSELF AT HOME"}
              </div>
              <h1>
                {page === "workspace"
                  ? "Humanization Studio"
                  : page === "history"
                    ? "Writing history"
                    : "Your preferences"}
                <span>.</span>
              </h1>
              <p>
                {page === "workspace"
                  ? "Refine the expression. Preserve the meaning."
                  : page === "history"
                    ? "Good words are worth coming back to."
                    : "A workspace that starts the way you like it."}
              </p>
            </div>
            <span className="page-badge">
              {page === "workspace" ? (
                <>
                  <span className={`status-dot ${loading ? "pulse" : ""}`} />
                  {loading
                    ? "Refining & verifying"
                    : result
                      ? "Ready to review"
                      : "Ready when you are"}
                </>
              ) : (
                <>
                  <Settings2 size={14} /> Stored in this browser
                </>
              )}
            </span>
          </div>
          {page === "workspace" && (
            <>
              <div className="controls-panel">
                <Select
                  label="WRITING MODE"
                  value={options.writingMode || "Clarity Improvement"}
                  items={writingModes}
                  onChange={(v) => updateOptions("writingMode", v)}
                />
                <Select
                  label="WRITING CONTEXT"
                  value={options.context}
                  items={contexts}
                  onChange={(v) => updateOptions("context", v)}
                />
                <Select
                  label="TONE OF VOICE"
                  value={options.tone}
                  items={tones}
                  onChange={(v) => updateOptions("tone", v)}
                />
                <div className="intensity-field">
                  <span>HUMANIZATION INTENSITY</span>
                  <div className="segmented">
                    {intensities.map((i) => (
                      <button
                        key={i}
                        className={options.intensity === i ? "selected" : ""}
                        onClick={() => updateOptions("intensity", i)}
                        title={descriptions[i]}
                      >
                        {i}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="intensity-description">
                <SlidersHorizontal size={13} />
                <span>
                  <strong>{options.writingMode || "Clarity Improvement"}:</strong>{" "}
                  {modeDescriptions[options.writingMode || "Clarity Improvement"]} ·{" "}
                  {descriptions[options.intensity]}
                </span>
              </div>
              <div className="editors">
                <section className="editor-panel">
                  <div className="editor-heading">
                    <span>
                      <FileText size={16} /> Original text
                    </span>
                    <div>
                      <button
                        title="Load synthetic example"
                        onClick={() => {
                          setInput(example)
                          setError("")
                        }}
                      >
                        Load example
                      </button>
                      <button
                        aria-label="Clear original text"
                        disabled={loading}
                        onClick={() => {
                          setInput("")
                          setResult(null)
                          setError("")
                        }}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                  <textarea
                    aria-label="Original text"
                    maxLength={12000}
                    value={input}
                    disabled={loading}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Paste your AI-generated text here. An email, a report, a rough draft—let’s make it feel like you."
                  />
                  <div className="editor-footer">
                    <span>
                      {words(input)} words <span>·</span>{" "}
                      {input.length.toLocaleString()} / 12,000 characters
                    </span>
                    <span>YOUR STARTING POINT</span>
                  </div>
                </section>
                <section className="editor-panel result-panel">
                  <div className="editor-heading">
                    <span>
                      <Sparkles size={16} /> Refined text
                    </span>
                    {result && (
                      <div>
                        <button
                          aria-label="Copy refined text"
                          onClick={() => copy(result.revised)}
                        >
                          <Copy size={15} />
                        </button>
                        <button
                          aria-label="Download refined text"
                          onClick={() => download(result.revised)}
                        >
                          <Download size={15} />
                        </button>
                      </div>
                    )}
                  </div>
                  {loading ? (
                    <div className="editor-empty">
                      <LoaderCircle className="spinner" size={32} />
                      <h3>A little clarity is on its way.</h3>
                      <p>
                        Refining your words, then independently
                        <br />
                        checking the meaning and important details.
                      </p>
                    </div>
                  ) : result ? (
                    <div className="output-text">{result.revised}</div>
                  ) : (
                    <div className="editor-empty">
                      <div className="empty-icon">
                        <Feather size={29} strokeWidth={1.4} />
                      </div>
                      <h3>Room for your best words.</h3>
                      <p>
                        Your refined writing will appear here.
                        <br />
                        Same meaning. A more natural flow.
                      </p>
                    </div>
                  )}
                  <div className="editor-footer">
                    <span>
                      {result
                        ? `${words(result.revised)} words`
                        : "A fresh perspective, not a different story."}
                    </span>
                    {result ? (
                      <button onClick={() => process()} disabled={loading}>
                        <RotateCcw size={12} /> Regenerate
                      </button>
                    ) : (
                      <ShieldCheck size={14} />
                    )}
                  </div>
                </section>
              </div>
              {error && (
                <div className="error-banner" role="alert">
                  <AlertCircle size={19} />
                  <div>
                    <strong>We couldn’t refine this text.</strong>
                    <p>{error}</p>
                  </div>
                  <button onClick={() => process()}>
                    Retry <RotateCcw size={14} />
                  </button>
                </div>
              )}
              <div className="analyze-row">
                <p>
                  <ShieldCheck size={15} /> Your facts matter. Verification runs
                  after every rewrite.
                </p>
                <Button onClick={() => process()} disabled={loading}>
                  {loading ? (
                    <>
                      <LoaderCircle size={17} className="spinner" /> Refining &
                      verifying…
                    </>
                  ) : (
                    <>
                      <WandSparkles size={17} /> Analyze & refine{" "}
                      <ArrowUpRight size={16} />
                    </>
                  )}
                </Button>
              </div>
              {result && (
                <section className="results-section">
                  <div className="results-header">
                    <h2>A closer look</h2>
                    <div className="result-tabs">
                      {[
                        "Refined text",
                        "Comparison",
                        "Verification report",
                      ].map((t) => (
                        <button
                          key={t}
                          className={tab === t ? "selected" : ""}
                          onClick={() => setTab(t)}
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>
                  {tab === "Verification report" ? (
                    <div className="report-grid">
                      <div className="report-card">
                        <h3>
                          <ShieldCheck size={19} /> {result.verification.status}
                        </h3>
                        <p>
                          Exact-value checks and independent AI-assisted review.
                        </p>
                        <div className="entity-groups">
                          <h4>Preserved entities</h4>
                          <div className="entity-tags">
                            {result.verification.preserved.length ? (
                              result.verification.preserved.map((e) => (
                                <span key={e}>
                                  <Check size={12} />
                                  {e}
                                </span>
                              ))
                            ) : (
                              <p>No exact-match entities identified.</p>
                            )}
                          </div>
                          <h4>Missing or changed values</h4>
                          <div>
                            {result.verification.missing.length ? (
                              result.verification.missing.map((e) => (
                                <p key={e} className="warning-text">
                                  {e}
                                </p>
                              ))
                            ) : (
                              <p>No missing exact values detected.</p>
                            )}
                          </div>
                          <h4>New values to review</h4>
                          {result.verification.added.length ? (
                            result.verification.added.map((e) => (
                              <p key={e} className="warning-text">
                                {e}
                              </p>
                            ))
                          ) : (
                            <p>No new exact values detected.</p>
                          )}
                        </div>
                        {result.verification.structural && (
                          <div className="entity-groups" style={{ marginTop: "1.25rem", paddingTop: "1rem", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
                            <h4>Structural integrity checks</h4>
                            <div className="entity-tags">
                              <span>
                                {result.verification.structural.numbersPreserved ? <Check size={12} /> : <AlertCircle size={12} />}
                                Numbers & measurements: {result.verification.structural.numbersPreserved ? "Preserved" : "Review needed"}
                              </span>
                              <span>
                                {result.verification.structural.negationsPreserved ? <Check size={12} /> : <AlertCircle size={12} />}
                                Negations & conditions: {result.verification.structural.negationsPreserved ? "Preserved" : "Review needed"}
                              </span>
                              <span>
                                {result.verification.structural.listsPreserved ? <Check size={12} /> : <AlertCircle size={12} />}
                                Lists & bullets: {result.verification.structural.listsPreserved ? "Intact" : "Condensed"}
                              </span>
                              <span>
                                {result.verification.structural.paragraphsPreserved ? <Check size={12} /> : <AlertCircle size={12} />}
                                Paragraph scope: {result.verification.structural.paragraphsPreserved ? "Intact" : "Condensed"}
                              </span>
                            </div>
                            {result.verification.structural.details.length > 0 && (
                              <div style={{ marginTop: "0.5rem" }}>
                                {result.verification.structural.details.map((d, i) => (
                                  <p key={i} className="warning-text">{d}</p>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="report-card">
                        <h3>Meaning & claims</h3>
                        {[
                          ...result.verification.warnings,
                          ...result.verification.claims,
                        ].length ? (
                          [
                            ...result.verification.warnings,
                            ...result.verification.claims,
                          ].map((w, i) => (
                            <p className="warning-text" key={i}>
                              {w}
                            </p>
                          ))
                        ) : (
                          <p>
                            Semantic review found no concerns requiring a
                            warning.
                          </p>
                        )}
                        <div className="verification-note">
                          <AlertCircle size={16} />
                          <p>
                            Automated checks do not guarantee factual accuracy.
                            Entity extraction is heuristic and may miss names or
                            technical terms. Always review important
                            communication yourself.
                          </p>
                        </div>
                        {result.verification.status !== "CONTENT INTEGRITY PASSED" && result.verification.status !== "Checks passed" && (
                          <Button secondary onClick={() => process(true)}>
                            Try a conservative rewrite <RotateCcw size={14} />
                          </Button>
                        )}
                      </div>
                    </div>
                  ) : tab === "Comparison" ? (
                    <div className="report-grid">
                      <div className="report-card">
                        <h3>Original · {words(result.original)} words</h3>
                        <p className="comparison-text">
                          {diffWords(result.revised, result.original).map(
                            (part, i) => (
                              <span
                                className={part.added ? "removed-word" : ""}
                                key={i}
                              >
                                {part.text}
                              </span>
                            ),
                          )}
                        </p>
                      </div>
                      <div className="report-card">
                        <h3>Refined · {words(result.revised)} words</h3>
                        <p className="comparison-text">
                          {diffWords(result.original, result.revised).map(
                            (part, i) => (
                              <span
                                className={part.added ? "added-word" : ""}
                                key={i}
                              >
                                {part.text}
                              </span>
                            ),
                          )}
                        </p>
                        <small>Highlighted wording was added or changed.</small>
                      </div>
                    </div>
                  ) : (
                    <div className="report-card">
                      <div className="report-summary">
                        {result.options.writingMode && <span>{result.options.writingMode}</span>}
                        <span>{result.options.context}</span>
                        <span>{result.options.tone}</span>
                        <span>{result.options.intensity}</span>
                        <span>
                          <ShieldCheck size={13} />
                          {result.verification.status}
                        </span>
                      </div>
                      <h3>Why was this changed?</h3>
                      {result.changes.length ? (
                        result.changes.map((c, i) => (
                          <div className="change-row" key={i}>
                            <div>
                              <span className="old-phrase">{c.original}</span>
                              <ArrowRight size={13} />
                              <span>{c.revised}</span>
                            </div>
                            <p>{c.reason}</p>
                          </div>
                        ))
                      ) : (
                        <p>No substantial wording changes were needed.</p>
                      )}
                    </div>
                  )}
                  <div className="report-card analysis-card">
                    <h3>
                      <ScanText size={18} /> Writing analysis
                    </h3>
                    {result.findings.length ? (
                      result.findings.map((f, i) => (
                        <div className="finding" key={i}>
                          <span>{f.category}</span>
                          <q>{f.phrase}</q>
                          <p>{f.explanation}</p>
                        </div>
                      ))
                    ) : (
                      <p>
                        No supported robotic-language issues were identified.
                        Minimal changes may be appropriate.
                      </p>
                    )}
                  </div>
                </section>
              )}
            </>
          )}
          {page === "history" && (
            <>
              <div className="history-toolbar">
                <span>
                  <Clock size={16} />
                  {history.length} saved{" "}
                  {history.length === 1 ? "session" : "sessions"}
                </span>
                {history.length > 0 && (
                  <Button secondary onClick={() => setConfirmClear(true)}>
                    <Trash2 size={14} /> Clear history
                  </Button>
                )}
              </div>
              {history.length ? (
                <div className="history-list">
                  {history.map((r) => (
                    <article className="history-card" key={r.id}>
                      <div className="history-card-icon">
                        <FileText size={21} />
                      </div>
                      <div className="history-content">
                        <div className="history-meta">
                          <span>{r.options.context}</span>
                          <span>{new Date(r.timestamp).toLocaleString()}</span>
                        </div>
                        <h3>
                          {r.revised.slice(0, 100)}
                          {r.revised.length > 100 ? "…" : ""}
                        </h3>
                        <div className="history-tags">
                          <span>{r.options.tone}</span>
                          <span>{r.options.intensity}</span>
                          <span>
                            <ShieldCheck size={12} />
                            {r.verification.status}
                          </span>
                        </div>
                      </div>
                      <div className="history-actions">
                        <button
                          aria-label="Copy saved result"
                          onClick={() => copy(r.revised)}
                        >
                          <Copy size={16} />
                        </button>
                        <button
                          aria-label="Delete session"
                          onClick={() =>
                            saveHistory(history.filter((h) => h.id !== r.id))
                          }
                        >
                          <Trash2 size={16} />
                        </button>
                        <button
                          className="open-session"
                          onClick={() => openResult(r)}
                        >
                          Reopen <ArrowUpRight size={15} />
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="empty-page">
                  <div className="empty-icon">
                    <Clock size={32} />
                  </div>
                  <h2>A clean slate. Full of possibilities.</h2>
                  <p>
                    Your completed writing sessions will appear here.
                    <br />
                    Create something worth coming back to.
                  </p>
                  <Button onClick={() => navigate("workspace")}>
                    Start writing <ArrowUpRight size={17} />
                  </Button>
                </div>
              )}
              <div className="privacy-note">
                <ShieldCheck size={17} />
                <p>
                  History is saved only in this browser. It doesn’t sync across
                  devices. Clearing browser data removes your sessions. Text is
                  sent to Google Gemini only when you choose to refine it.
                </p>
              </div>
            </>
          )}
          {page === "settings" && (
            <div className="settings-grid">
              <section className="settings-card">
                <div className="settings-title">
                  <FeatureIcon icon={SlidersHorizontal} />
                  <div>
                    <h2>Your writing defaults</h2>
                    <p>A familiar starting point for every new session.</p>
                  </div>
                </div>
                <Select
                  label="DEFAULT WRITING MODE"
                  value={preferences.writingMode || "Clarity Improvement"}
                  items={writingModes}
                  onChange={(v) =>
                    setPreferences((p) => ({
                      ...p,
                      writingMode: v as Options["writingMode"],
                    }))
                  }
                />
                <Select
                  label="DEFAULT CONTEXT"
                  value={preferences.context}
                  items={contexts}
                  onChange={(v) =>
                    setPreferences((p) => ({
                      ...p,
                      context: v as Options["context"],
                    }))
                  }
                />
                <Select
                  label="DEFAULT TONE"
                  value={preferences.tone}
                  items={tones}
                  onChange={(v) =>
                    setPreferences((p) => ({
                      ...p,
                      tone: v as Options["tone"],
                    }))
                  }
                />
                <Select
                  label="DEFAULT INTENSITY"
                  value={preferences.intensity}
                  items={intensities}
                  onChange={(v) =>
                    setPreferences((p) => ({
                      ...p,
                      intensity: v as Options["intensity"],
                    }))
                  }
                />
                <p className="setting-helper">
                  {descriptions[preferences.intensity]}
                </p>
                <Button
                  onClick={() => {
                    setOptions(preferences)
                    setToast(
                      writeLocal("verba-preferences", preferences)
                        ? "Preferences saved"
                        : "Browser storage unavailable. Preferences applied for this session.",
                    )
                  }}
                >
                  Save preferences <Check size={16} />
                </Button>
              </section>
              <div>
                <section className="settings-card">
                  <div className="settings-title">
                    <FeatureIcon icon={ShieldCheck} />
                    <div>
                      <h2>Your data, your choice</h2>
                      <p>No account. No cloud-synced history.</p>
                    </div>
                  </div>
                  <p className="settings-copy">
                    Your history and preferences stay in this browser. Your text
                    is sent to Google Gemini only when you click Analyze &
                    refine. Don’t submit confidential or sensitive information
                    without authorization.
                  </p>
                  <div className="data-row">
                    <span>Saved writing sessions</span>
                    <strong>{history.length}</strong>
                  </div>
                  <Button secondary onClick={() => setConfirmClear(true)}>
                    <Trash2 size={15} /> Clear local history
                  </Button>
                </section>
                <section className="settings-card about-card">
                  <div className="eyebrow">A NOTE ON VERIFICATION</div>
                  <h3>
                    A thoughtful second look.
                    <br />
                    Not a guarantee.
                  </h3>
                  <p>
                    HumanizeAI checks important details and meaning, but automated
                    verification has limits. You’re always the final editor.
                  </p>
                </section>
              </div>
            </div>
          )}
        </main>
      )}
      <footer className="footer">
        <div className="footer-main">
          <div>
            <Brand onClick={() => navigate("home")} />
            <p>
              Make AI sound natural.
              <br />
              Keep every fact intact.
            </p>
          </div>
          <div className="footer-links">
            <button onClick={() => navigate("workspace")}>Workspace</button>
            <button onClick={() => section("how-it-works")}>
              How it works
            </button>
            <button onClick={() => navigate("settings")}>
              Privacy & preferences
            </button>
          </div>
          <div className="footer-signoff">
            <span className="status-dot" /> BUILT FOR THE HUMAN IN YOU.
          </div>
        </div>
        <div className="footer-bottom">
          <span>© {new Date().getFullYear()} HumanizeAI</span>
          <span>Refine the expression. Preserve the meaning.</span>
          <span>Thoughtfully made. Carefully verified.</span>
        </div>
      </footer>
      {toast && (
        <div className="toast" role="status">
          <CheckCheck size={17} />
          {toast}
          <button
            aria-label="Dismiss notification"
            onClick={() => setToast("")}
          >
            <X size={14} />
          </button>
        </div>
      )}
      {confirmClear && (
        <div className="modal-backdrop" onClick={() => setConfirmClear(false)}>
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
            className="modal"
            onClick={(e) => e.stopPropagation()}
          >
            <FeatureIcon icon={Trash2} />
            <h2 id="modal-title">Clear your writing history?</h2>
            <p>
              This permanently removes all {history.length} sessions from this
              browser. Your preferences won’t be changed.
            </p>
            <div>
              <Button secondary onClick={() => setConfirmClear(false)}>
                Keep my history
              </Button>
              <Button
                onClick={() => {
                  saveHistory([])
                  setConfirmClear(false)
                  setToast("Local history cleared")
                }}
              >
                Clear history
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
