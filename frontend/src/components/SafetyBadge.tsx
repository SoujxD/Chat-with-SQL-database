interface SafetyBadgeProps {
  isSafe: boolean;
}

export function SafetyBadge({ isSafe }: SafetyBadgeProps) {
  return (
    <span className={`badge ${isSafe ? "badge-safe" : "badge-danger"}`}>
      {isSafe ? "Safe" : "Blocked"}
    </span>
  );
}
