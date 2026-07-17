"use client";

import { useEffect, useRef, useState } from "react";
import { gsap, useGSAP } from "@/lib/gsap";
import {
  API_BASE,
  INSTITUTION_DEMO_KEY,
  screenAccount,
  type AccountScreening,
} from "@/lib/api";

/** Bank Partner — the financial-institution (B2B) surface, made visible.
 *  A bank's AML system calls /institution/screen-account behind an API key;
 *  this panel is a live console for that call plus the surface's documentation.
 *  It reuses the Fraud Graph model with zero new detection logic — the point is
 *  the *stakeholder framing*, which the challenge statement names explicitly. */

const BAND_STYLE: Record<string, string> = {
  high: "border-red-500/40 bg-red-500/10 text-red-300",
  medium: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  low: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
};

const DECISION_LABEL: Record<string, string> = {
  block: "BLOCK + file STR",
  review: "Enhanced Due Diligence",
  monitor: "Monitor",
  clear: "Clear — standard KYC",
};

export default function BankPartnerPanel({ onClose }: { onClose: () => void }) {
  const [accountId, setAccountId] = useState("");
  const [result, setResult] = useState<AccountScreening | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [examples, setExamples] = useState<string[]>([]);
  const container = useRef<HTMLDivElement>(null);

  // Pull a few real account ids from the live graph so the demo is not hardcoded.
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/events`);
        if (!r.ok) return;
        const data = await r.json();
        const accts: string[] = (data.fraud_graph?.accounts ?? [])
          .slice(0, 6)
          .map((a: { account_id: string }) => a.account_id);
        setExamples(accts);
      } catch {
        /* examples are a convenience; ignore fetch failure */
      }
    })();
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useGSAP(
    () => {
      gsap.fromTo(
        ".gsap-bank",
        { opacity: 0, y: 12, scale: 0.98 },
        { opacity: 1, y: 0, scale: 1, duration: 0.4, stagger: 0.06, ease: "power3.out", clearProps: "all" },
      );
    },
    { scope: container },
  );

  const run = async (id?: string) => {
    const q = (id ?? accountId).trim();
    if (!q) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await screenAccount(q));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setResult(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div ref={container} className="relative h-full overflow-y-auto bg-zinc-950/95 p-6 scroll-thin">
      <button
        onClick={onClose}
        aria-label="Close Bank Partner"
        className="absolute right-4 top-4 z-10 border border-white/10 bg-zinc-900/80 p-2 text-zinc-400 transition hover:bg-white/10 hover:text-zinc-100"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>

      <div className="mb-5 pr-12 gsap-bank">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-zinc-100">Bank Partner · AML Surface</h2>
          <span className="border border-sky-500/40 bg-sky-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-sky-300">
            B2B · API-key gated
          </span>
        </div>
        <p className="mt-1 max-w-3xl text-xs leading-relaxed text-zinc-500">
          The third stakeholder the challenge names. A bank&apos;s compliance system calls these endpoints
          machine-to-machine — the same Counterfeit Vision and Fraud Graph models, no citizen UI, behind an{" "}
          <code className="bg-white/5 px-1 text-zinc-300">X-API-Key</code> header. This console is a live
          client for <code className="bg-white/5 px-1 text-zinc-300">/institution/screen-account</code>.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Screening console */}
        <div className="gsap-bank border border-white/10 bg-zinc-900/60 p-5">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
            Screen an account
          </div>
          <div className="mt-3 flex gap-2">
            <input
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && run()}
              placeholder="account id, e.g. acc_02000"
              className="min-w-0 flex-1 border border-white/10 bg-zinc-950/70 px-3 py-2 text-[12px] text-zinc-200 outline-none transition focus:border-sky-400/60"
            />
            <button
              onClick={() => run()}
              disabled={busy || !accountId.trim()}
              className="border border-sky-500/40 bg-sky-500/15 px-3 py-2 text-[11px] font-semibold text-sky-200 transition hover:bg-sky-500/25 disabled:opacity-50"
            >
              {busy ? "Screening…" : "Screen"}
            </button>
          </div>

          {examples.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] text-zinc-600">try:</span>
              {examples.map((id) => (
                <button
                  key={id}
                  onClick={() => {
                    setAccountId(id);
                    run(id);
                  }}
                  className="bg-white/5 px-1.5 py-0.5 font-mono text-[10px] text-zinc-400 transition hover:text-sky-300"
                >
                  {id}
                </button>
              ))}
            </div>
          )}

          {error && <p className="mt-3 text-[11px] text-red-300">{error}</p>}

          {result && (
            <div className="mt-4 border-t border-white/5 pt-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm text-zinc-100">{result.account_id}</span>
                <span className={`border px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest ${BAND_STYLE[result.risk_band]}`}>
                  {result.risk_band} risk
                </span>
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-3xl font-light text-zinc-100">
                  {Math.round(result.risk_score * 100)}%
                </span>
                <span className="text-[10px] text-zinc-500">illicit probability</span>
              </div>
              <div className="mt-3 border border-white/10 bg-white/5 p-3">
                <div className="text-[10px] font-semibold uppercase tracking-wide text-sky-300">
                  Decision · {DECISION_LABEL[result.decision]}
                </div>
                <p className="mt-1 text-[11px] leading-relaxed text-zinc-300">{result.recommendation}</p>
              </div>
              {result.ring && (
                <div className="mt-2 flex flex-wrap gap-1 text-[10px] text-zinc-500">
                  <span className="bg-white/5 px-1.5 py-0.5">ring {result.ring.ring_id}</span>
                  {result.ring.size != null && <span className="bg-white/5 px-1.5 py-0.5">{result.ring.size} accounts</span>}
                  {result.ring.district && <span className="bg-white/5 px-1.5 py-0.5">{result.ring.district}</span>}
                </div>
              )}
              <p className="mt-3 text-[9px] leading-relaxed text-zinc-600">{result.disclaimer}</p>
            </div>
          )}
        </div>

        {/* Endpoint documentation */}
        <div className="gsap-bank border border-white/10 bg-zinc-900/60 p-5">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
            B2B endpoints
          </div>
          <div className="mt-3 space-y-3">
            <Endpoint
              method="POST"
              path="/institution/screen-account"
              desc="AML risk for one account → band + decision (block / EDD / monitor / clear). Reuses the Fraud Graph."
              body={`{ "account_id": "acc_02000" }`}
            />
            <Endpoint
              method="POST"
              path="/institution/verify-note"
              desc="Teller / counting-machine note check → pass/fail + confidence + action. Reuses Counterfeit Vision."
              body={`{ "image_b64": "<note image>" }`}
            />
            <Endpoint
              method="GET"
              path="/institution/health"
              desc="Authenticated key + connectivity check."
            />
          </div>
          <div className="mt-4 border border-sky-500/20 bg-sky-500/5 p-3">
            <div className="text-[10px] font-semibold uppercase tracking-wide text-sky-300">Auth</div>
            <p className="mt-1 text-[11px] leading-relaxed text-zinc-400">
              Every call requires <code className="bg-white/5 px-1 text-zinc-300">X-API-Key</code>. This console
              uses the public demo key{" "}
              <code className="bg-white/5 px-1 font-mono text-zinc-300">{INSTITUTION_DEMO_KEY}</code>. A real
              deployment would issue per-partner keys over mTLS.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Endpoint({
  method,
  path,
  desc,
  body,
}: {
  method: string;
  path: string;
  desc: string;
  body?: string;
}) {
  return (
    <div className="border border-white/10 bg-white/5 p-3">
      <div className="flex items-center gap-2">
        <span
          className={`px-1.5 py-0.5 text-[9px] font-bold ${
            method === "POST" ? "bg-emerald-500/15 text-emerald-300" : "bg-sky-500/15 text-sky-300"
          }`}
        >
          {method}
        </span>
        <span className="font-mono text-[11px] text-zinc-200">{path}</span>
      </div>
      <p className="mt-1.5 text-[10px] leading-relaxed text-zinc-500">{desc}</p>
      {body && <div className="mt-1.5 bg-black/30 px-2 py-1 font-mono text-[10px] text-zinc-400">{body}</div>}
    </div>
  );
}
