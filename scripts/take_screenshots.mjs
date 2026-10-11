// Screenshots of the running web app through the Chrome DevTools protocol.
//
//   node scripts/take_screenshots.mjs <outDir> name.png=<url> [name.png=<url> ...]
//
// The README's screenshots are made with this, from a dev server on port 3000:
//
//   B=http://localhost:3000/
//   Q="cpu=AMD+Ryzen+5+7600&gpu=NVIDIA+GeForce+RTX+4070&ram=32&res=1440p&preset=High&lang=en"
//   node scripts/take_screenshots.mjs screenshots \
//     "build.png=$B?lang=en" "results.png=$B?$Q" "detail.png=$B?$Q&game=1"
//
// (game=1 is Cyberpunk 2077.) It waits in real time, because the interface's
// entry animation runs on requestAnimationFrame and a headless "virtual time"
// run never lets it finish. The first load after starting the dev server can
// be slower than the wait and yield a blank page; run it twice if one is white.
//
// No dependencies: Node 22+ ships fetch and WebSocket. Set CHROME to the
// browser's path if it is not in the default Windows location.
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = process.env.CHROME ?? "C:/Program Files/Google/Chrome/Application/chrome.exe";
const [, , outDir, ...pairs] = process.argv; // name=url name=url ...
if (!outDir || pairs.length === 0) {
  console.error("usage: node scripts/take_screenshots.mjs <outDir> name.png=<url> ...");
  process.exit(2);
}
const PORT = 9333;
const profile = mkdtempSync(join(tmpdir(), "shot-"));
const proc = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  "--hide-scrollbars", "--window-size=1600,1000", "about:blank",
], { stdio: "ignore" });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws;
for (let i = 0; i < 40 && !ws; i++) {
  try {
    const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
    const page = list.find((t) => t.type === "page");
    if (page) ws = new WebSocket(page.webSocketDebuggerUrl);
  } catch { await sleep(250); }
}
if (!ws) { console.error("could not reach Chrome"); proc.kill(); process.exit(1); }
await new Promise((r) => ws.addEventListener("open", r, { once: true }));

let id = 0;
const pending = new Map();
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
});
const send = (method, params = {}) => new Promise((r) => {
  const n = ++id; pending.set(n, r); ws.send(JSON.stringify({ id: n, method, params }));
});

await send("Emulation.setDeviceMetricsOverride",
  { width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false });
for (const pair of pairs) {
  const i = pair.indexOf("=");
  const name = pair.slice(0, i), url = pair.slice(i + 1);
  await send("Page.navigate", { url });
  await sleep(5000);
  const shot = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(outDir, name), Buffer.from(shot.result.data, "base64"));
  console.log("  wrote", join(outDir, name));
}
ws.close();
proc.kill();
