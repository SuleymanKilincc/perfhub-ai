import { useEffect, useMemo, useRef, useState } from "react";
import { normalise } from "./lib";

export type PickerItem = { value: string; label: string; meta?: string };

/**
 * A searchable picker for the hardware lists.
 *
 * A native <select> with 220 CPUs in it is technically a control and
 * practically a wall — finding a Ryzen 5 5600 means scrolling past every
 * Threadripper. Typing "5600" should be enough, so it is.
 *
 * Matching is on normalised text, which folds Turkish letters, so "ı" finds
 * "i" and a keyboard layout does not decide whether the search works.
 */
export default function Picker({ items, value, onChange, placeholder, emptyLabel }: {
  items: PickerItem[];
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  emptyLabel: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const box = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);

  const selected = items.find((i) => i.value === value) ?? null;

  const filtered = useMemo(() => {
    const q = normalise(query);
    if (!q) return items;
    const terms = q.split(" ");
    return items.filter((i) => {
      const hay = normalise(i.label + " " + (i.meta ?? ""));
      return terms.every((t) => hay.includes(t));
    });
  }, [items, query]);

  useEffect(() => setActive(0), [query]);

  useEffect(() => {
    if (!open) return;
    input.current?.focus();
    const away = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open]);

  const choose = (v: string) => {
    onChange(v);
    setOpen(false);
    setQuery("");
  };

  return (
    <div ref={box} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: "100%", textAlign: "left", display: "flex", alignItems: "center",
          gap: 10, background: "var(--surface)",
          border: `1px solid ${open ? "var(--amber)" : "var(--border)"}`,
          borderRadius: 10, padding: "14px 16px", fontSize: 16,
          color: selected ? "var(--text)" : "var(--text-3)",
        }}
      >
        <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {selected ? selected.label : emptyLabel}
        </span>
        {selected?.meta && (
          <span style={{ fontFamily: "var(--mono)", fontSize: 13, color: "var(--text-3)" }}>
            {selected.meta}
          </span>
        )}
        <span style={{ color: "var(--text-3)", fontSize: 12 }}>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 6px)", left: 0, right: 0, zIndex: 30,
          background: "var(--raised)", border: "1px solid var(--border-strong)",
          borderRadius: 10, overflow: "hidden",
          boxShadow: "0 24px 48px -12px rgba(0,0,0,0.8)",
        }}>
          <input
            ref={input}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, filtered.length - 1)); }
              else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
              else if (e.key === "Enter" && filtered[active]) { e.preventDefault(); choose(filtered[active].value); }
              else if (e.key === "Escape") setOpen(false);
            }}
            placeholder={placeholder}
            style={{
              width: "100%", background: "var(--surface)", border: "none",
              borderBottom: "1px solid var(--border)", padding: "13px 16px",
              fontSize: 15, outline: "none",
            }}
          />
          <div style={{ maxHeight: 320, overflowY: "auto" }}>
            {filtered.length === 0 ? (
              <div style={{ padding: "18px 16px", color: "var(--text-3)", fontSize: 14 }}>
                Eşleşme yok
              </div>
            ) : (
              filtered.map((i, n) => (
                <button
                  key={i.value}
                  onMouseEnter={() => setActive(n)}
                  onClick={() => choose(i.value)}
                  style={{
                    display: "flex", width: "100%", textAlign: "left", gap: 10,
                    alignItems: "center", padding: "11px 16px", border: "none",
                    background: n === active ? "var(--surface)" : "transparent",
                    color: i.value === value ? "var(--amber)" : "var(--text)",
                    fontSize: 15,
                  }}
                >
                  <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {i.label}
                  </span>
                  {i.meta && (
                    <span style={{ fontFamily: "var(--mono)", fontSize: 13, color: "var(--text-3)" }}>
                      {i.meta}
                    </span>
                  )}
                </button>
              ))
            )}
          </div>
          <div style={{
            padding: "9px 16px", borderTop: "1px solid var(--border)",
            fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)",
          }}>
            {filtered.length} / {items.length}
          </div>
        </div>
      )}
    </div>
  );
}
