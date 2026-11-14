# Put it online (no computer needed for your brother)

You do this once. After that your brother just opens a link on his phone or tablet.

## 1. Free AI key (2 minutes)
1. Open https://aistudio.google.com/apikey and sign in with Google.
2. Press **Create API key** and copy it.
3. Optional backup: a free key from https://console.groq.com/keys.

## 2. Host the API on Render
1. Sign up at https://render.com with your GitHub account.
2. **New > Blueprint**, pick `VishnuDurgam/fmge-agentic-tutor`, press **Apply**.
3. When asked, paste `GEMINI_API_KEY` (and `GROQ_API_KEY` if you have one).
4. Wait for the first build (10-15 minutes, it downloads the open textbooks).
5. Copy the service URL, like `https://fmge-api.onrender.com`. Opening `/health` on it should show `{"ok":true,...}`.

## 3. Host the website on Vercel
1. Sign up at https://vercel.com with GitHub, press **Add New > Project**, pick the repo.
2. Set **Root Directory** to `apps/web`.
3. Under Environment Variables add `NEXT_PUBLIC_API_URL` = the Render URL from step 2 (no trailing slash).
4. Press **Deploy**. You get a link like `https://fmge-tutor.vercel.app`.

## 4. Allow the website to talk to the API
In Render, open the service > Environment, set `CORS_ORIGINS` to your Vercel link, and save (it restarts).
Optional: set `APP_PASSCODE` to a secret word so only people you give it to can use the app.

## 5. Install it on the phone or tablet
- Android (Chrome): open the link, tap the menu (three dots), **Add to Home screen** or **Install app**.
- iPhone/iPad (Safari): open the link, tap **Share**, then **Add to Home Screen**.
It then opens full screen like a normal app. Then he opens **My material** and uploads his PDFs, photos or links.

## Things to know
- Free Render goes to sleep after 15 minutes idle. The first open then takes about a minute.
- Free Render wipes its disk on restart, so uploaded material and progress can disappear. Switch the plan to Starter (about 7 USD per month) and uncomment `disk` in `render.yaml` to keep them.
- Free AI keys have daily limits. If answers stop, wait or add the second key.
- A native Android/iOS app file is not needed. The installed website does the same job. A store app needs a computer and developer accounts.
