## Problem statement: AI-powered restaurant recommendations (Zomato dataset)

Related: see the phase plan and component breakdown in `docs/architecture.md`.

### What we’re building
Build an application that returns a **ranked shortlist of restaurants** based on a user’s preferences. The system combines:
- **Structured filtering** (hard constraints from the dataset), and
- **LLM-assisted ranking + explanations** (to handle nuance and produce user-friendly rationale).

The result should feel like a lightweight “Zomato-style” recommender: fast, relevant, and easy to understand.

### Why this problem exists
Restaurant datasets are large and messy (inconsistent cuisine tags, missing fields, noisy ratings). Users also express preferences that aren’t purely numeric (“family-friendly”, “quick service”, “good for groups”). A simple sort-by-rating or cost filter is usually not enough to produce satisfying recommendations.

### Primary user story
As a user, I want to provide my dining preferences (location, budget, cuisine, minimum rating, and optional constraints) and receive a small set of restaurants that:
- match my **hard constraints**, and
- are ordered by **best overall fit**, with short explanations.

### Functional requirements
- **Input collection**
  - The **basic web UI** is the primary source of user input (CLI can exist as a secondary/debug interface).
  - Location (e.g., Delhi, Bangalore)
  - Budget (e.g., low / medium / high, or a cost range if available)
  - Cuisine (one or more)
  - Minimum rating
  - Optional free-text preferences (e.g., family-friendly, quick service)
- **Data ingestion**
  - Load and preprocess the dataset from Hugging Face: `https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation`
  - Extract/normalize core fields (name, city/location, cuisine(s), rating, estimated cost, and any useful metadata)
- **Candidate generation (deterministic)**
  - Apply hard filters (location, min rating, budget band, cuisine match)
  - Produce a bounded candidate set suitable for prompting (to control latency and tokens)
- **Ranking + explanation (LLM-assisted)**
  - Construct a prompt that includes user preferences + structured candidates
  - Produce:
    - a ranked top \(N\) list
    - a short, grounded explanation per recommendation (tied to known attributes)
- **Output formatting**
  - Show results consistently (CLI and/or web), including:
    - Restaurant name
    - Cuisine
    - Rating
    - Estimated cost / budget indicator
    - Explanation

### Non-functional requirements
- **Determinism where it matters**: filtering should be reproducible; LLM output should be constrained to a stable schema.
- **Graceful fallback**: if strict filters return too few results, broaden in a predictable order (or explain why no matches exist).
- **Grounded explanations**: do not invent attributes not present in the dataset/candidate payload.
- **Efficiency**: limit candidate count and keep prompts compact to control runtime and cost.

### Scope (v1)
- Single request → recommendations (no user accounts, no long-term personalization).
- Dataset-based results only (no live web search/scraping).
- Preference handling supports both structured inputs and optional free-text constraints.

### Non-goals (v1)
- Real-time availability, table booking, delivery ETA, or dynamic pricing.
- Learning from implicit feedback over time (clicks, saves) beyond the current request.

### Success criteria
- **Constraint satisfaction**: results respect location / budget / min rating / cuisine constraints when possible.
- **Quality vs baseline**: users prefer the top results over a simple “sort by rating” or “closest cost match” baseline.
- **Clarity**: explanations are brief, specific, and traceable to candidate attributes.

### High-level workflow (implementation outline)
1. Load + preprocess dataset
2. Collect user preferences
3. Filter to candidates (hard constraints)
4. Prompt LLM to rank + explain (schema-constrained)
5. Render top \(N\) results (CLI/web)
