# Level 0 Documentation

## Subreddit scoring (business value)
We score each discovered subreddit using a weighted composite:
- Mention frequency (min-max normalized) = 0.35
- Engagement quality (average score + comments, min-max normalized) = 0.30
- Audience size (log-normalized subscribers) = 0.20
- Topic relevance (alias keyword match) = 0.15

This matches the implementation in `backend/app/services/scoring.py`.

## Data collection approach + trade-offs
We use a hybrid Reddit client:
- Primary: Playwright browser scraping against `old.reddit.com` JSON endpoints.
- Fallback: httpx-based API access (OAuth if credentials are provided).

Trade-offs:
- Browser scraping is more resilient without OAuth keys, but it is heavier, slower, and requires Chromium.
- OAuth/httpx is faster and lighter, but requires credentials and has stricter rate limits.

## Entity resolution + confidence
Resolution combines two steps:
- LLM resolution for canonical names and aliases.
- Deterministic normalization (lowercase, strip punctuation/@, remove common company suffixes, collapse spaces) with fuzzy matching.

Match confidence:
- Exact normalized match = 1.0
- Fuzzy match uses similarity thresholds (0.7 to 0.9)

Mention confidence shown in the UI is LLM confidence multiplied by resolution confidence.

## Discovery scope
- Top 20 subreddits are ranked and stored.
- Sources are fetched from the top 5 subreddits for analysis.
