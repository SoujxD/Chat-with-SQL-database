interface ExplanationPanelProps {
  explanation: string;
}

export function ExplanationPanel({ explanation }: ExplanationPanelProps) {
  if (!explanation) return null;
  return (
    <div className="stack" style={{ gap: 6 }}>
      <h3 style={{ margin: 0 }}>Explanation</h3>
      <p>{explanation}</p>
    </div>
  );
}
