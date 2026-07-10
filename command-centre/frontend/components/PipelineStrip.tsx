"use client";

import type { EventsResponse, FusionOutput } from "@/lib/api";
import { inr } from "@/lib/format";

/** The thin link between three "separate" crimes, made visible: one criminal
 *  money pipeline. Scams TAKE the money, mule rings MOVE it, and the cash
 *  economy (where counterfeit circulates) is where it CASHES OUT. Arrows light
 *  up when fusion actually links the stages — the traced-payment chip appears
 *  when a victim's money was followed into a ring account. */
export default function PipelineStrip({
  events,
  fusion,
}: {
  events: EventsResponse | null;
  fusion: FusionOutput | null;
}) {
  const scamCount = events?.scams.filter((s) => s.verdict !== "legit").length ?? 0;
  const rings = events?.fraud_graph?.rings ?? [];
  const ringMoney = rings.reduce((a, r) => a + (r.total_amount ?? 0), 0);
  const fakeCount = events?.counterfeits.filter((c) => c.verdict === "fake").length ?? 0;

  const trails = fusion?.money_trails ?? [];
  const types = new Set((fusion?.linked_signals ?? []).map((l) => l.type));
  const takeMoveLinked = trails.length > 0 || (types.has("scam") && types.has("fraud_ring"));
  const moveCashLinked = types.has("counterfeit");

  return (
    <div className="pointer-events-none absolute left-[23rem] right-[26.5rem] top-44 z-10 hidden justify-center lg:flex">
      <div className="glass pointer-events-auto flex items-center gap-3 px-4 py-2.5">
        <Stage
          n="1"
          verb="TAKE"
          tone="text-red-300"
          line={`${scamCount} scam signal${scamCount === 1 ? "" : "s"}`}
        />
        <Arrow
          lit={takeMoveLinked}
          litClass="text-red-400"
          chip={trails[0] ? `₹${trails[0].amount.toLocaleString("en-IN")} traced` : undefined}
        />
        <Stage
          n="2"
          verb="MOVE"
          tone="text-violet-300"
          line={`${rings.length} ring${rings.length === 1 ? "" : "s"} · ${inr(ringMoney)}`}
        />
        <Arrow lit={moveCashLinked} litClass="text-amber-400" />
        <Stage
          n="3"
          verb="CASH OUT"
          tone="text-amber-300"
          line={`${fakeCount} fake note${fakeCount === 1 ? "" : "s"}`}
        />
        <span className="ml-2 hidden max-w-44 text-[9px] leading-snug text-zinc-600 xl:block">
          one criminal pipeline: scams take the money, mule rings move it, the cash economy
          absorbs it
        </span>
      </div>
    </div>
  );
}

function Stage({
  n,
  verb,
  tone,
  line,
}: {
  n: string;
  verb: string;
  tone: string;
  line: string;
}) {
  return (
    <div className="text-center">
      <div className={`text-[10px] font-bold uppercase tracking-widest ${tone}`}>
        {n} · {verb}
      </div>
      <div className="mt-0.5 text-[10px] text-zinc-400">{line}</div>
    </div>
  );
}

function Arrow({ lit, litClass, chip }: { lit: boolean; litClass: string; chip?: string }) {
  return (
    <div className="flex flex-col items-center">
      <span
        className={`text-sm leading-none ${lit ? `${litClass} animate-pulse` : "text-zinc-700"}`}
      >
        ⟶
      </span>
      {chip && lit && (
        <span className="mt-0.5 rounded-full bg-red-500/15 px-1.5 py-px text-[8px] font-semibold text-red-300">
          {chip}
        </span>
      )}
    </div>
  );
}
