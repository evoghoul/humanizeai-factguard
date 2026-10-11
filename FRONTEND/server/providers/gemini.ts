import { GoogleGenAI } from "@google/genai"
import type { LlmProvider } from "./types"

export class GeminiProvider implements LlmProvider {
  readonly name = "Google Gemini"
  private ai: GoogleGenAI
  private model: string

  constructor(apiKey: string, modelName?: string) {
    this.ai = new GoogleGenAI({ apiKey, httpOptions: { timeout: 45000 } })
    this.model = modelName || process.env.GEMINI_MODEL || "gemini-2.5-flash"
  }

  async generateJson<T>(prompt: string, systemInstruction?: string): Promise<T> {
    const contents = systemInstruction ? `${systemInstruction}\n\n${prompt}` : prompt
    const response = await this.ai.models.generateContent({
      model: this.model,
      contents,
      config: { responseMimeType: "application/json", temperature: 0.2 },
    })
    const text = response.text || "{}"
    return JSON.parse(text) as T
  }
}
