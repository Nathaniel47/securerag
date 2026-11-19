# Deploying SecureRAG to Hugging Face Spaces (Gradio)

The Space runs `app.py` (a Gradio app with Results, Recorded runs and Live playground tabs). The settings Hugging Face reads are in the block at the top of `README.md`. Visitors need no account. Steps marked **(you)** need your own login; everything else is already in the repo.

The Docker Space type is marked Paid on some accounts, so this uses the free Gradio type instead.

## 1. Before you start (you)

1. Log in (or sign up) at https://huggingface.co.
2. Create an access token with **Write** permission: Settings > Access Tokens > New token. Keep it out of the repo and out of chat.
3. If your Groq key was ever shown in a chat or log, rotate it at https://console.groq.com/keys and use the new one.

## 2. Create the Space (you)

1. Go to https://huggingface.co/new-space.
2. Space name: `securerag`. License: any (for example MIT).
3. Space SDK: **Gradio**, template **Blank**.
4. Space hardware: **CPU basic, 2 vCPU, 16 GB, free**.
5. Visibility: **Public**. Click **Create Space**.

## 3. Add the API key as a secret (you)

In the Space, go to **Settings > Variables and secrets > New secret**:

| Name | Value |
|---|---|
| `SECURERAG_GROQ_API_KEY` | your Groq key |

Optional variable (not a secret): `SECURERAG_DAILY_LIVE_LIMIT` (default 50 live questions per UTC day, shared by all visitors). The Gemini key is not needed.

## 4. Push the code (you)

Replace `YOUR_USER` with your Hugging Face username. When Git asks for a password, paste the token from step 1.

```bash
git remote add space https://huggingface.co/spaces/YOUR_USER/securerag
```

```bash
git push space main
```

If Spaces rejects the push because it already created a starter README, use `git push space main --force`. This changes only the Space, not your GitHub repo.

## 5. Wait for the build

The first build takes about 5 to 10 minutes (it installs PyTorch CPU, the embedding model dependencies and Gradio). Watch the **Logs** tab. When the status turns **Running**, open the Space.

## 6. Check it works

1. **Results** shows 1748 finished queries across 7 configurations.
2. **Recorded runs** shows a table with one row per defense for the first example.
3. **Live playground**: open "Ask a question" and press **Ask** with the first example. It answers `Bolgatanga`, usually within a few seconds. If it says the model service is busy, wait a minute and try again.
4. Confirm the Space settings show the secret as hidden, and that the repo has no `.env` file.

Then send the Space URL to Claude so it can be added to `README.md` and `PORTFOLIO.md`.

## 7. Updating later

Make changes, commit, then `git push space main`. The Space rebuilds. Push to GitHub too (`git push`) so both stay in step.

## Notes

- A free Space goes to sleep after inactivity and takes about a minute to wake on the next visit.
- When the daily live limit is reached, or the model service is busy, the Live playground shows a message and points visitors to Recorded runs, which never uses the key.
- To run the same app locally: `python app.py`, then open http://localhost:7860. A Streamlit version (`streamlit run ui/app.py` with `uvicorn api.app:app`) and a `docker compose up --build` setup also exist for local use.
- The text corpus is Wikipedia (CC BY-SA 4.0). Keep the attribution in README.md.
