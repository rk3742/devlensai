import { useEffect, useState, useRef } from "react";
import { useOutletContext } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { api } from "../lib/api";
import { Card, Spinner, ErrorBanner, EmptyState } from "../components/ui";

const SUGGESTED_QUESTIONS = [
  "How does authentication work in this project?",
  "Where is the database connected?",
  "What's the entry point of this application?",
  "How is routing handled?",
];

export default function ChatPage() {
  const { repoId } = useOutletContext();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    api.getChatHistory(repoId).then(setMessages).catch(() => {});
  }, [repoId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendQuestion(question) {
    if (!question.trim() || loading) return;
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: question, sources: [] }]);
    setInput("");
    setLoading(true);
    try {
      const result = await api.askQuestion(repoId, question);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.answer, sources: result.sources || [] },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-8 py-6">
        {messages.length === 0 && (
          <div className="max-w-2xl mx-auto">
            <EmptyState
              title="Ask anything about this codebase"
              description="DevLens AI has indexed every file and can answer questions like a senior developer who's already studied it."
            />
            <div className="grid grid-cols-2 gap-2">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => sendQuestion(q)}
                  className="text-left text-sm text-ink-dim bg-base-900 border border-base-700 rounded-lg px-4 py-3 hover:border-accent/40 hover:text-ink transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="max-w-2xl mx-auto space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={msg.role === "user" ? "flex justify-end" : ""}>
              {msg.role === "user" ? (
                <div className="bg-accent/10 text-ink rounded-xl px-4 py-2.5 max-w-md text-sm">
                  {msg.content}
                </div>
              ) : (
                <Card className="p-4 max-w-xl">
                  <div className="markdown-body text-sm">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                  {msg.sources?.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-base-700 flex flex-wrap gap-1.5">
                      {msg.sources.map((s, si) => (
                        <span
                          key={si}
                          className="text-xs font-mono text-accent bg-accent/5 px-2 py-0.5 rounded border border-accent/20"
                          title={s.snippet}
                        >
                          {s.file_path}
                        </span>
                      ))}
                    </div>
                  )}
                </Card>
              )}
            </div>
          ))}

          {loading && (
            <Card className="p-4 max-w-xl flex items-center gap-2 text-ink-dim text-sm">
              <Spinner /> Searching the codebase…
            </Card>
          )}

          {error && <ErrorBanner message={error} />}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t border-base-700 p-4">
        <form
          onSubmit={(e) => { e.preventDefault(); sendQuestion(input); }}
          className="max-w-2xl mx-auto flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about this codebase…"
            disabled={loading}
            className="flex-1 bg-base-900 border border-base-700 rounded-lg px-4 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 rounded-lg bg-accent text-base-950 font-semibold text-sm disabled:opacity-40 hover:bg-accent-dim transition-colors"
          >
            Ask
          </button>
        </form>
      </div>
    </div>
  );
}
