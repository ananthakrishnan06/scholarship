import { useEffect, useState } from "react";
import { api } from "./api";
import { Source } from "./components";
import type { Answer } from "./types";
type Message = {
  role: "user" | "assistant";
  question?: string;
  answer?: Answer;
};
type Session = { session_id: string; session_token: string };

export default function Assistant({ schemeId }: { schemeId?: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [session, setSession] = useState<Session | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    async function initialize() {
      try {
        const stored = sessionStorage.getItem("scholar-session");
        const saved: Session | null = stored ? JSON.parse(stored) : null;
        if (saved) {
          try {
            const data = await api<{
              context: {
                messages: {
                  role: "user" | "assistant";
                  content: Answer & { question?: string };
                }[];
              };
            }>("/sessions/" + saved.session_id, undefined, saved.session_token);
            if (active) {
              setSession(saved);
              setMessages(
                data.context.messages
                  .filter((m) => m.content.status !== "error")
                  .map((m) =>
                    m.role === "user"
                      ? { role: m.role, question: m.content.question }
                      : { role: m.role, answer: m.content },
                  ),
              );
            }
            return;
          } catch {
            sessionStorage.removeItem("scholar-session");
          }
        }
        const created = await api<Session>("/sessions", {});
        if (active) {
          sessionStorage.setItem("scholar-session", JSON.stringify(created));
          setSession(created);
        }
      } catch (err) {
        if (active)
          setError(
            err instanceof Error ? err.message : "Could not load conversation.",
          );
      }
    }
    void initialize();
    return () => {
      active = false;
    };
  }, []);
  async function send(event: React.FormEvent) {
    event.preventDefault();
    if (!question.trim() || !session) return;
    const text = question.trim();
    setQuestion("");
    setBusy(true);
    setError("");
    setMessages((m) => [...m, { role: "user", question: text }]);
    try {
      const answer = await api<Answer>(
        "/agent/query",
        {
          question: text,
          session_id: session.session_id,
          ...(schemeId ? { context_scheme_id: schemeId } : {}),
        },
        session.session_token,
      );
      if (answer.status === "error")
        throw new Error(answer.error?.message || answer.answer);
      setMessages((m) => [...m, { role: "assistant", answer }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Assistant unavailable.");
      setQuestion(text);
    } finally {
      setBusy(false);
    }
  }
  async function reset() {
    if (!session || busy) return;
    setBusy(true);
    setError("");
    try {
      await api<void>(
        "/sessions/" + session.session_id,
        undefined,
        session.session_token,
        "DELETE",
      );
      sessionStorage.removeItem("scholar-session");
      const created = await api<Session>("/sessions", {});
      sessionStorage.setItem("scholar-session", JSON.stringify(created));
      setSession(created);
      setMessages([]);
      setQuestion("");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not start a new conversation.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel chat">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">ANSWERS WITH EVIDENCE</span>
          <h2>Your scholarship guide</h2>
          <p>Ask anything about the scholarships in the dataset.</p>
        </div>
        <button
          className="button subtle"
          disabled={busy || !session}
          onClick={reset}
        >
          New conversation
        </button>
      </div>
      {!messages.length && (
        <div className="chat-empty">
          <div className="assistant-symbol">✦</div>
          <h3>Start with a question</h3>
          <p>
            Explore scholarship criteria, benefits, documents, and application
            procedures. No profile is needed.
          </p>
          <div className="suggestions">
            {[
              "What is the Pragati Scholarship?",
              "What scholarships are available for girl students?",
              "What documents are needed for the single girl child scholarship?",
            ].map((q) => (
              <button key={q} onClick={() => setQuestion(q)}>
                {q} ↗
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="messages" aria-live="polite">
        {messages.map((m, i) => (
          <article className={"message " + m.role} key={i}>
            <span className="eyebrow">
              {m.role === "user" ? "YOU" : "SCHOLARSHIP GUIDE"}
            </span>
            {m.question ? (
              <p>{m.question}</p>
            ) : (
              m.answer && (
                <>
                  <p className="answer-text">{m.answer.answer}</p>
                  {!!m.answer.sources.length && (
                    <details>
                      <summary>
                        Sources (
                        {new Set(m.answer.sources.map((s) => s.scheme_id)).size}
                        )
                      </summary>
                      {m.answer.sources
                        .filter(
                          (s, j, all) =>
                            all.findIndex(
                              (other) => other.scheme_id === s.scheme_id,
                            ) === j,
                        )
                        .map((citation) => (
                          <Source
                            citation={citation}
                            key={citation.scheme_id}
                          />
                        ))}
                    </details>
                  )}
                </>
              )
            )}
          </article>
        ))}
      </div>
      {busy && (
        <p className="loading" role="status">
          Finding scholarship information and preparing your answer…
        </p>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <form className="chat-input" onSubmit={send}>
        <label className="sr-only" htmlFor="chat-question">
          Ask a scholarship question
        </label>
        <input
          id="chat-question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a scholarship question…"
          maxLength={2000}
        />
        <button
          className="button primary"
          disabled={busy || !session || !question.trim()}
        >
          Send ↗
        </button>
      </form>
      <small className="chat-footnote">
        Answers use the available scholarship information. Verify current
        requirements with the scholarship authority.
      </small>
    </section>
  );
}
