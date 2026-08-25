import { useEffect, useRef, useState } from "react";

/**
 * The entry gauge.
 *
 * There is nothing to load — the engine and the catalogue ship with the page
 * and the app is ready on first paint. So this is a *transition*, not a
 * progress bar, and it is capped at DURATION rather than waiting on anything.
 * A fake stall would spend the very thing that moving the engine into the
 * browser just bought back.
 *
 * Drawn in SVG, not WebGL. The reference for this look was a raymarched
 * fragment shader with a refractive glass cube; the parts that actually carry
 * the aesthetic — dark grid, ticked arc, amber, monospace digits — cost
 * nothing, and the expensive part would have made a fast page slow to enter.
 */
const DURATION = 750;
const TICKS = 44;
const RADIUS = 132;

export default function Loader({ onDone }: { onDone: () => void }) {
  const [pct, setPct] = useState(0);
  const [leaving, setLeaving] = useState(false);
  const started = useRef<number | null>(null);

  useEffect(() => {
    let frame = 0;
    const step = (now: number) => {
      if (started.current === null) started.current = now;
      const t = Math.min(1, (now - started.current) / DURATION);
      // Ease out: the counter sprints and settles, which reads as a machine
      // finishing rather than a bar crawling.
      setPct(Math.round(100 * (1 - Math.pow(1 - t, 3))));
      if (t < 1) frame = requestAnimationFrame(step);
      else {
        setLeaving(true);
        setTimeout(onDone, 420);
      }
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [onDone]);

  const sweep = 240; // degrees of arc
  const start = 180 + (360 - sweep) / 2;

  const polar = (deg: number, r: number) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return [200 + r * Math.cos(rad), 200 + r * Math.sin(rad)] as const;
  };

  const lit = Math.round((pct / 100) * TICKS);

  return (
    <div
      className="grid-bg"
      style={{
        position: "fixed",
        inset: 0,
        background: "var(--bg)",
        display: "grid",
        placeItems: "center",
        zIndex: 50,
        opacity: leaving ? 0 : 1,
        transform: leaving ? "scale(1.35)" : "scale(1)",
        transition: `opacity 400ms var(--ease), transform 400ms var(--ease)`,
      }}
    >
      <div style={{ textAlign: "center" }}>
        <svg width="400" height="300" viewBox="0 0 400 300" aria-hidden>
          {/* Ticks. Each one lights as the counter passes it, so the arc
              fills in discrete steps like an instrument rather than sliding. */}
          {Array.from({ length: TICKS }, (_, i) => {
            const deg = start + (sweep * i) / (TICKS - 1);
            const major = i % 5 === 0;
            const [x1, y1] = polar(deg, RADIUS - (major ? 16 : 9));
            const [x2, y2] = polar(deg, RADIUS);
            const on = i < lit;
            return (
              <line
                key={i}
                x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={on ? "var(--amber)" : "var(--border)"}
                strokeWidth={major ? 2 : 1}
                opacity={on ? 1 : 0.7}
              />
            );
          })}

          {/* Inner arc: continuous, to give the ticks something to sit against. */}
          <path
            d={describeArc(start, start + sweep, RADIUS - 30)}
            fill="none"
            stroke="var(--border)"
            strokeWidth="1"
          />
          <path
            d={describeArc(start, start + (sweep * pct) / 100, RADIUS - 30)}
            fill="none"
            stroke="var(--amber)"
            strokeWidth="2"
            style={{ filter: "drop-shadow(0 0 6px var(--amber-glow))" }}
          />

          <text
            x="200" y="205"
            textAnchor="middle"
            style={{
              fill: "var(--text)",
              fontFamily: "var(--mono)",
              fontSize: 64,
              fontWeight: 600,
              letterSpacing: "-0.03em",
            }}
          >
            {String(pct).padStart(3, "0")}
          </text>
          <text
            x="200" y="234"
            textAnchor="middle"
            style={{
              fill: "var(--text-3)",
              fontFamily: "var(--mono)",
              fontSize: 12,
              letterSpacing: "0.35em",
            }}
          >
            PERFHUB
          </text>
        </svg>
      </div>
    </div>
  );

  function describeArc(a: number, b: number, r: number) {
    if (b - a < 0.01) return "";
    const [sx, sy] = polar(a, r);
    const [ex, ey] = polar(b, r);
    const large = b - a > 180 ? 1 : 0;
    return `M ${sx} ${sy} A ${r} ${r} 0 ${large} 1 ${ex} ${ey}`;
  }
}
