import { useState } from "react";
import type { FormEvent } from "react";

interface QuestionBoxProps {
  onSubmit: (question: string) => void;
  loading: boolean;
  placeholder?: string;
}

export function QuestionBox({ onSubmit, loading, placeholder }: QuestionBoxProps) {
  const [question, setQuestion] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = question.trim();
    if (trimmed && !loading) onSubmit(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form className="stack" style={{ gap: 10 }} onSubmit={handleSubmit}>
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder ?? "Ask a question about your data, e.g. \"top 5 products by revenue\""}
        disabled={loading}
      />
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn" type="submit" disabled={loading || !question.trim()}>
          {loading ? <span className="spinner" /> : "Ask"}
        </button>
      </div>
    </form>
  );
}
