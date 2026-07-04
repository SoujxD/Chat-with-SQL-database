import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { QueryErrorDetail, QueryResponse } from "../api/types";
import { useDatabase } from "../context/DatabaseContext";
import { QuestionBox } from "../components/QuestionBox";
import { SafetyBadge } from "../components/SafetyBadge";
import { SqlPanel } from "../components/SqlPanel";
import { ExplanationPanel } from "../components/ExplanationPanel";
import { ResultTable } from "../components/ResultTable";

export function QueryPage() {
  const { selectedId } = useDatabase();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [blocked, setBlocked] = useState<QueryErrorDetail | null>(null);
  const [genericError, setGenericError] = useState<string | null>(null);

  const handleAsk = async (question: string) => {
    setLoading(true);
    setResult(null);
    setBlocked(null);
    setGenericError(null);
    try {
      const res = await api.query(question, selectedId);
      setResult(res);
    } catch (err) {
      if (err instanceof ApiError && typeof err.detail !== "string") {
        setBlocked(err.detail);
      } else {
        setGenericError(err instanceof Error ? err.message : String(err));
      }
    } finally {
      setLoading(false);
    }
  };

  const display = result ?? blocked;

  return (
    <div className="page">
      <h1>Ask a question</h1>
      <div className="card">
        <QuestionBox onSubmit={handleAsk} loading={loading} />
      </div>

      {genericError && <div className="error-banner">{genericError}</div>}

      {display && (
        <div className="card stack">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <SafetyBadge isSafe={display.is_safe} />
            {"reason" in display && display.reason && (
              <span className="muted">{display.reason}</span>
            )}
          </div>
          {blocked && !result && <div className="error-banner">{blocked.message}</div>}
          <ExplanationPanel explanation={display.explanation} />
          <SqlPanel sql={display.generated_sql} />
          {result && <ResultTable rows={result.result} />}
        </div>
      )}
    </div>
  );
}
