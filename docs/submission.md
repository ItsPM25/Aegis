<div align="center">

<br><br><br>

# 🛡️ AEGIS AI

## Digital Public Safety Intelligence Platform

<br>

### Hackathon Submission Document

<br>

**ET AI Hackathon 2026 — Problem Statement #6**
*AI for Digital Public Safety: Defeating Counterfeiting, Fraud & Digital Arrest Scams*

**Theme:** Smart Cities · Public Safety · Digital Trust · Geospatial Law Enforcement

<br><br>

> **Three AI systems. One correlated picture. Every verdict carries its evidence.**

<br><br>

| | |
|---|---|
| **Team** | Aegis |
| **Members** | Sudarsan (Fraud Shield — NLP) · Adharshan (Counterfeit Vision — CV) · Prayag (Fraud Graph — Graph ML + Gen AI Fusion) · Pushkar (Command Centre) |
| **Repository** | github.com/sudarsan2507-hue/Aegis |
| **Date** | July 2026 |

<br><br><br>

</div>

---

## Executive Summary

India logged **1.14 million cybercrime complaints in 2023** (up 60% year-on-year). "Digital arrest" scams alone stole **₹1,776 crore in the first nine months of 2024**. The RBI's 2025 Annual Report flagged record seizures of fake ₹500 notes good enough to beat manual bank checks. Yet every one of these crimes is investigated **in isolation, after the complaint** — a scam call in one file, a fake note in another, a mule account in a third.

**Aegis is the intelligence layer that sees them together, before mass victimisation.**

We built a working, end-to-end **Digital Public Safety Intelligence Platform** with four cooperating systems:

1. **Fraud Shield** — a real-time scam / digital-arrest classifier (NLP) that flags a scam **mid-message and mid-call, before any money moves**, names the exact manipulation markers as evidence, answers in **22 Indian languages**, and reaches citizens over the **web, live-call monitoring, and WhatsApp**.
2. **Counterfeit Vision** — a camera-based fake-note detector (CNN + OpenCV) that names the **specific missing security feature**, backed by a pre-AI forensic triage layer, an **RBI serial-number validator with a national duplicate-sighting registry** (catches counterfeit *printing runs*), and a vision-LLM review — none of which can ever certify a note genuine, only make the system more cautious.
3. **Fraud Graph** — a graph-ML engine (18 topology features + XGBoost + Louvain communities) that clusters accounts into **mule rings in seconds**, recovered **12/12 planted rings** on evaluation, and scores **0.994 ROC-AUC on the real Elliptic++ Bitcoin fraud benchmark** — real-data validated, not toy-data-only.
4. **Command Centre** — a police/analyst dashboard with a cross-domain crime map, a **deterministic evidence correlator narrated (never decided) by Gen AI**, DBSCAN coordinated-hub detection, a Disrupt/Respond **action queue with SLAs and append-only audit logs**, API-key-gated **B2B endpoints for banks**, and a live **Model Card** that reads every metric from the models' own persisted reports.

The platform's thesis — backed by public I4C/RBI records — is that scam calls, mule rings, and counterfeit cash are **three stages of one criminal money pipeline** (TAKE → MOVE → CASH OUT). Aegis is, to our knowledge, the first system to detect all three stages and **join them with deterministic, court-auditable evidence**: shared district, ≤30 km, ≤96 h, and an exact money-trail match from a victim's reported payment into a detected ring's collector account.

Headline measured results (all from persisted, reproducible reports — nothing tuned for display):

- Scam classifier: **ROC-AUC 0.994**, scam-verdict **precision 0.98**, digital-arrest recall **100%**
- Self-improving loop: recall on **unseen, never-trained scam families 69% → 100%** with zero human labels
- Counterfeit: fake-note **precision 1.00** (synthetic baseline); **0.97/0.96 P/R** on the real-photo dataset
- Fraud rings: **12/12 rings recovered**, account precision **0.976** / recall **0.988**; **0.994 AUC on real data**
- Live demo latency: a never-before-seen ring injected by judges is **caught in ~3 seconds**

---

## Table of Contents

1. [Problem Statement & Motivation](#1-problem-statement--motivation)
2. [Proposed Solution](#2-proposed-solution)
3. [What We Did That Is New, Different, and First-Time](#3-what-we-did-that-is-new-different-and-first-time)
4. [Comparison With Existing Solutions](#4-comparison-with-existing-solutions)
5. [Metrics & Measured Results](#5-metrics--measured-results)
6. [System Architecture](#6-system-architecture)
7. [Module Deep-Dives](#7-module-deep-dives)
8. [Generative AI: Doctrine, Fusion & Resilience](#8-generative-ai-doctrine-fusion--resilience)
9. [Research Lab — Advanced Experiments, Honestly Reported](#9-research-lab--advanced-experiments-honestly-reported)
10. [Auditability, Legal Admissibility & Safety](#10-auditability-legal-admissibility--safety)
11. [Scalability & Deployment](#11-scalability--deployment)
12. [User Experience](#12-user-experience)
13. [Challenge Compliance Matrix](#13-challenge-compliance-matrix)
14. [Honest Limitations & Roadmap](#14-honest-limitations--roadmap)
15. [Results & Conclusion](#15-results--conclusion)
16. [Appendix: Team, Repository & How to Run](#16-appendix-team-repository--how-to-run)

---

## 1. Problem Statement & Motivation

### 1.1 The scale of the threat

- **1.14 million cybercrime complaints** were registered in India in 2023 — up 60% from 2022, and the trajectory has steepened since.
- **Digital-arrest scams** — fraudsters impersonating CBI, ED, or Customs officers who trap victims in multi-day psychological hostage situations over video calls — defrauded citizens of **over ₹1,776 crore in just the first nine months of 2024** (Ministry of Home Affairs).
- These are **industrialised operations**, run from fraud compounds, often across borders, using spoofed numbers, AI-generated voices, and fake government portals — not opportunistic crime.
- **Counterfeit currency** remains a persistent, parallel threat: the RBI's Annual Report 2025 flagged record FICN (Fake Indian Currency Note) seizures, with ₹500 fakes of sufficient quality to defeat manual detection in routine banking operations.
- The money side is equally industrial: **I4C has flagged over 2.47 million Layer-1 mule accounts**, against **₹17,000+ crore of reported cyber-fraud losses since 2023**.

### 1.2 The real gap

What law enforcement lacks is **not evidence after the fact — it is intelligence before mass victimisation**, and reliable tools at the **point of contact** rather than the point of complaint. Today:

- A scam call is (maybe) reported *after* the victim has paid.
- A fake note is discovered *after* it has circulated.
- A mule ring is unwound *months later* by manual investigation.
- **No system connects the three.** Police see three unrelated cases where there is actually one operation.

### 1.3 Why one platform is legitimate (the pipeline thesis)

Our research brief (`docs/crime-pipeline.md`, all claims backed by public reporting and government records) documents that these "three crimes" are **three stages of one criminal money pipeline**:

```
 ① TAKE                     ② MOVE                        ③ CASH OUT
 scam calls /            mule-account rings             the cash economy
 digital arrest    ──▶   (collection, layering,   ──▶   (where counterfeit
 phishing                 round-tripping)                notes circulate)
```

- Scam proceeds land **immediately in mule accounts** (RBI's own definition of mule accounts; I4C's 2.47M flagged accounts). The state's countermeasure — RBI's **MuleHunter.ai** and the May 2026 I4C–RBI Innovation Hub MoU — validates exactly this architecture.
- Laundered digital money **exits into cash**, and the criminal cash layer is precisely where FICN circulates — FICN distribution is itself a trafficked *network* (NIA runs a dedicated Terror Funding and Fake Currency Cell).
- The **same districts host multiple crime types** because the *enabling infrastructure* is shared — rented mule accounts, farmed SIMs, forged KYC, local agent networks (the Jamtara and Mewat belts are the documented examples). Infrastructure, not crime type, clusters geographically — which is why **two independent detections converging on one district is real evidence of an organised hub**, not a coincidence.

This is the multi-source, multi-agency intelligence problem the challenge describes — and the reason a fused platform is the *correct* shape of the answer, not a hackathon gimmick.

---

## 2. Proposed Solution

### 2.1 One sentence

**Aegis detects all three stages of the fraud pipeline in real time, correlates them with deterministic auditable evidence, and turns the result into concrete disrupt/respond actions — served to law enforcement, financial institutions, and citizens.**

### 2.2 Detect → Disrupt → Respond, for three stakeholders

The challenge names three stakeholders and three verbs. Aegis implements all nine cells:

| | 👮 Law enforcement | 🏦 Financial institutions | 🧑 Citizens |
|---|---|---|---|
| **Detect** | Dashboard cards, crime map, ring viewer, per-district case files | `POST /institution/screen-account` (AML risk), `POST /institution/verify-note` (teller/POS) — API-key-gated B2B | Scam-alert site, currency-check site, live-call monitor, WhatsApp |
| **Disrupt** | Action queue: freeze mule account, block scam number, MHA/I4C alert — each with priority, SLA, evidence chain | Screen-account verdicts: BLOCK / EDD / monitor / clear, with "file STR" guidance | **Mid-call intercept before the transfer** — the call monitor interrupts with a full-screen + spoken warning |
| **Respond** | Dispatch / acknowledge / dismiss with append-only audit log (dispatch simulated, explicitly labelled) | Same queue visibility for actions targeting their accounts | Guided advisory in **22 languages**, clear next steps (1930 helpline, cybercrime.gov.in) |

### 2.3 The four systems

| Module | Port | AI type | What it does |
|---|---|---|---|
| 🗣️ **Fraud Shield** | 8001 | Supervised NLP + marker rules + LLM red-team loop | Classifies calls/messages as scam / suspicious / legit with evidence spans; live-call risk staircase; WhatsApp channel; 22 languages |
| 💵 **Counterfeit Vision** | 8002 | CNN (EfficientNet-B0 transfer learning) + OpenCV forensics + serial registry + vision-LLM | Genuine / fake / uncertain verdict naming the failed security feature; serial-number validation & duplicate-sighting registry |
| 🕸️ **Fraud Graph** | 8003 | Graph feature engineering + XGBoost + Louvain communities | Scores accounts, clusters mule rings (chains, smurfing fan-in, round-tripping), district-tagged; real-data validated on Elliptic++ |
| 🎛️ **Command Centre** | 8000 / 4000 / 3000 | Agentic Gen-AI fusion + DBSCAN geospatial + deterministic response engine | Correlates all three signals into intelligence packages; crime map with coordinated hubs; action queue; B2B APIs; Model Card |

### 2.4 The three live "wow moments" (all real, all demoable)

1. **Scam call read aloud** → flagged at **99.9% risk** with the digital-arrest markers that triggered it (authority impersonation, fake FIR, video-call isolation, urgency…).
2. **Note held to a camera** → verdict **FAKE ₹500**, with the *specific* missing security feature named (security thread / watermark / microprint).
3. **RUN FUSION** → the dashboard writes: *"This scam call is linked to a fraud ring active in Jamtara, where a counterfeit ₹500 note was also seized"* — **threat: CRITICAL**, with a reproducible audit hash — and beneath it, the **money trail**: *"₹49,999 reported by an Alwar victim traced into collector account acc_02033 of ring_06, six hours after the call."* That is an account number you can freeze tonight.

Plus the interactive kill-shot: judges **name a gang**, we inject that never-seen ring into the transaction stream live, and the model catches it in ~3 seconds — proof it learned laundering *behaviour*, not memorised account IDs.

---

## 3. What We Did That Is New, Different, and First-Time

### 3.1 Cross-domain fusion with a deterministic evidence engine (first of its kind)

**No product on the market correlates scam detection + counterfeit currency + fraud-ring intelligence.** Single-domain products exist in each silo (see §4); the convergence layer does not. Ours is also *architecturally novel* in how it uses Gen AI:

> **The engine decides; the AI explains.** Links between events require concrete, checkable evidence — same district, ≤30 km geo-radius, ≤96 h time window, or an exact money-trail match (amount ±1% AND 0–96 h window AND district). The LLM **narrates** established links into an intelligence brief; it **cannot create, remove, or reweigh a link**. Every fusion output carries `audit_trail.inputs_hash` — re-run the fusion with the same inputs and you get the same hash. That is what makes the package *admissible*, not just impressive.

This is the challenge's "Agentic AI for multi-source intelligence fusion" — implemented so that hallucination is structurally impossible in the evidence path.

### 3.2 A deployed self-improving classifier (exists only as a research paper elsewhere)

Scams evolve, so Aegis **red-teams itself**: an LLM writes *next year's* scam scripts — including whole families the classifier had **never seen** (investment fraud, job-task scams) — half augment training, half are held out as "unseen future scams."

**Measured result: scam recall on held-out unseen variants 69% → 100%, with zero human labelling** (held-out ROC-AUC after: 0.997). The evaluation half never enters training — the protocol is stated in the persisted report itself. To our knowledge this loop exists in the literature (a January 2026 paper) and in **zero deployed products**.

### 3.3 Counterfeit printing-run detection via a serial-sighting registry (new for citizen tools)

Real counterfeiting is industrial: a press copies **one genuine serial number onto every note of a plate**. Aegis exploits this: every scanned serial is validated against the **RBI Mahatma Gandhi (New) Series format** (digit + 2 letters + 6 digits; I/O never used in prefixes; repeated/sequential digit blocks = classic prop-money tells) and then checked into a **durable sighting registry** (MongoDB Atlas, JSON-file fallback). The same serial surfacing in two different scans — different districts, different days — elevates to `duplicate`: **evidence of a counterfeit printing run**, a distribution-network signal no single-note scanner can produce.

### 3.4 Cap-only AI safety invariant (a design contribution)

Every advisory layer in Counterfeit Vision — OpenCV triage, serial checks, the vision-LLM review — obeys one machine-enforced rule, covered by tests:

> An auxiliary finding can make the system **more cautious** (cap a `genuine` verdict to `uncertain`, forcing manual review) — it can **never convict, and never acquit**. A note is never certified genuine while any check fails; a `fake` verdict is never softened.

This directly answers the brief's hardest constraint — *"false positive rate for citizen-facing tools must be very low"* — with an architecture, not just a threshold.

### 3.5 Mid-call intercept before the transfer (pre-victimisation, not post-complaint)

The live-call monitor re-scores the **cumulative transcript** after every utterance. On the demo script the risk staircase climbs 12% → 46% → **94% and triggers a full-screen + spoken intercept before the payment demand completes**. Detection at the *point of contact*, not the point of complaint — the exact shift the challenge asks for.

### 3.6 The money trail: joining a victim's report to a freezable account

A scam event carrying the victim's `reported_payment` is matched — amount (±1%) + payment window (0–96 h after the call) + district — against **actual transaction edges flowing into detected ring collector accounts**. Output: *"₹49,999 traced into account acc_02033 of ring_06 (Alwar)"* with a `shared_account` correlation basis. Not a heat map — **an account number to freeze**.

### 3.7 Cross-domain coordinated-hub detection on the map

DBSCAN clusters all event types together; a hotspot where **independent detection systems converge** (scam + counterfeit + ring in one geo-cluster) is flagged as a **coordinated crime hub** — the red pulsing circle on the command-centre map. Single-domain hotspot maps exist; cross-domain convergence detection does not.

### 3.8 Contract-first architecture (an engineering innovation that showed up in the product)

The **only coupling between modules is JSON** validated against versioned schemas in `contracts/`. Detection modules never import each other. Four people built four systems in parallel with near-zero merge conflicts, and any model can be swapped without touching the rest — the scalability story judges ask about, demonstrated in our own development history.

### 3.9 Honest-negative research reporting (rare anywhere)

Our Research Lab (§9) ships three genuine research experiments — federated cross-bank detection, an adversarial arms race, spectral graph analysis — **with their negative results displayed as prominently as their positives**, verdicts generated from the data rather than hard-coded optimism. We believe showing a judge a red "federation did NOT beat the best single bank on this run" box, next to a perfect 0.0 false-merge rate, is worth more than a fabricated success — and it is exactly the evidentiary discipline the platform preaches.

---

## 4. Comparison With Existing Solutions

| Existing solution | What it does | Where Aegis goes further |
|---|---|---|
| **RBI MuleHunter.ai** (+ I4C–RBIH MoU, May 2026) | ML over transaction patterns to flag mule accounts, per-bank | Aegis's Fraud Graph is a working MuleHunter-class engine — **and the fusion layer joins the mule ring back to the scam that fed it and the district where the cash surfaces**. The state's own roadmap validates our thesis; we built the next step. |
| **Truecaller / telco spam ID** | Caller-ID reputation: flags *numbers* | Aegis classifies *content* with **evidence spans** (court-usable), works on first contact from an unknown number, monitors **live calls with mid-call intercept**, and covers WhatsApp text — where number reputation is blind. |
| **I4C 1930 helpline / cybercrime.gov.in / Chakshu portal** | Post-incident complaint intake and reporting | Aegis operates **pre-transfer** at the point of contact; its citizen tools *end* with guided reporting to these very portals — we complement, not duplicate. |
| **Bank note-sorting machines / UV lamps** | Branch-bound hardware; pass/fail with no explanation | Aegis is **software on any phone camera**, names *which* security feature failed, and runs the **serial dedup registry** that turns isolated scans into printing-run network intelligence. B2B endpoint serves tellers/POS. |
| **Single-domain fraud-analytics SaaS** (transaction monitoring vendors) | One domain, opaque scores, no citizen surface | Aegis fuses **three domains** with a deterministic correlator, reproducible audit hashes, and citizen + LEA + bank surfaces on one contract-validated data plane. |
| **Self-improving scam classifiers** | January 2026 research paper; no deployments | Aegis ships the loop, with a leakage-safe eval protocol and measured 69% → 100% unseen-family recall (§3.2). |

---

## 5. Metrics & Measured Results

> **Methodology & integrity.** Every figure below is read from a model's **own persisted training/eval report** in the repo (`models/train_report.json` per module, `self_improve_report.json`, `ghost_ring.json`, `spectral_data.json`) — the same files the dashboard's **Model Card** (`GET /metrics`) serves live. Nothing is recomputed or tuned for display; the Model Card carries that disclaimer in the product. Ring-recovery numbers below were **re-run and re-verified on 19 July 2026**. Exact figures vary by ±0.01 across retrains (fresh seeds per machine); the dashboard always shows the current run's truth.

### 5.1 Fraud Shield — scam / digital-arrest detection (the brief's "precision and recall" ask)

Held-out test protocol: template-grouped 3-way split (tune on validation, report on untouched test) so paraphrases of a training script can never leak into the test set.

| Metric | Value |
|---|---|
| ROC-AUC | **0.994** |
| Average precision | **0.989** |
| Scam-verdict precision (precision-first threshold) | **0.980** |
| Scam-verdict recall | **0.943** |
| **Digital-arrest family recall** | **1.00** |
| Synthetic KYC / loan / phishing family recall | 1.00 / 1.00 / 1.00 |
| UCI SMS spam (public benchmark slice) | 0.930 |
| False-alarm rate (1 − precision, the citizen-tool FPR) | **2.0%** |
| Train / test sizes | 3,407 / 1,076 |

**Self-improvement loop** (eval half never trained on; two families brand-new to the model):

| | Before | After |
|---|---|---|
| Scam recall on held-out LLM-evolved variants (n=64) | 68.8% | **100%** |
| — of which *investment fraud* (never-seen family) | 75% | 100% |
| — of which *job-task scam* (never-seen family) | 37.5% | 100% |
| Held-out ROC-AUC after augmentation | — | 0.997 |
| Human labels used | 0 | 0 |

### 5.2 Counterfeit Vision — accuracy across denominations and print quality (the brief's CV ask)

Two evaluation regimes, honestly separated:

**Real-photo dataset** (Kaggle fake-currency dataset, EfficientNet-B0 retrained): validation accuracy **0.969**, ROC-AUC **0.994**, fake precision/recall **0.976 / 0.964**, false-alarm **2.4%**.

**Synthetic baseline** (repo-reproducible renderer with per-feature ground truth — ₹500 and ₹2000, controllable security features):

| Metric | Value |
|---|---|
| Validation ROC-AUC | 0.962 |
| **Fake-verdict precision** | **1.00** (zero false accusations) |
| Fake-verdict recall | 0.79 |
| Uncertain rate (routed to manual check) | 18.3% |
| OpenCV feature checks (thread darkness, watermark lift, microprint sharpness) | 40/40 genuine clean · 40/40 fakes caught **with the correct feature named** |

**Print-quality coverage** comes from the layered design: the pre-CNN triage catches low-grade fakes deterministically (B&W photocopy saturation, flat-print texture, wrong aspect ratio/hue), the CNN handles high-grade fakes, the serial registry catches *perfect* fakes that reuse a serial. Denomination is inferred from hue (₹500/₹2000); per-denomination metric breakdown is on the roadmap (§14).

### 5.3 Fraud Graph — network detection (the brief's "lead time" and admissibility asks)

**Synthetic world** (3 laundering topologies — mule chains, smurfing fan-in, round-tripping — *plus* legitimate heavy actors like merchants and payroll, so the model must learn behaviour, not "big amount = fraud"):

| Metric | Value |
|---|---|
| ROC-AUC | **0.998** |
| Average precision | 0.971 |
| Precision / recall at chosen threshold | 0.90 / 0.973 |
| **Ring recovery (re-verified 19 Jul 2026)** | **12/12 rings (100%)** |
| Account-level precision / recall within rings | **0.976 / 0.988** |

**Real-data validation — Elliptic++ (real Bitcoin fraud graph, the only large public labelled fraud network):** ROC-AUC **0.994**, average precision **0.950**, precision/recall **0.900 / 0.854**. Same pipeline, no code changes — it transfers because we score graph **topology** (fan-in/out, layering, communities), not currency-specific features; the same reason it applies to UPI rails.

**Detection latency (the honest version of "lead time"):** the live inject-ring console measures it on stage — a never-seen ring is caught **~3 seconds** after its transactions enter the stream, with no retraining. The Model Card states plainly that "lead time before mass victimisation" is a workflow claim, not a stored number — no victimisation timeline is simulated; *latency* is what is measured. Scam detection is pre-transfer **by construction** (it runs on the live message); counterfeit verdicts are one forward pass at the counter.

### 5.4 False-positive posture (the brief's hardest citizen-tool requirement)

- Every module thresholds **precision-first** from its own PR curve (scam band tuned to ≥0.97 precision).
- Counterfeit `fake` precision is **1.00** on the synthetic benchmark — the layer that talks to citizens never cries wolf; ambiguity routes to `uncertain` + manual check.
- `legit` / `genuine` verdicts are **excluded from correlation entirely** — a citizen's innocent message can never contribute to a "crime hub."
- The cap-only invariant (§3.4) means auxiliary AI can only *raise* caution, never generate an accusation.
- Fusion links require deterministic evidence; the false-merge rate measured in the federated experiment is **0.0** (§9.1).

---

## 6. System Architecture

### 6.1 Topology — the 3-website setup

Two citizen-facing sites and a police command centre, over one contract-validated data plane:

```
  CITIZENS                      PUBLIC ENTRY              COMMAND CENTRE (police/analyst)
┌──────────────────────┐      ┌───────────────┐      ┌────────────────────────────────────┐
│ Scam-alert site :8001│─────▶│               │      │ FastAPI backend :8000              │
│  chat · live call ·  │      │  Express 5    │─────▶│  event store · health · /fuse      │
│  WhatsApp            │      │  gateway :4000│      │  /actions · /institution/* ·       │
├──────────────────────┤      │  validate +   │      │  /metrics · /citizen/*             │
│ Currency-check :8002 │─────▶│  forward      │      ├────────────────────────────────────┤
│  camera scanner ·    │      └───────────────┘      │ Fusion (Python): deterministic     │
│  serial check        │              ▲              │  correlator + LLM narrator         │
└──────────────────────┘              │              │ Geospatial: DBSCAN hubs            │
                                      │              ├────────────────────────────────────┤
┌──────────────────────┐              │              │ Next.js 15 dashboard :3000         │
│ Fraud Graph :8003    │◀─────────────┘              │  MapLibre crime map · fusion       │
│  internal service    │   (backend refresh)         │  reveal · ring viewer · Model Card │
└──────────────────────┘                             └────────────────────────────────────┘
```

- **Contracts are the only coupling.** `contracts/*.schema.json` (scam_detection, counterfeit, fraud_graph, fusion_output, response_action) + samples + a shared validator. Every arrow above carries schema-validated JSON.
- **The gateway is the single public entry**; internal ML services are never exposed.
- **Map tiles are keyless and free** (CARTO dark / Esri via MapLibre GL) — the demo cannot die on a missing token.

### 6.2 The fusion pipeline

```
Dashboard ──POST /fuse──▶ Backend ──▶ Deterministic correlator
                                        · evidence links: shared_district / geo ≤30 km / time ≤96 h
                                        · money trail: amount ±1% ∧ 0–96 h ∧ district → ring account
                                        · threat level = # distinct domains linked (3 = CRITICAL)
                                            │  FACTS ONLY
                                            ▼
                                       LLM narrator (Groq → Gemini → Claude → template)
                                        · narrates links, recommends actions (JSON-constrained)
                                        · cannot create/remove links
                                            │
                                            ▼
                                   fusion_output.json  (contract-valid, audit_trail.inputs_hash)
                                            │
                                            ▼
                                   response engine auto-derives Disrupt/Respond actions
```

### 6.3 Key backend surface

| Endpoint | Purpose |
|---|---|
| `POST /fuse` | Run fusion; auto-derives response actions |
| `GET /actions` · `POST /actions/{id}/dispatch\|acknowledge\|dismiss` | Disrupt/Respond queue (simulated dispatch, append-only audit) |
| `POST /institution/screen-account` · `POST /institution/verify-note` | B2B bank surface (X-API-Key) |
| `GET /metrics` | Model Card — measured P/R, FPR, AUC, per-family, latency |
| `POST /citizen/analyze` | Citizen message check in 22 languages (Sarvam translate → Fraud Shield → advisory back) |
| `POST /citizen/call/analyze` | Live-call monitoring — running verdict on the transcript so far |
| `POST /citizen/whatsapp` · `POST /webhook/whatsapp` | WhatsApp transport (simulator + Twilio webhook with HMAC signature validation) |
| `GET /rings/{id}/spectral` | Per-ring spectral corroboration badge (research) |

### 6.4 Tech stack

- **Fraud Shield** — Python · scikit-learn (word+char TF-IDF ⊕ 8 marker features → Logistic Regression) · FastAPI · browser SpeechRecognition (en-IN) + speechSynthesis for the live-call monitor
- **Counterfeit Vision** — PyTorch (EfficientNet-B0 transfer learning) · OpenCV (feature checks, triage forensics, contour + perspective note localisation) · MongoDB Atlas serial registry (fail-open JSON fallback)
- **Fraud Graph** — NetworkX · XGBoost · Louvain/Leiden communities · Elliptic++ real-data benchmark · Typer CLI
- **Command Centre** — Next.js 15 · React 19 · Tailwind 4 · MapLibre GL · FastAPI · Express 5 · scikit-learn DBSCAN (haversine)
- **Gen AI** — Groq (Llama-3.3-70B) / Gemini / Claude with structured JSON output and failover; Sarvam AI for 22-language translation
- **Shared** — JSON-Schema contracts · pytest across all modules · GitHub

---

## 7. Module Deep-Dives

### 7.1 Fraud Shield (NLP scam & digital-arrest detection)

- **Marker rules engine** for the 8 contract markers — authority impersonation, fake FIR/legal threat, urgency, isolation ("do not tell anyone"), video-call coercion, payment demand, secrecy, spoofed identity — each match returning the **exact evidence span** from the text.
- **Classifier**: word+char TF-IDF ⊕ marker features → Logistic Regression; precision-first thresholds from the PR curve; three verdict bands (scam / suspicious / legit).
- **Corpus**: public datasets predate digital arrest entirely, so we built a **synthetic Indian-scam corpus** (digital-arrest scripts, KYC-freeze, lottery, loan, phishing + hard legitimate negatives — real bank/govt messages that *look* alarming), blended with the UCI SMS Spam Collection, and extended by the LLM red-team corpus (§3.2).
- **Live-call detection (two modes)**: Mode B replays a scripted scam call turn-by-turn; Mode A uses the browser microphone (Chrome/Edge SpeechRecognition, en-IN). Both re-score the **cumulative transcript** on every utterance — risk climbs 12% → 46% → 94% on the demo script — and on crossing the scam threshold fire a **full-screen intercept overlay plus a spoken warning** (speechSynthesis) *before the payment ask completes*.
- **WhatsApp channel**: a Twilio sandbox webhook (`/webhook/whatsapp`) with **HMAC-SHA1 X-Twilio-Signature validation** (tunnel-aware), answering any forwarded message with a verdict + advisory TwiML reply; plus a phone-frame **simulator page** so the demo works with zero external dependencies.
- **22 languages**: the citizen analyze pipeline translates in (Sarvam AI), classifies in English, and returns the advisory in the citizen's language — a wrapper, not a retrain; fails safe to English passthrough without a key. (The brief asked for 12 regional languages; all 22 scheduled languages are covered.)
- 15+ offline tests; contract emitter validated by `shared/validate_contract.py`.

### 7.2 Counterfeit Vision (fake-currency detection)

A **layered funnel, cheap-and-certain before expensive-and-probabilistic**:

1. **Triage (OpenCV forensics, pre-AI)** — Laplacian blur variance (unscannable), HSV saturation (B&W photocopy = conclusive tell), flat-print texture, aspect-ratio window (1.70–3.10), known ink-hue windows. Decision rule: `unscannable` / `obvious_fake` (≥2 independent tells, or one conclusive) / `pass` to the model. Obvious junk never wakes the CNN.
2. **CNN** — EfficientNet-B0 transfer learning; verdict fusion with per-feature OpenCV checks (security-thread darkness contrast, watermark brightness lift, microprint sharpness). **≥2 failed features (or 1 + elevated CNN score) ⇒ fake; a note is never certified genuine while any check fails; mid-band ⇒ uncertain.**
3. **Serial layer** — RBI format validation (§3.3), then the **durable sighting registry**: MongoDB Atlas when configured, JSON file otherwise, every DB path **fails open** so a database hiccup can never break a scan. A duplicate sighting elevates the verdict cap and raises a dashboard alert (printing-run signal).
4. **Vision-LLM review (optional, keyed)** — checks portrait identity (Gandhi), SPECIMEN/COPY overprints, RBI header text; findings are advisory and **cap-only** (never convict — genuine SPECIMEN-stamped training notes exist, which is exactly why).
- Robustness: contour + perspective-warp note localisation so angled phone shots land the feature regions; upload size caps; captures served for dashboard evidence display.
- The contract schema gained optional `triage`, `serial`, `vision_review` blocks — additive, nothing downstream breaks.

### 7.3 Fraud Graph (ring detection)

- **Synthetic world generator** with three real laundering topologies — mule chains, smurfing fan-in, round-tripping cycles — *plus* legitimate heavy actors (merchants, payroll, B2B) so "big volume" alone can't score.
- **18 graph features** per account (fan-in/out ratios, burst ratio, throughput, hold time, PageRank, clustering, core number, mule score…) → **XGBoost** with feature importances persisted (auditability); **Louvain** clustering turns high-scoring neighbourhoods into named rings with district tags, member lists, and risk bars.
- **Ring viewer**: renders the actual money flow of any ring — click an account for plain-word evidence (*"money out ≈ money in · 56% of transfers within 60 min · round amounts"*).
- **Live inject-ring console**: judges design a gang (or name one); its transactions enter the stream; detection happens live with no retraining. A **fraud console** lets a skeptic build any money movement and press Run — laundering is caught, a normal day comes back clean, and clean runs never pollute the map.
- **Elliptic++ badge**: a confirmed-illicit wallet cluster from the real Bitcoin blockchain renders in the same viewer, labelled REAL.

### 7.4 Command Centre

- **Dashboard**: module health pills, three signal cards, warning feed with click-to-fly alerts, signal-volume bars, the TAKE → MOVE → CASH OUT pipeline strip with live counts, full-bleed MapLibre crime map (pulsing per-domain markers, red coordinated-hub rings), **Run Fusion** typewriter reveal with the audit hash on screen, ring viewer, per-district **case files** (AI officer narrative over a deterministic dossier), Disrupt tab (action queue), Bank Partner tab (B2B), **Model Card** tab (§5), Research Lab tab (§9).
- **Geospatial**: DBSCAN clustering over all event types; `cross_domain=true` hubs are the coordinated-crime signal; district → coordinates lookup places graph rings on the map.
- **Response engine** (`response.py`): deterministic rules turn findings into recipient-addressed actions — freeze account (bank), block number (telco), MHA/I4C alert, victim intercept, manual review — each with priority, **SLA against the fraud clock**, trigger evidence refs, and an append-only audit log. Dispatch is **simulated and labelled as such** — honesty over theatre.

---

## 8. Generative AI: Doctrine, Fusion & Resilience

- **Doctrine — "the engine decides, the AI explains."** Deterministic engines produce every verdict, link, threat level, and action; LLMs narrate them for humans. In the one place an LLM *sees* images (vision review), its findings are cap-only. Hallucination is structurally excluded from the evidence path.
- **Where Gen AI works in the product**: fusion narration; dashboard morning **briefings** (server-cached, Mongo-durable, real data in every sentence); per-district case-file officer narratives; citizen advisories in 22 languages; triage/serial narration on the counterfeit site; the red-team scam generator (§3.2); the vision review.
- **Failover chain everywhere**: Claude → Groq (Llama-3.3-70B) → Gemini → **deterministic template**. Every Gen-AI surface has a data-faithful template fallback; the entire platform runs with **zero API keys** (a stated design constraint — the demo cannot die on stage, and a poor district deployment cannot die on budget).
- **Dynamism audit**: every AI-written surface regenerates from current data (and is labelled when a cached briefing is shown); nothing is canned text.

---

## 9. Research Lab — Advanced Experiments, Honestly Reported

A dedicated dashboard tab ships three research experiments with **data-driven verdicts** — the display logic renders whatever the numbers say, including failure.

### 9.1 Ghost Ring — federated cross-bank ring detection

**Question**: can four banks find a ring that spans them, sharing only hashed account tokens (privacy-preserving), never raw ledgers?
**Measured** (persisted `ghost_ring.json`): cross-bank edge **matching precision 1.00**, **false-merge rate 0.00**, fused ring precision 1.00; per-bank ring recall 0.44–0.73; fused recall 0.494 — **below the best single bank on this run, and the card says so in red**. The honest claim: the privacy-preserving *matching* mechanism is validated (zero false merges — the legally dangerous failure mode); the fusion recall gain is not yet demonstrated. That distinction is on the card.

### 9.2 Arms Race — adversarial co-evolution

**Question**: if launderers evolve against the detector (evolutionary search over ring parameters), does retraining keep up?
**Measured** (30 generations): attacker's best-escape rate reaches **0.86** by the final generation while detector recall on evolved rings falls to **0.20** — an "attacker wins" regime on this run, presented as exactly that, with the mean-escape curve (the honest statistic) charted instead of the max-of-population one that pegs near 1.0 by construction. The takeaway shown to judges: static detectors decay against adaptive adversaries — which is *why* the self-improving loop (§3.2) is in the main product.

### 9.3 Spectral — graph-signal analysis of laundering rings

**Question**: do fraud rings look different in the graph's spectral domain (Rayleigh quotient of the transaction signal on the normalized Laplacian)?
**Measured** (persisted run): matched-pair shift — ring community **0.917** vs size-matched clean community **0.693** (shift **+0.223**) — rings *are* spectrally rougher on this validated pairing. Cross-community *ranking* is documented as unreliable (module docs say so), so the UI labels it a triage hint only, and the per-ring badge in the ring viewer renders **only when the spectral signal corroborates** — it never contradicts the main engine (cap-only thinking again).

---

## 10. Auditability, Legal Admissibility & Safety

The brief names *"auditability of intelligence packages for legal admissibility"* as an evaluation focus. Aegis treats it as a first-class feature at **every** layer:

| Layer | Evidence artefact |
|---|---|
| Scam verdict | Matched marker **evidence spans** (the exact words), per-marker scores, model probability |
| Counterfeit verdict | Per-feature check scores, triage tells, serial status + prior sightings, capture image ref |
| Ring detection | Per-account **feature importances** (XGBoost), plain-word account evidence, ring member/edge lists |
| Fusion package | `correlation_basis` per link (which rule fired, with the measured distance/hours), threat derivation, **reproducible `audit_trail.inputs_hash`** |
| Response action | `trigger.refs` evidence chain, priority/SLA, **append-only audit log** of every state change; an action never asserts guilt |
| Model claims | The Model Card serves measured metrics **from persisted reports with a printed disclaimer**; postures labelled honestly (Predictive / Point-of-contact / Fast-classification) |

Safety and privacy engineering: precision-first thresholds; cap-only invariants; legit verdicts excluded from correlation; hashed tokens in the federated experiment; API keys in gitignored `.env` files only; Twilio webhook HMAC signature validation; API-key gating on B2B endpoints; ingest schema validation at the backend door; CORS restricted by environment; no citizen PII stored beyond the event payloads a deployment would own.

---

## 11. Scalability & Deployment

- **Horizontal by architecture**: six independent services speaking versioned JSON contracts — swap any model (LogReg → DistilBERT, XGBoost → GNN) without touching the rest; scale any service independently; add a new detection domain by adding a contract.
- **Cloud deployment (free tier, fully env-driven)**: Vercel (dashboard, `NEXT_PUBLIC_API_BASE`) + Render (gateway, backend, ML services; per-service root directories; models train on deploy since weights are gitignored) + **MongoDB Atlas M0** for durable state (serial-sighting registry, briefing cache) — with fail-open JSON/file fallbacks so *nothing* breaks if the database blinks. Total infrastructure cost: **₹0**.
- **Runs fully offline too**: one script (`./run-all.ps1`) starts all six services locally with zero keys — the stage-proof path, and the *"constrained-connectivity district office"* path.
- **Practical scale limits stated honestly**: DBSCAN → sklearn haversine at city scale; boosted trees at this scale match GNN accuracy while training in seconds and giving feature importances (auditability); a national deployment would swap the synthetic feed for bank/telco integrations behind the same contracts.

---

## 12. User Experience

- **Citizens** get two clean single-purpose sites (scam check with chat + live call + WhatsApp; note check with camera), in a consistent dark zinc/violet design system with the Aegis owl-shield identity, responsive clamp-based layouts down to small laptops, instant verdicts in plain language, and advisory in **22 languages**. False alarms are engineered low (§5.4) because a citizen tool that cries wolf gets uninstalled.
- **Analysts/police** get a single dark-theme command centre: three cards, one map, one fusion button; click-to-fly alerts; plain-word evidence everywhere ("money out ≈ money in", not "high betweenness centrality"); case files that read like a briefing, not a CSV.
- **Judges/banks** get interactive proof: the inject-ring console, the fraud console for building arbitrary scenarios, the Bank Partner screen, and a Model Card that shows real measured numbers with their caveats.
- **Demo resilience is a UX feature**: every beat of the 6-minute run-of-show (`docs/demo-script.md`) has a fallback; keyless map tiles; template narration if every LLM fails; per-module graceful degradation on the dashboard.

---

## 13. Challenge Compliance Matrix

### 13.1 "What you may build" — we built all five

| Challenge suggestion | Aegis delivery |
|---|---|
| **Digital Arrest Scam Detection & Alerting** — real-time classifier on call flows/scripts, flags active sessions **before financial transfer**, automated MHA alert generation | ✅ Fraud Shield: digital-arrest recall 1.00; **mid-call risk staircase with pre-transfer intercept**; marker evidence; response engine auto-generates **MHA/I4C alert actions** (simulated dispatch, labelled) |
| **Counterfeit Currency Identification Agent** — mobile-deployable CV; microprint, security thread, **serial number pattern validation**; field officers and tellers | ✅ Counterfeit Vision: phone-camera scanner; security-thread/watermark/microprint checks naming the failed feature; **RBI serial validation + duplicate registry**; `POST /institution/verify-note` for teller/POS |
| **Fraud Network Graph Intelligence** — transaction metadata + account linkages → coordinated campaigns, mule networks, **court-admissible packages**, cross-jurisdiction | ✅ Fraud Graph: 12/12 ring recovery, real-data validated; district-tagged rings; evidence-carrying intelligence packages with reproducible hashes; federated cross-bank research (§9.1) for the cross-jurisdiction path |
| **Geospatial Crime Pattern Intelligence** — map complaints, seizure points, hotspots; command-centre interface; inter-district sharing | ✅ MapLibre crime map; DBSCAN hotspots; **cross-domain coordinated-hub detection**; per-district case files; pipeline strip |
| **Citizen Fraud Shield (Multi-channel)** — conversational AI via **WhatsApp, IVR, app**; instant verdicts; guided NCRB reporting; **12 regional languages** | ✅ Web chat + **live-call monitor** + **WhatsApp** (Twilio + simulator); instant verdicts with advisory; guided pointers to 1930/cybercrime.gov.in; **22 languages** (brief asked 12). IVR: transport adapter designed, on roadmap |

### 13.2 Suggested technologies — all six used

| Suggested | Where |
|---|---|
| Computer Vision | Counterfeit CNN + OpenCV forensics + note localisation |
| Graph AI & Network Analysis | 18-feature XGBoost + Louvain rings + spectral research |
| NLP / LLMs | TF-IDF⊕marker classifier; LLM red-team; narrators |
| Geospatial Intelligence | DBSCAN hubs, crime map, district case files |
| Speech AI | Live-call SpeechRecognition (en-IN) + spoken intercept; voice-spoofing detection on roadmap |
| Agentic AI for multi-source fusion | The fusion layer itself — deterministic correlator + constrained LLM narration + auto-derived actions |

### 13.3 Expected deliverables

| Deliverable | Status |
|---|---|
| Working prototype | ✅ This repo — 6 services, 3 websites, all wow-paths verified end-to-end |
| Architecture diagram | ✅ `docs/architecture.md` (system, fusion sequence, Detect→Disrupt→Respond) |
| Presentation deck | ✅ `docs/pitch-deck.md` (slide-by-slide, every number from persisted reports) |
| Demo video | 🎬 Run-of-show scripted (`docs/demo-script.md`); recording scheduled |

### 13.4 Evaluation focus — answered by measurement

| Named focus | Our answer |
|---|---|
| Counterfeit detection accuracy across denominations and print quality | §5.2 — layered funnel covers the print-quality spectrum; ₹500/₹2000; real-photo P/R 0.976/0.964 |
| Digital-arrest scam detection precision and recall | §5.1 — precision 0.98 / recall 0.94; digital-arrest family recall 1.00 |
| Fraud network detection lead time before mass victimisation | §5.3 — ~3 s live detection latency; pre-transfer by construction for scams; honestly scoped in-product |
| False positive rate for citizen-facing tools (must be very low) | §5.4 — 2.0–2.4% false-alarm; fake precision 1.00 on citizen path; cap-only invariants |
| Auditability of intelligence packages for legal admissibility | §10 — evidence artefacts at every layer + reproducible audit hashes + append-only action logs |

---

## 14. Honest Limitations & Roadmap

We state these before a judge asks — the platform's credibility *is* its evidentiary discipline:

- **Transaction stream is synthetic / Elliptic++** — there is no live bank feed; that is a partnership, not a technology gap. Real deployment would join the money trail by UPI/transaction reference, not amount (same join, stronger key — labelled in-product).
- **Dispatch is simulated** — freeze/block/MHA actions are queued, audited, and labelled simulated; live telecom/bank/government wiring sits behind the already-built response-action contract.
- **Rings → counterfeit link is geographic convergence**, not a traced artefact — tracing physical cash needs serial capture at seizure (the contract fields exist as the hook).
- **Live-call audio**: speech recognition is browser-based today; a server STT front-end (e.g. Sarvam *saarika*) feeding the same analyzer is the designed next step, along with IVR transport and validation on real call recordings.
- **Per-denomination counterfeit metrics** and real-note field validation beyond the Kaggle dataset are on the roadmap.
- **Research lab findings are runs, not theorems** — the federated recall gain is unproven (stated on the card); the arms race shows detector decay (that is the point); spectral ranking is a triage hint only.
- Twilio/WhatsApp runs in sandbox mode; production requires a WhatsApp Business account.

---

## 15. Results & Conclusion

### 15.1 Results at a glance

| System | Headline measured result |
|---|---|
| Scam / digital-arrest detection | ROC-AUC **0.994** · precision **0.98** · digital-arrest recall **100%** · false-alarm **2%** |
| Self-improving loop | Unseen-family scam recall **69% → 100%**, zero human labels |
| Counterfeit detection | Real-photo acc **0.969** / AUC **0.994**; synthetic fake-precision **1.00**; 40/40 feature checks with the correct feature named |
| Fraud-ring detection | **12/12 rings**, account P/R **0.976/0.988**; **0.994 AUC on real Elliptic++**; ~3 s live detection |
| Fusion | Deterministic cross-domain links + money-trail account trace + reproducible audit hash + auto-derived actions |
| Federated research | Cross-bank matching precision **1.00**, false merges **0** (fusion recall gain honestly unproven) |
| Cost of the entire stack | **₹0** — free-tier cloud or a single laptop, zero API keys required |

### 15.2 Conclusion

The challenge asked for a shift **from reactive case investigation to predictive threat neutralisation**. Aegis delivers that shift in the three places it actually happens:

1. **At the point of contact** — a scam is intercepted mid-call before the transfer; a note is verdicted at the counter; a ring is caught seconds after the laundering pattern forms.
2. **Across domains** — the platform's defining move is the join: scam → mule ring → cash economy, correlated by deterministic evidence into one intelligence picture no single-domain tool can see.
3. **Into action** — detections become recipient-addressed, SLA-tracked, audit-logged disrupt/respond actions for police, banks, and citizens.

And it does so with a discipline we believe matters more than any single metric: **every verdict carries its evidence, every AI claim is capped by a deterministic engine, every number on every card is read from a persisted report — including the negative ones.** That is what makes an intelligence package court-admissible, a citizen tool trustworthy, and a hackathon prototype a credible blueprint for national deployment.

Four people. A few days. Free-tier infrastructure. **Because the architecture — not the budget — is the innovation.**

**We're Aegis.**

---

## 16. Appendix: Team, Repository & How to Run

### Team

| Member | Module |
|---|---|
| **Sudarsan** | Fraud Shield (NLP scam detection) — classifier, markers, corpus, chat UI, live-call monitor, WhatsApp channel |
| **Adharshan** | Counterfeit Vision (CV fake currency) — CNN, real-dataset retrain, camera UI |
| **Prayag** | Fraud Graph (Graph ML) + Gen AI fusion — rings, Elliptic++, correlator, narrator, self-improve loop |
| **Pushkar** | Command Centre — dashboard, gateway, map, 3-website architecture |

### Repository layout

```
Aegis/
├── contracts/              JSON schemas + samples every module codes against (the interface)
├── fraud-shield-nlp/       Marker rules · TF-IDF⊕marker LogReg · chat/live-call/WhatsApp UIs   :8001
├── counterfeit-vision/     Triage · CNN · OpenCV checks · serial registry · camera UI          :8002
├── fraud-graph-ml/         18 graph features · XGBoost · Louvain rings · research lab          :8003
├── command-centre/
│   ├── backend/            FastAPI aggregator (fusion, actions, B2B, metrics, citizen APIs)    :8000
│   ├── fusion/             Correlator + multi-provider narrator + self-improving classifier
│   ├── geospatial/         DBSCAN hotspot clustering — cross-domain hubs
│   ├── supply_trail/       Provenance / next-hub-at-risk research
│   ├── gateway/            Express 5 public entry point                                        :4000
│   └── frontend/           Next.js 15 + MapLibre dashboard                                     :3000
├── shared/                 Contract validator — run before every hand-off
├── docs/                   Architecture · demo script · pitch deck · crime-pipeline brief ·
│                           deployment guide · this submission document
└── PROJECT_PLAN.md         Living plan + dated progress log (the build history, day by day)
```

### How to run

```powershell
./setup.ps1        # first time: venvs, deps, model training, npm install
./run-all.ps1      # every run: all 6 services  → open http://localhost:3000
```

Or per-service commands in `README.md`. Optional: a free `GROQ_API_KEY` in `command-centre/fusion/.env` lights up live Gen-AI narration; without any key, deterministic templates keep every feature alive.

*Every metric in this document is reproducible from the repository: `python -m aegis_fraud_shield.cli train` · `python -m aegis_counterfeit.cli train` · `fraud-graph demo` / `fraud-graph evaluate` · `python -m aegis_fusion.self_improve_eval` — each writes the persisted report the dashboard's Model Card reads.*
