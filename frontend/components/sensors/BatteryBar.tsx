"use client";

interface BatteryBarProps {
  pct?: number | null;
  daysLeft?: number | null;
  height?: number;
  width?: number | string;
}

export function BatteryBar({ pct, daysLeft, height = 10, width = "100%" }: BatteryBarProps) {
  const value = pct ?? null;

  const getColor = (v: number): string => {
    if (v >= 60) return "#6FAF82";
    if (v >= 30) return "#D48B3A";
    return "#C25A1A";
  };

  if (value === null) {
    return (
      <span style={{ fontSize: 12, color: "#9CA3AF" }}>N/A</span>
    );
  }

  const clampedPct = Math.max(0, Math.min(100, value));
  const color = getColor(clampedPct);

  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8, width }}>
      <span
        style={{
          display: "inline-block",
          flex: 1,
          height,
          backgroundColor: "#E5E7EB",
          borderRadius: height / 2,
          overflow: "hidden",
          minWidth: 60,
        }}
      >
        <span
          style={{
            display: "block",
            height: "100%",
            width: `${clampedPct}%`,
            backgroundColor: color,
            borderRadius: height / 2,
            transition: "width 0.4s ease",
          }}
        />
      </span>
      <span style={{ fontSize: 12, color, fontWeight: 600, minWidth: 36 }}>
        {clampedPct}%
      </span>
      {daysLeft !== null && daysLeft !== undefined && (
        <span style={{ fontSize: 11, color: "#6B7280" }}>
          {daysLeft}d
        </span>
      )}
    </span>
  );
}
