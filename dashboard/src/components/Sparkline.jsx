import { useT } from "../context/ThemeContext";

export default function Sparkline({ values, lowerBetter = true, width = 80, height = 28 }) {
  const T = useT();
  if (!values || values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const lastY = parseFloat(pts.at(-1).split(",")[1]);
  const prevY = parseFloat(pts.at(-2).split(",")[1]);
  const improving = lowerBetter ? lastY > prevY : lastY < prevY;
  const color = improving ? T.good : T.textFaint;
  const [lx, ly] = pts.at(-1).split(",");
  return (
    <svg width={width} height={height} style={{ overflow: "visible", flexShrink: 0 }}>
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth="1.5"
        strokeLinecap="round" strokeLinejoin="round" opacity="0.7" />
      <circle cx={lx} cy={ly} r="2.5" fill={color} />
    </svg>
  );
}
