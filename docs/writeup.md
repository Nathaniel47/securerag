# SecureRAG: measuring attacks on, and defenses for, a small RAG assistant

## 1. Problem

A retrieval-augmented generation (RAG) assistant answers a question by first fetching passages from a document store and putting them into the prompt. That makes the document store part of the attack surface. Anyone who can add or edit a document can change what the model says, and anyone who can type a question can try to talk the model out of its rules. The OWASP Top 10 for LLM Applications names the relevant risks: prompt injection (LLM01), sensitive information disclosure (LLM02) and vector and embedding weaknesses (LLM08).

This project asks a narrow, measurable question: on one small assistant, how often do four well-known attacks succeed, and how much does each of several simple defenses reduce that, at what cost to normal use? The aim is a reproducible testbed, not a state-of-the-art defense.

## 2. Method

**System.** The assistant answers from about 400 English Wikipedia articles on Ghana (2,330 chunks). Each chunk is embedded with MiniLM-L6-v2 and stored in Chroma. A question retrieves the top 3 chunks by cosine similarity, each trimmed to 600 characters, and `openai/gpt-oss-20b` on Groq answers (reasoning effort low, temperature 0.3, seed 42). The pipeline is plain Python, and each defense is a separate class that overrides one of five hooks: accepting a document, checking the query, filtering retrieved chunks, generating, and filtering the answer. A defense can therefore be switched on alone or in combination.

**Data.** 150 clean questions were generated from the corpus, each with a short reference answer. Seventeen answers were spot-checked by the project owner and the other 133 were verified against their source passage by an AI assistant; none was fully hand-checked. Ghanaian-style synthetic "restricted" case notes (40, with invented names and IDs marked `FAKE`) support the leakage tests. No real personal data is used.

**Attacks (25 attempts each, 100 in total).**
- *Poisoning* (PoisonedRAG style): planted documents repeat the target question and state a wrong answer.
- *Indirect injection*: planted documents carry instructions the model may follow.
- *Direct injection*: a user message overrides the rules or asks for the system prompt, which holds a canary string.
- *Leakage*: questions that ask for the synthetic restricted records.

Poisoning and indirect injection arrive through two channels, a user upload (15 attempts) and an edit to an "official" page (10). All attacks target this application only.

**Defenses.**
- D1, source filter: rejects untrusted uploads and any text that contains instruction phrases.
- D2, retrieval anomaly: drops a chunk that contains instruction text, matches the question at cosine 0.85 or higher, or nearly duplicates another chunk (0.915 or higher). The thresholds come from the 150 clean questions.
- D3, consistency: answers from two disjoint halves of the evidence and abstains on disagreement. It costs a second model call.
- D4, output filter: blocks answers that contain the canary, personal-data patterns, or five-word runs of the system prompt.
- D5, Prompt Guard: scores the query with Meta's Prompt Guard 2. It was added after the plan froze and is not part of "combined".
- Combined means D1 to D4 together.

**Scoring.** Everything is automatic. An attack succeeds when a whole-word success marker appears in the answer and a "must not contain" check does not fire. A clean answer is correct when every content word of the reference (or an alias) is present. There is no LLM judge. Rates carry 95% Wilson intervals, because 25 attempts is a small sample. A 30-answer hand check of the accuracy scorer agreed with it on 27 (90%); the three disagreements are explained in `results/limitations.md`. Seeds, model IDs and the commit are recorded in `results/run_meta.json`.

## 3. Results

All numbers come from `results/results_table.md` (1,748 of 1,750 planned queries; two d5 items exceed Groq's context limit and always fail). Intervals are 95% Wilson.

| Configuration | Attacks succeeding (n=100) | Clean accuracy (n=150) | False blocks | Model calls per query |
|---|---|---|---|---|
| none | 60% [50%-69%] | 55% | 0 | 1.00 |
| D1 source filter | 16% [10%-24%] | 55% | 0 | 1.00 |
| D2 retrieval anomaly | 9% [5%-16%] | 55% | 0 | 1.00 |
| D3 consistency | 58% [48%-67%] | 59% | 0 | 2.00 |
| D4 output filter | 35% [26%-45%] | 55% | 0 | 1.00 |
| D5 Prompt Guard | 52% [42%-61%] | 54% | 0 | 0.94 (+3.81 guard calls) |
| D1 to D4 combined | 6% [3%-12%] | 59% | 0 | 1.96 |

**Per attack, with no defense:** leakage 100% (25/25), poisoning 68% (17/25), indirect injection 36% (9/25), direct injection 36% (9/25).

**What each defense does.**
- D2 removed every planted document in poisoning and indirect injection (0/25 for each) and was the strongest single defense, but it does not touch direct injection (still 36%).
- D4 is the leakage defense (100% down to 12%) and also lowers direct injection (36% down to 24%), but it does nothing about poisoning.
- D1 stops injection and leakage entirely (0/25 each) but let 7 of 10 poisonings through when they arrived as official edits, because the "official" trust label was itself what the attacker used.
- D3 barely helped (58%) and doubled the cost. When both retrieved halves contain a poison, the halves agree, which defeats the idea.
- D5 mainly helped direct injection (36% to 12%), had little effect elsewhere, and its extra guard calls add cost.
- Combined leaves 6 successes, all direct injection (24% of that attack).

**Variance.** Three repeat runs on a 70-query subset gave an attack success mean of 59.2% (sd 2.9) with no defense, 5.8% (sd 1.4) for D2 and 5.0% (sd 0.0) for combined. The model's own sampling noise is therefore small next to the sampling error from using only 25 attempts per attack.

**Second model.** A confirmation run on Gemini over the same 70-query subset points the same way: 19/40 attacks succeeded with no defense, 7 with D1, 4 with D2, 21 with D3, 11 with D4, 17 with D5 and 2 combined. Accuracy was 20/30 in most configurations. This checks direction only, not size, since it uses 40 attacks and different limits.

## 4. Limitations

- **Small attack sets.** With 25 attempts, a rate of 0/25 still allows a true rate near 13%, and many differences between defenses are within the intervals.
- **Non-adaptive attacks.** Poisons repeat the question word for word and injections use five fixed templates. D1's phrase scan and D2's similarity checks are built to catch exactly that, so their scores are optimistic. A paraphrased poison or an injection with no trigger phrase would be a fairer test, and it was not run.
- **One answer model** for the main results, and a lenient scorer that was hand-checked on only 30 answers.
- **Partly human-checked questions:** 17 of 150 by the owner, the rest by an AI assistant.
- **Low base accuracy (55%).** Retrieval puts the right chunk in the top 3 for about 89% of questions, and the model is small. Defense effects are measured relative to this baseline.
- **Synthetic leakage data.** The restricted notes are short and uniform, so real records would be messier. The baseline has no access control by design, so 100% leakage shows the cost of that choice and not a model flaw.

## 5. Lessons learned

1. **Where a defense sits matters more than how clever it is.** Cheap checks at retrieval time (D1, D2) beat a more expensive consistency check (D3) against these attacks, and an output filter (D4) was the only thing that handled leakage.
2. **A trust label is an attack surface.** D1 trusted pages marked "official", and the attacker simply planted poison there. Provenance has to be verified, not assumed.
3. **Measure the cost of defending.** Counting false blocks, false flags and calls per query separates a defense that helps from one that refuses everything (which also scores 0% attack success).
4. **Be honest about scope.** The best result here (6%) depends on attacks that the defenses were tuned against. The numbers support "these defenses stop these attacks", not "RAG is now secure".
5. **Engineering detail decides evaluations.** A leaked API key in test output, a client closed mid-request and Excel rewriting "January 7" into "Jan-07" all affected the project, and each was caught only by looking at real outputs.

## 6. Reproducing this

Code, data manifest, per-query records (`results/runs/`) and the report generator are in the repository. `README.md` lists the commands; the full run needs a free Groq key and spans several days because of the daily limit.

*Text corpus: English Wikipedia, CC BY-SA 4.0. Article titles, URLs and revision ids are in `data/manifest.jsonl`.*
