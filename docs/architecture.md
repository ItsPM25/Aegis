# 🏛️ Aegis — System Architecture

> Expected deliverable: architecture diagram. This renders natively on GitHub (Mermaid).
> Export to PNG for the deck via https://mermaid.live if needed.

## Full-system view

```mermaid
flowchart TB
    subgraph inputs["📥 Signal sources"]
        CALL["📞 Scam call / SMS text<br/>(read aloud in demo)"]
        NOTE["💵 Currency note photo<br/>(webcam in demo)"]
        TXN["🏦 Transaction network<br/>(Elliptic++ / synthetic)"]
    end

    subgraph detectors["🔍 Detection modules — independent, contract-coupled"]
        FS["Fraud Shield · :8001<br/>TF-IDF ⊕ marker rules → LogReg<br/>ROC-AUC 0.984 · precision-first thresholds<br/><i>Sudarsan</i>"]
        CV["Counterfeit Vision · :8002<br/>EfficientNet-B0 + OpenCV feature checks<br/>never certifies genuine on failed check<br/><i>Adharshan</i>"]
        FG["Fraud Graph · :8003<br/>18 graph features → XGBoost → Louvain rings<br/>0.9945 AUC real-data benchmark<br/><i>Prayag</i>"]
    end

    subgraph contracts["📜 contracts/ — locked JSON schemas"]
        SCAM_J["scam_detection.json"]
        NOTE_J["counterfeit.json"]
        RING_J["fraud_graph.json"]
    end

    subgraph centre["🎛️ Command Centre — Pushkar + Prayag"]
        BE["Backend aggregator · :8000<br/>ingest · health probes · proxies"]
        CORR["Correlation engine (deterministic)<br/>shared district · ≤30km · ≤96h<br/>audit_trail.inputs_hash"]
        LLM["Gen AI narrator<br/>Claude → Groq (Llama 3.3 70B) → Gemini → template<br/>structured JSON, never-invent-links prompt"]
        GEO["Geospatial · DBSCAN hotspots<br/>cross-domain hub = coordinated crime"]
        FE["Dashboard · :3000<br/>Next.js 16 · React 19 · Leaflet crime map"]
    end

    CALL --> FS --> SCAM_J
    NOTE --> CV --> NOTE_J
    TXN --> FG --> RING_J
    SCAM_J --> BE
    NOTE_J --> BE
    RING_J --> BE
    BE --> CORR --> LLM
    CORR --> GEO
    LLM --> FE
    GEO --> FE
    BE <--> FE

    LLM -.->|"innovation #2: generates evolved<br/>scam variants → retrains Fraud Shield"| FS
```

## The fusion pipeline (innovation #1)

```mermaid
sequenceDiagram
    participant D as Dashboard (:3000)
    participant B as Backend (:8000)
    participant C as Correlator (deterministic)
    participant L as LLM narrator (Groq/Claude)

    D->>B: POST /fuse
    B->>C: scams + counterfeits + fraud_graph
    C->>C: evidence links: shared_district / geo ≤30km / time ≤96h
    C->>C: threat level = # distinct domains linked (3=critical)
    C->>L: FACTS only (established links, never raw guesses)
    L->>L: narrate + recommend actions (JSON-constrained)
    L->>B: summary + actions
    B->>D: fusion_output.json (contract-valid, audit hash)
    Note over C,L: LLM cannot create links — only narrate them.<br/>audit_trail.inputs_hash makes every package reproducible.
```

## Why this architecture wins the judged criteria

| Criterion | Architectural answer |
|---|---|
| **Innovation** | Fusion of 3 independent detectors; deterministic-evidence + LLM-narration split; cross-domain DBSCAN hubs; LLM red-team self-improvement loop |
| **Auditability / legal admissibility** | Marker evidence spans (NLP), per-feature check scores (CV), feature importances (graph), correlation basis + reproducible `inputs_hash` (fusion) |
| **Low false positives** | Every module thresholds precision-first from its PR curve; `legit`/`genuine` verdicts are excluded from correlation entirely |
| **Scalability** | Modules are independent services speaking versioned JSON contracts — swap any model without touching the rest |
| **Resilience (demo!)** | LLM failover chain ends in a deterministic template; dashboard degrades gracefully per-module |

## Port map

| Service | Port | Owner |
|---|---|---|
| Fraud Shield API + chat UI | 8001 | Sudarsan |
| Counterfeit Vision API + camera UI | 8002 | Adharshan |
| Fraud Graph API | 8003 | Prayag |
| Command-centre backend | 8000 | Pushkar/Prayag |
| Dashboard (Next.js) | 3000 | Pushkar/Prayag |
