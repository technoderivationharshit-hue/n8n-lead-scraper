import os
import json
import requests
import re
import openai
import gspread
from google.oauth2.service_account import Credentials

# --- Load environment variables from GitHub Secrets ---
APIFY_API_KEY = os.getenv("APIFY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SERVICE_ACCOUNT = os.getenv("GOOGLE_SERVICE_ACCOUNT")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

openai.api_key = OPENAI_API_KEY

# --- Google Sheets setup ---
creds = Credentials.from_service_account_info(
    json.loads(GOOGLE_SERVICE_ACCOUNT),
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gs = gspread.authorize(creds)
sheet = gs.open_by_key(GOOGLE_SHEET_ID).sheet1


# --- AI Email Extractor ---
def extract_email(text):
    # Use regex first
    regex_emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    if regex_emails:
        return regex_emails[0]

    # Fall back to AI extraction
    prompt = f"Extract the email from this text ONLY if it is a valid email:\n{text}\n\nEmail:"
    msg = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    email = msg["choices"][0]["message"]["content"].strip()
    return email if "@" in email else ""


# --- Scrape using Apify ---
def scrape_leads():
    print("Launching Apify actor...")
    url = "https://api.apify.com/v2/acts/apify~website-scraper/run-sync"
    payload = {
        "startUrls": [{"url": "https://example.com"}],   # CHANGE to your target
        "includeScreenshot": False,
        "maxConcurrency": 3
    }

    response = requests.post(
        url,
        params={"token": APIFY_API_KEY},
        json=payload
    )

    if response.status_code != 200:
        print("Error:", response.text)
        return []

    run_data = response.json()
    dataset_id = run_data["defaultDatasetId"]

    # Get dataset items
    dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?clean=true"
    items = requests.get(dataset_url).json()
    return items


# --- Main ---
def main():
    leads = scrape_leads()

    for lead in leads:
        title = lead.get("title", "")
        url = lead.get("url", "")
        text = lead.get("text", "")

        email = extract_email(text)

        row = [title, url, email]
        sheet.append_row(row)
        print("Added:", row)


if __name__ == "__main__":
    main()
