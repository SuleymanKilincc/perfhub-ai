import { useEffect } from "react";
import type { Lang } from "./i18n";

/**
 * The chosen build, encoded in the address bar.
 *
 * A result that cannot be linked to is a result that has to be described. This
 * makes "here is what your machine does with these games" a URL you can send,
 * and for a portfolio it means a specific, impressive example is one link away
 * rather than five clicks in.
 *
 * Hardware is stored by name rather than by an index into the catalogue, so a
 * link stays valid when a part is added or the list is re-sorted. Names are
 * long, but the whole thing is still shorter than a typical tracking URL and
 * it survives the catalogue changing under it, which an index would not.
 */
export type UrlState = {
  cpu?: string;
  gpu?: string;
  ram?: number;
  res?: string;
  preset?: string;
  lang?: Lang;
  game?: number;
};

export function readUrl(): UrlState {
  if (typeof window === "undefined") return {};
  const q = new URLSearchParams(window.location.search);
  const num = (k: string) => {
    const v = q.get(k);
    if (v === null) return undefined;
    const n = Number(v);
    return Number.isFinite(n) ? n : undefined;
  };
  const lang = q.get("lang");
  return {
    cpu: q.get("cpu") ?? undefined,
    gpu: q.get("gpu") ?? undefined,
    ram: num("ram"),
    res: q.get("res") ?? undefined,
    preset: q.get("preset") ?? undefined,
    lang: lang === "en" || lang === "tr" ? lang : undefined,
    game: num("game"),
  };
}

/**
 * Keeps the address in step with the state, without adding a history entry per
 * keystroke — `replaceState` means the back button still leaves the site
 * rather than walking backwards through every preset the user tried.
 */
export function useUrlState(state: UrlState) {
  useEffect(() => {
    const q = new URLSearchParams();
    if (state.cpu) q.set("cpu", state.cpu);
    if (state.gpu) q.set("gpu", state.gpu);
    if (state.ram) q.set("ram", String(state.ram));
    if (state.res) q.set("res", state.res);
    if (state.preset) q.set("preset", state.preset);
    if (state.lang && state.lang !== "tr") q.set("lang", state.lang);
    if (state.game) q.set("game", String(state.game));

    const search = q.toString();
    const next = window.location.pathname + (search ? `?${search}` : "");
    if (next !== window.location.pathname + window.location.search) {
      window.history.replaceState(null, "", next);
    }
  }, [state.cpu, state.gpu, state.ram, state.res, state.preset, state.lang, state.game]);
}
