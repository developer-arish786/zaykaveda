# Zaykaveda — Restaurant Website (Indian + Chinese)

Front end (HTML/CSS/JS) → **GitHub Pages** (free). Back end (Python + SQL) → **PythonAnywhere** (free).
Payments → **plain UPI** (QR + UPI link, owner approves manually). No payment gateway, no fees.

> Why two hosts? GitHub Pages can only serve static files; it cannot run Python or a database.
> So the pages live on GitHub Pages and talk to the Python API on PythonAnywhere.

## Folder layout
```
zaykaveda/
  index.html menu.html checkout.html about.html contact.html
  admin/index.html          <- owner panel  (yourlink/admin/)
  assets/ style.css app.js config.js
  backend/ app.py requirements.txt   <- Flask + SQLite (SQL)
```

---
## PART 1 — Test on your computer (10 min)
1. Install Python 3.10+.
2. In a terminal:
   ```
   cd zaykaveda/backend
   pip install -r requirements.txt
   set ADMIN_PASSWORD=MyStrongPass123      (Windows)   |   export ADMIN_PASSWORD=MyStrongPass123  (Mac/Linux)
   set UPI_ID=yourupi@bank                 |   export UPI_ID=yourupi@bank
   python app.py
   ```
3. In a second terminal: `cd zaykaveda` then `python -m http.server 8000`
4. Open http://localhost:8000 . Admin: http://localhost:8000/admin/

## PART 2 — Deploy the Python backend (free, PythonAnywhere)
1. Sign up free at pythonanywhere.com. Choose a username (your API will be `https://USERNAME.pythonanywhere.com`).
2. **Files** tab → upload `app.py` and `requirements.txt` into `/home/USERNAME/zaykaveda/`.
3. **Consoles** → Bash:
   `pip install --user flask flask-cors`
4. **Web** tab → *Add a new web app* → *Manual configuration* → Python 3.10+.
5. On the Web tab, open the **WSGI configuration file** and replace everything with:
   ```python
   import os, sys
   sys.path.insert(0, "/home/USERNAME/zaykaveda")
   os.environ["ADMIN_PASSWORD"] = "choose-a-strong-password"
   os.environ["UPI_ID"] = "yourupi@bank"
   os.environ["UPI_NAME"] = "Zaykaveda"
   os.environ["WHATSAPP_NUMBER"] = "919669219030"
   os.environ["ALLOWED_ORIGIN"] = "https://YOURGITHUBNAME.github.io"
   os.environ["DB_PATH"] = "/home/USERNAME/zaykaveda/zaykaveda.db"
   from app import app as application
   ```
6. Click **Reload**. Visit `https://USERNAME.pythonanywhere.com/api/health` → you should see `{"ok":true}`.
7. Free accounts must click "Run until 3 months from today" on the Web tab every ~3 months. Set a reminder.

## PART 3 — Put the website on GitHub Pages
**The link must match the name.** GitHub gives you `https://<account-name>.github.io`, so the *account name* becomes your link.

1. Create a GitHub account (github.com/signup) with the username **`zaykaveda`**
   (if taken, try `zaykaveda-kitchen`; then your link is `https://zaykaveda-kitchen.github.io`).
   *Best check first:* open `https://github.com/zaykaveda` — a "404" means it is free.
2. Click **+ → New repository**. Name it exactly **`zaykaveda.github.io`** (i.e. `<account>.github.io`), set **Public**, tick *Add a README*, Create.
3. Edit `assets/config.js` and set `API_URL` to your PythonAnywhere URL (no trailing slash).
4. In the repo click **Add file → Upload files**, drag in **everything inside the `zaykaveda` folder except `backend/`**
   (`index.html`, `menu.html`, `checkout.html`, `about.html`, `contact.html`, `admin/`, `assets/`). Commit.
5. **Settings → Pages** → Source: *Deploy from a branch* → Branch: `main`, folder `/ (root)` → Save.
6. Wait 1–2 minutes. Your site: **https://zaykaveda.github.io**  (admin: `/admin/`).
   Links work with no interruption, no ads, no "redirect" screen.

Optional: a custom domain like `zaykaveda.in` costs ~₹700/yr; free `github.io` works fine without it.

## PART 4 — First-time owner checklist
1. Open `/admin/`, sign in with `ADMIN_PASSWORD`, then **Settings** → set your real **UPI ID**, confirm WhatsApp number, and change the password.
2. **Menu & prices**: edit prices, hide/remove dishes, add new ones.
3. **Staff & salary**: replace the two sample staff.
4. Place a test order from the site, pay ₹1 yourself if you like, then **Payments → Approve**.

## How payment works (free, no gateway)
1. Customer places order → sees a UPI QR/link for the exact amount (pays straight to *your* UPI ID).
2. Customer enters the UTR / reference number and submits.
3. You check your UPI app/bank SMS → **Approve** (order confirmed) or **Deny** (not received → order cancelled).
The customer's page updates by itself.
Note: this is manual verification, so approval is only as accurate as your check. Always match amount + UTR.

## Security notes
* Never put your password in GitHub. It lives only in the PythonAnywhere WSGI file.
* Prices are always re-read from the database on the server, so customers cannot edit prices.
* Free PythonAnywhere keeps the SQLite file safely; download `zaykaveda.db` now and then as a backup.

## Name uniqueness
"Zaykaveda" returned no restaurant or business in my web searches (only the similar words "Zayka"/"Zaykara"). No one can guarantee global uniqueness, so before launch:
search Google for "Zaykaveda", check `github.com/zaykaveda`, and (for legal protection) search the Indian Trade Marks registry (ipindiaservices.gov.in) and register a trademark if you wish.
