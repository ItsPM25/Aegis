/** Types mirror contracts/*.schema.json — the team's locked data contract. */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:4000";

export interface LocationHint {
  district?: string;
  lat?: number;
  lon?: number;
}

export interface ScamEvent {
  event_id: string;
  source: string;
  timestamp: string;
  raw_text: string;
  verdict: "scam" | "suspicious" | "legit";
  risk_score: number;
  scam_type?: string;
  markers?: string[];
  explanation?: string;
  phone_number?: string;
  location_hint?: LocationHint;
}

export interface CounterfeitEvent {
  event_id: string;
  timestamp: string;
  denomination: string;
  verdict: "fake" | "genuine" | "uncertain";
  confidence: number;
  missing_features?: string[];
  image_ref?: string;
  location_hint?: LocationHint;
}

export interface Ring {
  ring_id: string;
  account_ids: string[];
  risk_score: number;
  size: number;
  total_amount: number;
  label?: string;
  district?: string;
}

export interface FraudGraph {
  generated_at?: string;
  model?: string;
  rings: Ring[];
  accounts?: { account_id: string; illicit_probability: number; ring_id: string | null }[];
  edges?: { source: string; target: string; amount: number; timestamp?: string }[];
}

export interface FusionOutput {
  generated_at?: string;
  summary: string;
  threat_level: string;
  linked_signals: { type: string; ref_event_id: string; reason: string }[];
  correlation_basis: string[];
  recommended_actions: string[];
  map_hotspots: MapPoint[];
  audit_trail?: { model: string; inputs_hash: string; prompt_version: string };
}

export interface MapPoint {
  type: string;
  district?: string;
  lat: number;
  lon: number;
  weight?: number;
}

export interface Hub {
  hub_id: string;
  lat: number;
  lon: number;
  domains: string[];
  cross_domain: boolean;
  intensity: number;
  district: string | null;
  n_points: number;
  points: MapPoint[];
}

export interface EventsResponse {
  scams: ScamEvent[];
  counterfeits: CounterfeitEvent[];
  fraud_graph: FraudGraph | null;
  last_fusion: FusionOutput | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  version?: string;
  modules: Record<string, string>;
}

export interface HotspotsResponse {
  hubs: Hub[];
  n_cross_domain: number;
  points: MapPoint[];
}

export async function runFusion(): Promise<FusionOutput> {
  const r = await fetch(`${API_BASE}/api/fuse`, { method: "POST" });
  if (!r.ok) throw new Error(`fusion failed: ${r.status}`);
  return r.json();
}

/** Live wow moment #1: analyse a scam message/transcript; auto-ingested for the map + fusion. */
export async function analyzeScam(
  text: string,
  source = "manual_demo",
  location_hint?: LocationHint
): Promise<ScamEvent> {
  const r = await fetch(`${API_BASE}/api/analyze/scam`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text, source, location_hint }),
  });
  if (!r.ok) throw new Error(`scam analysis failed: ${r.status}`);
  return r.json();
}

/** Live wow moment #2: analyse a note photo (data URL / base64); auto-ingested. */
export async function analyzeCounterfeit(
  image_b64: string,
  location_hint?: LocationHint
): Promise<CounterfeitEvent> {
  const r = await fetch(`${API_BASE}/api/analyze/counterfeit`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ image_b64, location_hint }),
  });
  if (!r.ok) throw new Error(`note analysis failed: ${r.status}`);
  return r.json();
}
