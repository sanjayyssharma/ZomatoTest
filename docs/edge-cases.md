## Edge cases and failure modes (mapped to `docs/problemstatement.md` + `docs/architecture.md`)

This document enumerates edge cases the system should handle gracefully. It is organized by the phases/components described in `docs/architecture.md` and the requirements in `docs/problemstatement.md`.

---

### Cross-cutting principles (apply everywhere)

- **Never crash on bad input/data**: return a clear user-facing message and/or safe fallback output.
- **Prefer deterministic behavior**: where broadening/fallback is required, use a fixed, documented order.
- **Grounding**: explanations must only reference attributes present in the dataset payload.
- **Bounded cost/latency**: enforce limits for candidate count, prompt size, and LLM timeouts.
- **Stable schema**: internal APIs should return consistent shapes even when results are empty.

---

### Phase 0 edge cases: Dataset loading + preprocessing

#### Dataset access and availability
- **Dataset download fails (network/DNS/timeout)**
  - **Expected**: use cached dataset/artifact if present; otherwise show a clear error and exit non-zero.
- **Hugging Face returns different schema/version**
  - **Expected**: schema validation fails fast with a message listing missing/renamed columns; do not silently mis-map fields.
- **Partial download / corrupt cache**
  - **Expected**: detect checksum/read errors; purge the specific broken cache entry and retry once; fall back to error if still failing.

#### Data quality issues (common in real datasets)
- **Missing required fields** (name/location/cuisine/rating/cost)
  - **Expected**: impute only when safe (e.g., unknown cuisine → empty list); otherwise drop row and count it in the preprocess report.
- **Rating not numeric** (e.g., `"NEW"`, `"—"`, `"None"`, `"3/5"`)
  - **Expected**: parse common formats; map unparseable values to `null` and exclude from min-rating filter (or treat as failing the constraint—choose one policy and keep it consistent).
- **Cost field mixed types** (string, int, range `"₹500-₹800"`, currency symbols)
  - **Expected**: normalize to a comparable number or bucket; if unparseable, set to `null` and handle in budget filters deterministically.
- **Cuisine field inconsistencies** (comma-separated string, list, weird separators, casing)
  - **Expected**: normalize to `list[str]`, trim whitespace, lowercase, de-duplicate.
- **Location inconsistencies** (city vs neighborhood, spelling variants)
  - **Expected**: normalize via mapping table (e.g., `Bengaluru`↔`Bangalore`) and store both raw and normalized forms.

#### Duplicates and identity
- **Duplicate restaurants** (same name + area, multiple entries)
  - **Expected**: define a stable `restaurant_id` (e.g., hash of normalized key fields) and de-duplicate or keep duplicates but ensure ranking/output doesn’t show identical entries repeatedly.
- **Name collisions** (same name, different locations)
  - **Expected**: include location/area in display to avoid confusion; ensure IDs remain unique.

#### Artifact generation
- **Artifact write fails (permissions/disk full)**
  - **Expected**: fail with actionable error; do not proceed with half-written artifacts.
- **Non-deterministic preprocessing** (random sampling, unstable ordering)
  - **Expected**: enforce stable ordering and fixed seeds; record dataset fingerprint in preprocess report.

---

### Phase 1 edge cases: Input validation + deterministic filtering + fallback policy

#### User input validation
- **Empty input / user hits enter for all prompts**
  - **Expected**: either require minimum inputs (e.g., location) or run a “popular overall” fallback mode (must be explicitly documented).
- **Invalid location** (not in dataset)
  - **Expected**: suggest closest matches (string similarity) and/or show available locations; do not return random city results silently.
- **Budget outside allowed range** (negative, huge, unknown label)
  - **Expected**: reject with message + allowed values; or coerce to nearest bucket (document policy).
- **Cuisine not in dataset**
  - **Expected**: suggest close cuisines; optionally broaden to similar cuisines only if user opts in (or use a deterministic “no matches” response).
- **Minimum rating out of bounds** (<0, >5) or non-numeric
  - **Expected**: reject and request correction; do not default silently unless explicitly designed.
- **Conflicting constraints** (e.g., “high budget” + “cost < 200”)
  - **Expected**: detect conflict and ask the user to choose which constraint to honor (CLI) or provide a clear message (web); if no interaction, pick deterministic precedence (e.g., explicit numeric wins).

#### Filtering semantics
- **Too strict filters → zero candidates**
  - **Expected**: apply fallback broadening in a documented order, e.g.:
    1) relax cuisine (exact → partial → any)
    2) widen budget (strict → adjacent buckets)
    3) relax min rating (step down)
    4) expand location scope (city → nearby/region if supported)
  - Always report what was relaxed (transparency).
- **Too many candidates** (e.g., large city, no constraints)
  - **Expected**: cap to \(K\) candidates for downstream ranking; choose top \(K\) deterministically (e.g., best rating, most-rated, lowest missingness).
- **Missing rating/cost during filtering**
  - **Expected**: define consistent policy:
    - missing rating fails min-rating filter
    - missing cost is allowed but sorted last in budget comparisons

#### Baseline ranking stability
- **Many ties** (same rating/cost)
  - **Expected**: stable tie-breakers (e.g., rating desc → cost asc → name asc → id asc) to ensure reproducible output.
- **Top \(N\) > available candidates**
  - **Expected**: return all candidates and note “only \(M\) matches found”.

---

### Phase 2 edge cases: Prompting + LLM ranking + grounding/validation

#### Prompt construction
- **Prompt exceeds token budget**
  - **Expected**: reduce candidate count \(K\), truncate long fields, or summarize attributes deterministically before calling LLM.
- **Candidates contain unsafe/untrusted text** (prompt injection inside restaurant descriptions/names)
  - **Expected**: treat dataset text as untrusted; delimit candidates; instruct the model to ignore instructions found inside candidate text; strip/escape problematic tokens if necessary.
- **Free-text preferences too long**
  - **Expected**: cap length and preserve the first \(X\) characters; optionally summarize deterministically (not via LLM) before ranking.

#### LLM call failures
- **Timeouts / rate limits / transient 5xx**
  - **Expected**: retry with backoff up to a limit; if still failing, fall back to baseline ranking with a message like “LLM ranking unavailable—showing deterministic ranking.”
- **Authentication missing / invalid API key**
  - **Expected**: fail gracefully; continue with baseline ranking; provide setup guidance.

#### Output parsing + schema validation
- **Model returns non-JSON / malformed JSON**
  - **Expected**: attempt a single “repair” pass (strict) or re-ask with “return valid JSON only”; then fall back to baseline.
- **Model returns restaurant names instead of IDs**
  - **Expected**: map names to IDs only if unambiguous; otherwise fall back.
- **Model returns IDs not in candidate set**
  - **Expected**: drop unknown IDs, log the event, and fill missing ranks using baseline ordering.
- **Model returns fewer than \(N\) items**
  - **Expected**: append remaining from baseline ordering.
- **Model returns duplicates**
  - **Expected**: de-duplicate while preserving order; backfill from baseline.
- **Explanations hallucinate attributes** (e.g., “live music”, “parking” not in data)
  - **Expected**: grounding verifier flags and removes/rewrites explanation (or replaces with a template grounded in known fields); if too many violations, fall back to baseline explanations.

#### Ranking quality pitfalls
- **Model overweights one preference** (e.g., cuisine) and ignores min rating/budget
  - **Expected**: hard constraints are enforced pre-LLM; prompt must state constraints are already applied and remaining ranking should focus on best fit.
- **Model flips ordering across runs** (non-determinism)
  - **Expected**: set temperature low; cache by normalized input; provide deterministic fallback.

---

### Phase 3 edge cases: CLI/Web output + UX

#### CLI-specific
- **Non-interactive environment** (piped input, CI)
  - **Expected**: support flags/env vars; avoid blocking prompts; return non-zero on invalid args.
- **Unicode/encoding issues** (₹, accented names)
  - **Expected**: ensure UTF-8 output; provide ASCII fallback if needed.
- **Terminal width constraints**
  - **Expected**: wrap text; keep explanations short; support `--json` output for automation.

#### Web-specific (if implemented)
- **User refreshes / double-submits**
  - **Expected**: idempotent request handling; disable submit while loading.
- **Slow LLM responses**
  - **Expected**: show progress indicator; consider streaming partial results (baseline first, then LLM-enhanced).
- **Empty states**
  - **Expected**: show why there are no matches and what constraints can be relaxed; never show a blank page.

---

### Phase 4 edge cases: Observability, evaluation, and safety gates

#### Logging and metrics
- **PII leakage in logs** (user free-text can include phone numbers/addresses)
  - **Expected**: sanitize logs; avoid storing raw free-text; store hashes or truncated versions.
- **Metrics cardinality explosion** (logging raw locations/cuisines as labels)
  - **Expected**: aggregate; keep labels bounded; sample logs.

#### Evaluation harness
- **Golden tests become stale after dataset update**
  - **Expected**: pin dataset version/fingerprint for evaluation runs; rebaseline intentionally.
- **Baseline vs LLM comparisons not reproducible**
  - **Expected**: record model/version and decoding params; cache LLM outputs during eval.

#### Quality gates
- **LLM output invalid but still “looks okay”**
  - **Expected**: strict schema checks must win; never bypass validation.
- **Candidate count/token limits exceeded**
  - **Expected**: enforce centrally; never allow a single request to blow up cost.

---

### Phase 5 edge cases: Scalability + caching + retrieval (optional)

#### Indexing/retrieval
- **Index out of sync with dataset artifact**
  - **Expected**: include artifact fingerprint in index metadata; rebuild if mismatch.
- **Vector search returns irrelevant items**
  - **Expected**: keep vector search as a soft signal; still enforce hard constraints.

#### Caching
- **Cache key collisions** (different prefs normalize to same key)
  - **Expected**: include normalized preferences + dataset fingerprint + candidate hash in the cache key.
- **Stale cache after dataset update**
  - **Expected**: invalidate by dataset fingerprint.

---

### Recommended “must test” scenarios (minimal suite)

- **No matches**: location valid but min rating very high and cuisine rare → verify fallback order + messaging.
- **Messy data**: cost/rating missing in many rows → verify filter policy and stable sorting.
- **LLM failure**: force timeout/invalid JSON → verify baseline fallback and no crash.
- **Hallucination check**: model produces explanation with non-existent attributes → verify grounding verifier behavior.
- **Huge candidate set**: large city with no constraints → verify \(K\) cap and deterministic selection.

