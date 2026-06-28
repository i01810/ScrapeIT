import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { Bot, Send, Sparkles } from 'lucide-react'
import { askAiChat, askAiHealth } from '../api/askAi'
import { cn } from '../lib/cn'

type Role = 'user' | 'assistant'

type ChatMessage = {
  id: string
  role: Role
  content: string
  createdAt: string
}

const SUGGESTIONS = [
  'How many orders are pending payment?',
  'Show UPI vs Card payment split',
  'Which orders failed payment today?',
]

const WELCOME: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content:
    'Hi! Ask me about orders, payments, refunds, and payment methods. I query your database using a local LLM (Ollama) on the backend.',
  createdAt: new Date().toISOString(),
}

function makeId() {
  return `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function renderMarkdownLite(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={idx} className="font-semibold text-zinc-900">
          {part.slice(2, -2)}
        </strong>
      )
    }
    return <span key={idx}>{part}</span>
  })
}

export default function AskAIPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME])
  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking')
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const inputRef = useRef<HTMLTextAreaElement | null>(null)

  const canSend = input.trim().length > 0 && !isThinking

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isThinking])

  useEffect(() => {
    void askAiHealth()
      .then(() => setBackendStatus('online'))
      .catch(() => setBackendStatus('offline'))
  }, [])

  async function sendMessage(text: string) {
    const trimmed = text.trim()
    if (!trimmed || isThinking) return

    const userMessage: ChatMessage = {
      id: makeId(),
      role: 'user',
      content: trimmed,
      createdAt: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsThinking(true)

    try {
      const result = await askAiChat(trimmed)
      const assistantMessage: ChatMessage = {
        id: makeId(),
        role: 'assistant',
        content: result.response,
        createdAt: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, assistantMessage])
      setBackendStatus('online')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'AskAI request failed.'
      const assistantMessage: ChatMessage = {
        id: makeId(),
        role: 'assistant',
        content:
          `I could not reach the AskAI backend.\n\n**Error:** ${message}\n\n` +
          'Start backend with:\n`python -m uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000`\n\n' +
          'Also ensure Ollama is running and DB settings are filled in `backend/config.py`.',
        createdAt: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, assistantMessage])
      setBackendStatus('offline')
    } finally {
      setIsThinking(false)
      inputRef.current?.focus()
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void sendMessage(input)
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-zinc-100 px-4 py-3 sm:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-zinc-900 text-white">
            <Sparkles className="size-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-zinc-900">AskAI</div>
            <div className="truncate text-xs text-zinc-500">Local LLM + SQL database</div>
          </div>
        </div>
        <div
          className={cn(
            'hidden rounded-full px-2.5 py-1 text-xs font-medium ring-1 sm:inline-flex',
            backendStatus === 'online' && 'bg-emerald-50 text-emerald-700 ring-emerald-200',
            backendStatus === 'offline' && 'bg-rose-50 text-rose-700 ring-rose-200',
            backendStatus === 'checking' && 'bg-zinc-50 text-zinc-600 ring-zinc-200',
          )}
        >
          {backendStatus === 'online' ? 'Backend online' : backendStatus === 'offline' ? 'Backend offline' : 'Checking...'}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-[linear-gradient(180deg,#fafafa_0%,#f4f4f5_100%)] px-3 py-4 sm:px-5">
        <div className="mx-auto flex max-w-3xl flex-col gap-3">
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}

          {isThinking ? <TypingBubble /> : null}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t border-zinc-100 bg-white px-3 py-3 sm:px-5">
        <div className="mx-auto max-w-3xl space-y-3">
          <div className="flex gap-2 overflow-x-auto pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => void sendMessage(s)}
                disabled={isThinking}
                className="shrink-0 rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs font-medium whitespace-nowrap text-zinc-700 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                {s}
              </button>
            ))}
          </div>

          <div className="flex items-end gap-2 rounded-2xl border border-zinc-200 bg-zinc-50 p-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              placeholder="Ask about orders, payments, refunds, UPI, cards..."
              className="max-h-32 min-h-[44px] flex-1 resize-none bg-transparent px-2 py-2 text-sm text-zinc-900 outline-none placeholder:text-zinc-400"
            />
            <button
              type="button"
              onClick={() => void sendMessage(input)}
              disabled={!canSend}
              className={cn(
                'grid size-10 shrink-0 place-items-center rounded-xl transition',
                canSend ? 'bg-zinc-900 text-white hover:bg-zinc-800' : 'bg-zinc-200 text-zinc-400',
              )}
              aria-label="Send message"
            >
              <Send className="size-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-2', isUser ? 'justify-end' : 'justify-start')}>
      {!isUser ? (
        <div className="mt-1 grid size-8 shrink-0 place-items-center rounded-lg bg-zinc-900 text-white">
          <Bot className="size-4" aria-hidden="true" />
        </div>
      ) : null}

      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm',
          isUser ? 'rounded-br-md bg-zinc-900 text-white' : 'rounded-bl-md border border-zinc-200 bg-white text-zinc-700',
        )}
      >
        <div className="whitespace-pre-wrap">{isUser ? message.content : renderMarkdownLite(message.content)}</div>
        <div className={cn('mt-1 text-[10px]', isUser ? 'text-zinc-300' : 'text-zinc-400')}>
          {new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit' }).format(new Date(message.createdAt))}
        </div>
      </div>
    </div>
  )
}

function TypingBubble() {
  return (
    <div className="flex justify-start gap-2">
      <div className="mt-1 grid size-8 shrink-0 place-items-center rounded-lg bg-zinc-900 text-white">
        <Bot className="size-4" aria-hidden="true" />
      </div>
      <div className="rounded-2xl rounded-bl-md border border-zinc-200 bg-white px-4 py-3 shadow-sm">
        <div className="flex items-center gap-1">
          <span className="size-1.5 animate-bounce rounded-full bg-zinc-400 [animation-delay:-0.2s]" />
          <span className="size-1.5 animate-bounce rounded-full bg-zinc-400 [animation-delay:-0.1s]" />
          <span className="size-1.5 animate-bounce rounded-full bg-zinc-400" />
        </div>
      </div>
    </div>
  )
}
