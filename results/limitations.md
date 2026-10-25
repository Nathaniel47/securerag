# Limitations

Written before the full run finished; numbers are added to `results_table.md` by `python -m securerag.eval.report`. These weaknesses are known in advance and do not depend on the results.

1. **Small attack sets.** There are 25 attempts per attack, so a rate has a wide 95% interval (for 0/25 the upper bound is about 13%; for 12/25 it spans roughly 30% to 67%). Differences of a few attempts between two defenses are not evidence of a real difference. Adding attempts is the most direct fix.
2. **My attacks are not adaptive.** Poison and injection documents repeat the target question word for word and use five fixed injection templates. D2 (similarity and near-duplicate checks) and D1's phrase scan are built to catch exactly that, so their scores are likely to be optimistic. A paraphrased or lower-similarity poison, or an injection without trigger phrases, would be a fairer test and was not run.
3. **One answer model.** All main results use `openai/gpt-oss-20b` at low reasoning effort on Groq; one provider and one prompt. The Gemini confirmation run, if it happens, uses a 70-query subset and different limits, so it checks direction, not size.
4. **Questions are only partly human-checked.** 17 of 150 reference answers were spot-checked by the owner and 133 were checked against their source chunk by an AI assistant; none were fully hand-checked. Wikipedia text is a snapshot, so some answers may have changed since the revision used.
5. **The accuracy scorer is automatic and lenient.** It accepts any answer containing all content words of the reference, in any order, and rejects correct answers phrased differently ("8,877" with no percentage). `results/scorer_validation.csv` holds 30 answers for a human verdict; until that is filled in, treat clean accuracy as approximate.
6. **Retrieval, not the model, limits accuracy.** The right chunk is in the top 3 for about 89% of questions, so clean accuracy cannot exceed that without changing retrieval. All configurations share this ceiling.
7. **Synthetic leakage data.** The restricted notes are invented and short, with a consistent format; real records would be messier and harder to both leak and filter. The no-defense baseline deliberately has no access control, so its leakage rate shows the cost of that choice, not a flaw in the model.
8. **D3 is tested on top-3 chunks only.** With three chunks, one half has a single chunk. When both halves contain poison they agree, which is expected to defeat it for the two-document poisons used here.
9. **D5 is a preview model** with a 512-token window and a fixed threshold of 0.5 that was not tuned. It was also not part of the combined configuration.
10. **Latency numbers are unreliable.** Many answers come from the cache, so recorded latencies mostly measure the cache. Cost is reported as extra LLM calls, which is exact.
11. **Wikipedia can be edited by anyone,** so "official" means "trusted base corpus", not verified. The `official_edit` attack channel models exactly that gap.
12. **Free-tier drift.** Model availability and limits changed once already during this project. A rerun on another day may behave differently.

## What would improve the results
More attempts per attack (100+), a paraphrasing attacker for poisoning and injection, a second answer model run in full, a fully human-checked question set, a tuned Prompt Guard threshold, and variance over more than 3 repeats.
