// Leave empty to use Vite dev proxy (/api -> http://127.0.0.1:8000)
// For production, set e.g. VITE_API_BASE_URL=http://10.0.0.5:8000
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export type AskAIChatResponse = {
  response: string
  source?: string
}

export type AskAIHealthResponse = {
  status: string
  ollama_model: string
  ollama_base_url: string
  ollama_connected: boolean
  ollama_model_installed: boolean
  ollama_model_loaded: boolean
  ollama_running_models: string[]
  ollama_message: string
  db_configured: boolean
  db_connected: boolean
  db_message: string
  message: string
}

function apiUrl(path: string) {
  return `${API_BASE_URL}${path}`
}

export async function askAiChat(question: string): Promise<AskAIChatResponse> {
  const res = await fetch(apiUrl('/api/ask-ai/chat'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })

  if (!res.ok) {
    let detail = `AskAI request failed (${res.status})`
    try {
      const data = (await res.json()) as { detail?: string }
      if (data.detail) detail = data.detail
    } catch {
      // ignore json parse errors
    }
    throw new Error(detail)
  }

  return (await res.json()) as AskAIChatResponse
}

export async function askAiHealth(): Promise<AskAIHealthResponse> {
  const res = await fetch(apiUrl('/api/ask-ai/health'))
  if (!res.ok) throw new Error(`Health check failed (${res.status})`)
  return (await res.json()) as AskAIHealthResponse
}
