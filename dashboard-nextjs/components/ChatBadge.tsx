'use client'

import { useState, useRef, useEffect } from 'react'
import { sendChatMessage } from '@/lib/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function ChatBadge() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (open && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [open, messages])

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setSending(true)
    setError(null)
    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }))
      const data = await sendChatMessage(text, history)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.message || 'Geen antwoord' },
      ])
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Kon niet verzenden')
      setMessages((prev) => prev.slice(0, -1))
    } finally {
      setSending(false)
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-blue-600 hover:bg-blue-700 flex items-center justify-center shadow-lg transition-colors z-40"
        title="Chat met Neuroion"
        aria-label="Open chat"
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-end p-4 pb-20 sm:p-6 sm:pb-24">
          <div className="bg-[#111] border border-[var(--border)] rounded-2xl shadow-2xl flex flex-col w-full max-w-md h-[70vh] max-h-[500px] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-[var(--border)]">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm font-semibold">
                  N
                </div>
                <span className="font-medium">Neuroion</span>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="p-2 text-muted hover:text-white rounded-lg transition-colors"
                aria-label="Sluiten"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 && (
                <p className="text-muted text-sm text-center py-8">
                  Stel een vraag of start een gesprek.
                </p>
              )}
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-2 ${
                      m.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-[#222] border border-[var(--border)]'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                  </div>
                </div>
              ))}
              {error && (
                <p className="text-sm text-red-400 text-center">{error}</p>
              )}
              <div ref={bottomRef} />
            </div>

            <form onSubmit={handleSend} className="p-4 border-t border-[var(--border)]">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Bericht..."
                  className="flex-1 px-4 py-3 bg-[#0a0a0a] border border-[var(--border)] rounded-xl focus:outline-none focus:border-blue-500"
                  disabled={sending}
                />
                <button
                  type="submit"
                  disabled={sending || !input.trim()}
                  className="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl font-medium transition-colors"
                >
                  {sending ? '...' : 'Verstuur'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
