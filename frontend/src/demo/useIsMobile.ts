import { useEffect, useState } from "react";

/**
 * Below this the desktop layout stops being a layout.
 *
 * At 375px the 264px sidebar left 111px for the entire application, and the
 * monitor bezel — which is the right frame for a performance tool on a
 * desktop — eats a phone screen alive. So the breakpoint switches the shell
 * rather than shrinking it: the sidebar becomes a top bar, the bezel is
 * dropped, rows stack, and the detail drawer becomes a bottom sheet.
 */
export const MOBILE_BREAKPOINT = 760;

export default function useIsMobile(): boolean {
  const query = `(max-width: ${MOBILE_BREAKPOINT - 1}px)`;
  const [mobile, setMobile] = useState(
    () => typeof window !== "undefined" && window.matchMedia(query).matches,
  );

  useEffect(() => {
    const mql = window.matchMedia(query);
    // Both signals, deliberately. The media query is the correct one and fires
    // once per crossing rather than on every pixel, but it did not fire at all
    // under the viewport emulation used to test this — the query reported the
    // new value while the change event never arrived, leaving the phone layout
    // on a 1280px window. `resize` is noisier and always fires, and reading
    // `mql.matches` from it keeps the breakpoint in one place.
    const sync = () => setMobile(mql.matches);
    sync();
    mql.addEventListener("change", sync);
    window.addEventListener("resize", sync);
    return () => {
      mql.removeEventListener("change", sync);
      window.removeEventListener("resize", sync);
    };
  }, [query]);

  return mobile;
}
