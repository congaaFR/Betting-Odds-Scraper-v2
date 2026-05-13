import os
import json
import gspread
import pandas as pd
import re
import time
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager

# ============================================
# 1. CONFIGURATION
# ============================================
SPREADSHEET_ID = "16ZBhF4k4ah-zhc3QcH7IEWLXrhbT8TRTMi5BptCFIcM"
# URLs to scrape automatically (you can add more)
FOOTBALL_URLS = [
    "https://www.coteur.com/cotes/football/europe/ligue-des-champions"
]
BOOKMAKERS = ["Winamax", "Unibet", "Betclic", "Pmu", "Betsson", "Vbet"]

# ============================================
# 2. GOOGLE SHEETS CONNECTION
# ============================================
def _authorize_gsheets():
    """Silent connection via GitHub Actions secrets"""
    creds_json_str = os.environ.get("GOOGLE_SHEET_CREDENTIALS")
    if not creds_json_str:
        raise RuntimeError("Secret GOOGLE_SHEET_CREDENTIALS not found!")
    
    credentials_dict = json.loads(creds_json_str)
    credentials = Credentials.from_service_account_info(
        credentials_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(credentials)

def write_to_sheet(df, tab_name):
    """Writes raw data to a specific tab"""
    if df.empty:
        print(f"Nothing to write for {tab_name}.")
        return
        
    client = _authorize_gsheets()
    sheet = client.open_by_key(SPREADSHEET_ID)
    
    # Check if the tab exists, otherwise create it
    try:
        worksheet = sheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=tab_name, rows="1000", cols="20")
    
    # Clear the tab and paste the new data
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    print(f"✅ Data successfully written to tab '{tab_name}'!")

# ============================================
# 3. THE SCRAPER (Invisible version)
# ============================================
def init_driver():
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    firefox_options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/120.0")
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-dev-shm-usage")
    
    service = Service(GeckoDriverManager().install())
    return webdriver.Firefox(service=service, options=firefox_options)

def get_match_odds(competition_url):
    driver = init_driver()
    driver.get(competition_url)
    
    match_links = []
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "match-row")))
        anchors = driver.find_elements(By.CSS_SELECTOR, ".match-row a[href*='/cote/']")
        for a in anchors:
            match_links.append(a.get_attribute("href"))
    except:
        driver.quit()
        return pd.DataFrame()
    
    match_links = list(dict.fromkeys(match_links))[:10] # Get the first 10 matches
    all_odds = []
    
    bookmaker_map = {"20": "Unibet", "21": "Pmu", "24": "Betclic", "33": "Winamax", "37": "Vbet", "43": "Betsson"}
    
    for match_url in match_links:
        driver.get(match_url)
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr td.ps-4")))
            time.sleep(1)
        except:
            continue
        
        odds_script = '''
        let results = [];
        document.querySelectorAll("tbody tr").forEach(row => {
            let bookLink = row.querySelector("td.ps-4 a[href*='/bookmaker/']");
            let cells = row.querySelectorAll("td.text-center");
            if (bookLink && cells.length >= 2) {
                let bookId = bookLink.getAttribute("href").split("/").pop();
                let odds = Array.from(cells).map(c => c.innerText.trim()).filter(txt => /^[0-9.,]+$/.test(txt));
                results.push({id: bookId, odds: odds});
            }
        });
        return results;
        '''
        
        raw_data = driver.execute_script(odds_script)
        raw_name = match_url.split("/")[-1].replace("-", " ").title()
        match_name = re.sub(r'\s*\d+$', '', raw_name).strip()
        
        for item in raw_data:
            b_name = bookmaker_map.get(item['id'])
            if not b_name or b_name not in BOOKMAKERS:
                continue
            try:
                odds_values = [float(v.replace(',', '.')) for v in item['odds'] if v]
                if len(odds_values) < 3: continue
                
                # Here is where your code calculates the Payout (TRJ)!
                inv_sum = sum(1 / val for val in odds_values[:3])
                payout_val = round((1 / inv_sum) * 100, 2)
                
                all_odds.append([match_name, b_name, odds_values[0], odds_values[1], odds_values[2], payout_val])
            except:
                continue
                
    driver.quit()
    return pd.DataFrame(all_odds, columns=["Match", "Bookmaker", "1", "Draw", "2", "Payout"])

# ============================================
# 4. SCRIPT EXECUTION
# ============================================
if __name__ == "__main__":
    print("Starting the scraper bot...")
    df_final = pd.DataFrame()
    
    for url in FOOTBALL_URLS:
        print(f"Scraping in progress: {url}")
        df = get_match_odds(url)
        df_final = pd.concat([df_final, df], ignore_index=True)
        
    # Write everything to a tab named "Raw_Football_Data"
    write_to_sheet(df_final, "Raw_Football_Data")
    print("Finished!")