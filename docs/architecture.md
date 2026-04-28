## Phase-wise architecture (mapped to `docs/problemstatement.md`)

This document describes a phased architecture for the AI-powered restaurant recommendation system. Each phase is shippable and builds on the previous one.

---

### Phase 0: Project foundation + dataset readiness

**Goal**: Make the system runnable end-to-end with reproducible data loading/preprocessing, and a minimal UI to collect inputs.

- **Components**
  - **Dataset loader**: pulls/loads the Hugging Face dataset (or a cached local copy) and exposes it as a structured table.
  - **Preprocessor/normalizer**: standardizes fields (location naming, cuisines list, rating type, cost/budget mapping) and handles missing values.
  - **Artifacts store**: writes processed data to a local, versionable artifact (e.g., JSONL/Parquet) for fast iteration.
  - **Basic web UI (input source)**:
    - A minimal form for user preferences (location, budget, cuisine(s), min rating, optional free-text).
    - On submit, stores/returns a validated preference payload (even if Phase 0 does not yet compute recommendations).
    - Intended to become the primary “source of input” for later phases; CLI remains optional for debugging.
- **Interfaces**
  - `load_raw_dataset() -> RawDataset`
  - `preprocess(raw) -> CleanDataset`
  - `collect_preferences_via_web() -> Preferences`
- **Outputs**
  - Clean dataset artifact + a preprocessing report (row counts, missingness, unique locations/cuisines).
  - A basic web page that can produce a validated preferences payload.

**Exit criteria**
- Running a single command produces a clean dataset artifact deterministically.
- The web UI can collect preferences and produce a validated payload (no recommender logic required yet).

---

### Phase 1: Deterministic candidate generation (baseline recommender)

**Goal**: Provide correct results for hard constraints without any LLM dependency.

- **Components**
  - **Preference schema**: validates user inputs (location, budget, cuisine(s), min rating, optional preferences).
  - **Filter engine**: deterministic filtering + tie-breaking (e.g., rating desc, cost asc).
  - **Fallback policy**: predictable broadening strategy when results are empty (e.g., relax min rating, expand cuisines, widen budget).
- **Data flow**
  - User preferences → filter engine → candidate set → baseline ranker → top \(N\).
- **Interfaces**
  - `generate_candidates(preferences, dataset) -> list[Restaurant]`
  - `rank_baseline(candidates) -> list[Restaurant]`

**Exit criteria**
- For a given input, the same filtered set and baseline ranking are produced every time.

---

### Phase 2: LLM-assisted ranking + grounded explanations

**Goal**: Improve ranking quality and generate concise, grounded explanations.

- **Components**
  - **Prompt builder**: compacts candidates into a prompt-friendly format (bounded \(K\) candidates).
  - **LLM client**: calls the model with retries/timeouts and cost controls.
  - **Schema-constrained output**: enforces a stable response shape (e.g., JSON with `ranked_ids[]` + `explanations{}`).
  - **Verifier/grounder**:
    - ensures returned IDs exist in candidates
    - checks explanations reference only known fields
    - falls back to baseline ranker if parsing/validation fails
- **Data flow**
  - Preferences + candidates → prompt → LLM → parsed response → validated ranking → enriched results.
- **Interfaces**
  - `rank_with_llm(preferences, candidates) -> RankedRecommendations`
  - `validate_llm_output(output, candidates) -> ValidatedRanking | fallback`

**Exit criteria**
- System returns a ranked list with explanations; failures degrade gracefully to baseline ranking.

---

### Phase 3: User-facing interfaces (CLI first, then web)

**Goal**: Make the system usable and consistent across entrypoints.

- **CLI interface**
  - guided prompts or flags for preferences
  - prints top \(N\) results in a stable format
- **Web interface (optional in v1)**
  - simple form for preferences
  - results page with sorting, “why this” explanations, and empty-state handling
- **Shared application layer**
  - `recommend(preferences) -> RecommendationsResponse` used by both CLI and web

**Exit criteria**
- Users can obtain recommendations via CLI (and web if implemented) with the same underlying logic.

---

### Phase 4: Observability + quality gates

**Goal**: Make behavior measurable, debuggable, and safe to iterate on.

- **Instrumentation**
  - logs for request inputs (sanitized), candidate counts, fallback triggers
  - LLM call metrics (latency, token usage, failure rates)
- **Evaluation harness**
  - golden test cases (preference → expected properties of results)
  - baseline vs LLM comparison on a fixed sample of queries
- **Quality gates**
  - schema validation failures auto-trigger baseline
  - max-candidate and max-token limits enforced centrally

**Exit criteria**
- You can confidently change prompts/ranking logic and detect regressions quickly.

---

### Phase 5: Scalability + robustness (optional)

**Goal**: Support larger datasets and faster retrieval while keeping costs bounded.

- **Faster retrieval**
  - indexing by city/cuisine/budget buckets
  - optional vector search for matching free-text preferences against restaurant metadata
- **Caching**
  - cache preprocessed dataset
  - cache LLM responses keyed by normalized preference inputs + candidate hashes
- **Policy hardening**
  - stricter grounding checks, improved fallback order, configurable ranking weights

**Exit criteria**
- P95 latency improves and token usage remains stable as dataset size grows.

---

### Phase 6: Production-grade Full-Stack Architecture

**Goal**: Decouple the monolithic Phase 3 web UI into a dedicated, scalable frontend and backend ecosystem.

- **Backend (API Service)**
  - Move from local JSONL files to a robust Database (e.g., PostgreSQL or MongoDB) for storing restaurants and observability logs.
  - Enhance the FastAPI layer with caching (e.g., Redis) for frequent queries to reduce LLM costs.
  - Dockerize the Python backend for easy deployment.
- **Frontend (Web Application)**
  - Replace the Phase 3 Vanilla JS/HTML with a modern frontend framework (e.g., Next.js or Vite + React).
  - Implement a highly dynamic, aesthetic UI with modern styling (Tailwind CSS, Framer Motion) featuring responsive design, glassmorphism, and micro-animations.
  - Implement robust client-side state management and error handling (e.g., showing skeleton loaders while the Groq LLM processes).
- **Interfaces**
  - Strict RESTful API decoupling the React frontend from the Python backend.

**Exit criteria**
- Frontend runs on a separate dev server (e.g., `npm run dev`) and communicates with the FastAPI backend over HTTP/CORS.
- Data is persisted and queried from a real database instead of local JSON files.

---

### Phase 7: Deployment to Streamlit

**Goal**: Provide an easily deployable, unified frontend and backend application using Streamlit for rapid sharing and prototyping.

- **Components**
  - **Streamlit Web App**: A unified Python frontend that directly imports and calls the backend recommender functions to render the UI.
  - **Deployment Configuration**: Setup files for Streamlit Community Cloud (e.g., `requirements.txt`, managing API keys via Streamlit Secrets).
- **Data flow**
  - Streamlit UI inputs -> Direct internal Python function call to recommender -> Renders output dynamically.
- **Interfaces**
  - A single, monolithic deployment that bypasses the FastAPI HTTP layer for simpler hosting.

**Exit criteria**
- The application is live and accessible via a public Streamlit URL.

---

### System diagram (logical)

- **Frontend Application**: Next.js/Vite Web App (React) -> Collects preferences & displays dynamic UI.
- **API Gateway / Backend**: FastAPI -> Validates requests, coordinates logic.
- **Data Layer**: PostgreSQL/MongoDB -> Stores clean restaurant dataset.
- **Decision Layer**:
  - Deterministic filter -> queries DB for candidate set.
  - Baseline ranker (always available).
  - LLM ranker (Groq) -> Validator -> Final ranking.
- **Observability Layer**: Logs metrics and evaluations to structured data stores.

