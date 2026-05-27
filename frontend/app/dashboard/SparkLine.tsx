'use client';

interface Props {
  values: number[];
  width?: number;
  height?: number;
  color?: string;
  fillOpacity?: number;
}

export default function SparkLine({
  values,
  width = 200,
  height = 36,
  color = '#4A7C59',
  fillOpacity = 0.15,
}: Props) {
  if (!values || values.length < 2) {
    return (
      <svg width={width} height={height} role="img" aria-label="sem dados">
        <line
          x1={0}
          y1={height / 2}
          x2={width}
          y2={height / 2}
          stroke="#DEE8DE"
          strokeWidth={1.5}
          strokeDasharray="3 3"
        />
      </svg>
    );
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  const area = `0,${height} ${points} ${width},${height}`;

  return (
    <svg width={width} height={height} role="img" aria-label="sparkline">
      <polygon points={area} fill={color} fillOpacity={fillOpacity} />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={1.8}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
