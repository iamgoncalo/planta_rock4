"use client";

export const STATUS_COLORS: Record<string, string> = {
  online:   "#6FAF82",
  degraded: "#D48B3A",
  offline:  "#6B7280",
  unknown:  "#6B7280",
  critical: "#C25A1A",
};

export const STATUS_LABELS: Record<string, string> = {
  online:   "Online",
  degraded: "Degradado",
  offline:  "Offline",
  unknown:  "Desconhecido",
  critical: "Crítico",
};

interface StatusDotProps {
  status: string;
  size?: number;
  showLabel?: boolean;
}

export function StatusDot({ status, size = 10, showLabel = false }: StatusDotProps) {
  const color = STATUS_COLORS[status] ?? STATUS_COLORS.unknown;
  const label = STATUS_LABELS[status] ?? status;

  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span
        style={{
          display: "inline-block",
          width: size,
          height: size,
          borderRadius: "50%",
          backgroundColor: color,
          flexShrink: 0,
          boxShadow: status === "online" ? `0 0 6px ${color}80` : undefined,
        }}
        title={label}
        aria-label={label}
      />
      {showLabel && (
        <span style={{ fontSize: 13, color, fontWeight: 500 }}>{label}</span>
      )}
    </span>
  );
}
