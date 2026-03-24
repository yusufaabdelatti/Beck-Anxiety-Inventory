# Beck Anxiety Inventory — Clinical Assessment App

A confidential, clinician-facing web app for administering the **Beck Anxiety Inventory (BAI)** to clients. After submission, an AI-generated clinical PDF report is automatically emailed to the therapist.

---

## Features

- 21-item BAI with a 0–3 severity scale
- AI-generated clinical report via **Groq (LLaMA 3.3 70B)**
- Professional PDF with item-level breakdown and score bar
- Auto-email to therapist with PDF attachment
- Admin portal to browse and download past reports
- Clean, confidential UI — no scores shown to the client

---

## Project Structure

```
├── bai_app.py           # Main Streamlit app
├── requirements.txt     # Python dependencies
├── logo.png             # Your clinic logo (optional)
└── reports/             # Auto-created; stores generated PDFs
```

---

## Setup & Deployment

### 1. Clone the repo

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

### 2. Add your logo (optional)

Place your logo file in the root directory and name it exactly:
```
logo.png
```

### 3. Configure Streamlit Secrets

In **Streamlit Cloud → App Settings → Secrets**, add:

```toml
GROQ_API_KEY = "your_groq_api_key_here"
ADMIN_PASSWORD = "your_admin_password_here"
```

> To get a free Groq API key: https://console.groq.com

### 4. Deploy on Streamlit Cloud

1. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
2. Connect your GitHub repo
3. Set the main file path to `bai_app.py`
4. Add secrets as above
5. Click **Deploy**

---

## Email Configuration

The app sends reports from and to `Wijdan.psyc@gmail.com` using a Gmail App Password.

To update the email address or password, edit these lines at the top of `bai_app.py`:

```python
GMAIL_ADDRESS   = "your_email@gmail.com"
GMAIL_PASSWORD  = "your_app_password"
THERAPIST_EMAIL = "recipient@gmail.com"
```

> **Important:** Use a [Gmail App Password](https://support.google.com/accounts/answer/185833), not your regular Gmail password. 2-Step Verification must be enabled on the account.

---

## Admin Portal

Access the therapist portal by navigating to:

```
https://your-app-url/?page=admin
```

Enter the `ADMIN_PASSWORD` set in your secrets to view and download all submitted reports.

---

## Scoring Reference

| Total Score | Anxiety Level |
|-------------|---------------|
| 0 – 21      | Low Anxiety |
| 22 – 35     | Moderate Anxiety |
| 36 – 63     | Potentially Concerning Levels of Anxiety |

*Reference: Beck, A.T., Epstein, N., Brown, G., & Steer, R.A. (1988). An inventory for measuring clinical anxiety: Psychometric properties. Journal of Consulting and Clinical Psychology, 56, 893–897.*

---

## Confidentiality Notice

All reports are strictly confidential and intended solely for the treating clinician. The client sees only a thank-you screen after submission — no scores or results are displayed to them.

---

## Local Development (optional)

```bash
pip install -r requirements.txt
streamlit run bai_app.py
```

Create a `.streamlit/secrets.toml` file locally:

```toml
GROQ_API_KEY = "your_groq_api_key_here"
ADMIN_PASSWORD = "your_admin_password_here"
```
