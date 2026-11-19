# Portfolio card: SecureRAG

**SecureRAG: attacking and defending a RAG assistant**

Retrieval-augmented assistants answer from documents they fetch at question time, which means anyone who can plant text in those documents can steer the answer. SecureRAG is a small, fully reproducible testbed for that problem. It runs a question-answering assistant over about 400 Ghana-related Wikipedia articles, then attacks it four ways: knowledge-base poisoning, indirect and direct prompt injection, and leakage of synthetic restricted records. Five separate defenses plug into the pipeline. With no defense, 60% of 100 attacks succeed. Four defenses combined cut that to 6%, with no false blocks on 150 clean questions. Scoring is automatic, with no LLM judge, and every rate carries a 95% interval. Built in plain Python with Chroma, FastAPI and Streamlit.

Tags: LLM security, RAG, prompt injection, evaluation
Links: GitHub (Nathaniel47/securerag) | Live demo (add the Hugging Face Space link) | Write-up (docs/writeup.md)

## One sentence for emailing researchers

I built SecureRAG, an open testbed that measures how knowledge-base poisoning, indirect prompt injection, and data leakage succeed against a retrieval-augmented assistant with and without modular defenses (60% of attacks succeed undefended and 6% with four defenses combined), and I found that a source-trust label itself became the weak point when poison arrived as an "official" edit, which is the same trust-boundary problem that arises when an agent's memory is written by untrusted content.

Tailoring: for memory-poisoning work (Linköping) lead with the "official edit" finding; for multi-agent security (Miami) lead with the trust-boundary point; for an AI security lab (Guelph) lead with the measurement method (automatic scoring, Wilson intervals, no LLM judge); for agentic AI (Exeter) say what you would test next, which is adaptive attacks and persistent memory.
