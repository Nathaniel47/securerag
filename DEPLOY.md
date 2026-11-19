# Deploying SecureRAG to Hugging Face Spaces

The Space runs the `Dockerfile` in this repo: Streamlit on port 7860 (public) and the FastAPI backend on port 8000 (inside the container only). Visitors need no account. Steps marked **(you)** need your own login; everything else is already in the repo.

## 1. Before you start (you)

1. Create a free account at https://huggingface.co/join (skip if you have one).
2. Create an access token with **Write** permission: Settings > Access Tokens > New token. Keep it out of the repo and out of chat.

## 2. Create the Space (you)

1. Go to https://huggingface.co/new-space.
2. Name: `securerag`. SDK: **Docker** > **Blank**. Hardware: **CPU basic (free)**. Visibility: **Public**.
3. Click **Create Space**. It starts empty.

## 3. Add the API key as a secret (you)

In the Space: **Settings > Variables and secrets > New secret**:

| Name | Value |
|---|---|
| `SECURERAG_GROQ_API_KEY` | your Groq key |

Optional variable (not secret): `SECURERAG_DAILY_LIVE_LIMIT` (default 50 live questions per UTC day, shared by all visitors). Leave the Gemini key out; the demo does not use it.

If your Groq key was ever shown in a chat or log, rotate it first at https://console.groq.com/keys and use the new one.

## 4. Push the code (you)

Replace `YOUR_USER` with your Hugging Face username. When Git asks for a password, paste the token from step 1.

```bash
git remote add space https://huggingface.co/spaces/YOUR_USER/securerag
```

```bash
git push space main
```

If Spaces rejects the push as a non-fast-forward (it adds a starter README), use `git push space main --force`. This only changes the Space, not your GitHub repo.

## 5. Wait for the build

The first build takes about 5 to 10 minutes (PyTorch CPU, the embedding model, the app). Watch the **Logs** tab. When the status turns **Running**, open the Space URL.

## 6. Check it works

1. **Results dashboard** shows 1748 finished queries and 7 configurations.
2. **Recorded runs** shows a table with one row per defense.
3. **Live playground**: pick the first example and press Ask. It answers `Bolgatanga` within a few seconds. If it says the API is unreachable, wait a minute for the backend to start and retry.
4. In **Settings > Variables and secrets**, confirm no secret value is shown in plain text, and that the repo contains no `.env` file.

## 7. Updating later

Make changes, commit, then `git push space main`. The Space rebuilds. Push to GitHub too (`git push`) so both stay in step.

## Notes

- A free Space goes to sleep after inactivity and takes about a minute to wake on the next visit.
- When the daily live limit is reached the Live playground shows a message and points visitors to Recorded runs, which never uses the key.
- To run the same container locally: `docker compose up --build`, then open http://localhost:8501 (compose serves the UI on 8501 and the API on 8000).
- The text corpus is Wikipedia (CC BY-SA 4.0). Keep the attribution in README.md.
