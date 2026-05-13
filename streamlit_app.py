# Betting Odds Scraper - Single Production App
# Complete solution with favorites, colored table, and copy-paste ready

import streamlit as st
import gspread
import pandas as pd
import re
import time
from typing import List
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager


# ============================================
# SELENIUM DRIVER INITIALIZATION
# ============================================
def init_driver(headless: bool = True):
    """Initialize Firefox WebDriver with anti-detection headers."""
    firefox_options = Options()
    if headless:
        firefox_options.add_argument("--headless")
    
    firefox_options.set_preference("general.useragent.override",
                                   "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0")
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-dev-shm-usage")
    
    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=firefox_options)
    return driver


# ============================================
# GOOGLE SHEETS AUTHORIZATION
# ============================================
def _authorize_gsheets():
    """Create authorized gspread client from Streamlit secrets."""
    credentials_dict = st.secrets.get("GOOGLE_SHEET_CREDENTIALS")
    if not credentials_dict:
        raise RuntimeError("Missing GOOGLE_SHEET_CREDENTIALS in st.secrets.")
    credentials = Credentials.from_service_account_info(
        credentials_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(credentials)


def get_competitions_from_sheets(sheet_name: str,
                                 spreadsheet_id: str = "16ZBhF4k4ah-zhc3QcH7IEWLXrhbT8TRTMi5BptCFIcM") -> pd.DataFrame:
    """Retrieve competitions from Google Sheet with Favorite column."""
    client = _authorize_gsheets()
    try:
        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    except Exception as e:
        st.error(f"Unable to open worksheet '{sheet_name}': {e}")
        return pd.DataFrame()
    
    data = sheet.get_all_records()
    competitions_df = pd.DataFrame(data)
    
    required_columns = {"Country", "Competition", "URL"}
    if not required_columns.issubset(set(competitions_df.columns)):
        st.error(f"❌ Sheet must contain columns: {required_columns}")
        return pd.DataFrame()
    
    # Sort with France first, then alphabetically
    competitions_df = competitions_df.sort_values(
        by=["Country", "Competition"],
        key=lambda x: x.map(lambda y: ("" if str(y).strip() == "France" else str(y)))
    ).reset_index(drop=True)
    
    return competitions_df


# ============================================
# ODDS SCRAPING
# ============================================
def get_match_odds(
        competition_url: str,
        selected_bookmakers: List[str],
        nb_matches: int = 5,
        outcomes_count: int = 3,
        headless: bool = True
) -> pd.DataFrame:
    """Scrape odds from competition URL."""
    driver = init_driver(headless=headless)
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
    
    match_links = list(dict.fromkeys(match_links))[:nb_matches]
    all_odds = []
    
    bookmaker_map = {
        "20": "Unibet", "21": "Pmu", "22": "ParionsSport", "24": "Betclic",
        "32": "Genybet", "33": "Winamax", "37": "Vbet", "43": "Betsson", "44": "Olybet"
    }
    
    for match_url in match_links:
        driver.get(match_url)
        
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr td.ps-4"))
            )
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
                let odds = Array.from(cells)
                                 .map(c => c.innerText.trim())
                                 .filter(txt => /^[0-9.,]+$/.test(txt));
                results.push({id: bookId, odds: odds});
            }
        });
        return results;
        '''
        
        raw_data = driver.execute_script(odds_script)
        
        raw_name = match_url.split("/")[-1].replace("-", " ").title()
        match_name = re.sub(r'\s*\d+$', '', raw_name).strip()
        
        for item in raw_data:
            b_name = bookmaker_map.get(item['id'], f"ID_{item['id']}")
            if b_name not in selected_bookmakers:
                continue
            
            try:
                odds_values = [float(v.replace(',', '.')) for v in item['odds'] if v]
                if len(odds_values) < outcomes_count:
                    continue
                
                inv_sum = sum(1 / val for val in odds_values[:outcomes_count])
                payout_val = round((1 / inv_sum) * 100, 2)
                
                if outcomes_count == 3:
                    all_odds.append([match_name, b_name, odds_values[0], odds_values[1], odds_values[2], payout_val])
                else:
                    all_odds.append([match_name, b_name, odds_values[0], odds_values[-1], payout_val])
            except:
                continue
    
    driver.quit()
    cols = ["Match", "Bookmaker", "1", "Draw", "2", "Payout"] if outcomes_count == 3 else ["Match", "Bookmaker", "1", "2", "Payout"]
    return pd.DataFrame(all_odds, columns=cols)


# ============================================
# TABLE FORMATTING FOR COPY-PASTE
# ============================================
def format_table_for_copy_paste(df: pd.DataFrame, outcomes_count: int = 3) -> pd.DataFrame:
    """Format table with fixed bookmaker order and empty cells."""
    if df.empty:
        return pd.DataFrame()
    
    bookmaker_order = ["Winamax", "Unibet", "Betclic", "Pmu", "Betsson"]
    df = df.copy()
    matches = df["Match"].unique()
    formatted_data = []
    
    for match in matches:
        match_data = df[df["Match"] == match]
        
        for bookmaker in bookmaker_order:
            book_row = match_data[match_data["Bookmaker"] == bookmaker]
            
            if book_row.empty:
                if outcomes_count == 3:
                    formatted_data.append([match, bookmaker, "", "", "", ""])
                else:
                    formatted_data.append([match, bookmaker, "", "", ""])
            else:
                row = book_row.iloc[0]
                if outcomes_count == 3:
                    formatted_data.append([
                        match, bookmaker, 
                        row["1"], row["Draw"], row["2"], 
                        row["Payout"]
                    ])
                else:
                    formatted_data.append([
                        match, bookmaker, 
                        row["1"], row["2"], 
                        row["Payout"]
                    ])
    
    cols = ["Match", "Bookmaker", "1", "Draw", "2", "Payout"] if outcomes_count == 3 else ["Match", "Bookmaker", "1", "2", "Payout"]
    return pd.DataFrame(formatted_data, columns=cols)


def display_colored_table(df: pd.DataFrame):
    """Display table with bookmaker colors using Streamlit columns."""
    if df.empty:
        st.info("No data to display.")
        return
    
    # Bookmaker colors mapping
    colors = {
        "Winamax": "#DC143C",    # Crimson Red
        "Unibet": "#FFD700",      # Gold
        "Betclic": "#32CD32",     # Lime Green
        "Pmu": "#4169E1",         # Royal Blue
        "Betsson": "#FF8C00"      # Dark Orange
    }
    
    # Group by match
    matches = df["Match"].unique()
    
    for match in matches:
        match_data = df[df["Match"] == match].reset_index(drop=True)
        
        st.subheader(f"📌 {match}")
        
        # Display each bookmaker with color
        for _, row in match_data.iterrows():
            bookmaker = row["Bookmaker"]
            color = colors.get(bookmaker, "#CCCCCC")
            
            # Build display text
            if "Draw" in row.index:
                # 3-way odds
                odds_text = f"{row['1']} | {row['Draw']} | {row['2']}"
            else:
                # 2-way odds
                odds_text = f"{row['1']} | {row['2']}"
            
            payout_text = f"{row['Payout']}"
            
            # Display with HTML for color
            display_html = f"""
            <div style="background-color: {color}; padding: 12px; border-radius: 5px; margin-bottom: 8px; text-align: center;">
                <h4 style="color: white; margin: 0; font-weight: bold;">{bookmaker}</h4>
                <p style="color: white; margin: 5px 0; font-size: 14px;">{odds_text}</p>
                <p style="color: white; margin: 0; font-size: 12px; opacity: 0.9;">Payout: {payout_text}</p>
            </div>
            """
            st.markdown(display_html, unsafe_allow_html=True)


def display_copy_paste_table(df: pd.DataFrame, outcomes_count: int = 3):
    """Display clean table ready for copy-paste."""
    if df.empty:
        st.info("No data to display.")
        return
    
    # Display raw dataframe for copy-paste
    st.write("**Copy-paste this table directly to Google Sheets:**")
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Also show as CSV for easier copying
    csv_text = df.to_csv(index=False, sep="\t")
    st.text_area(
        "Or copy from here (Tab-separated):",
        csv_text,
        height=150,
        disabled=True
    )


# ============================================
# MAIN APPLICATION
# ============================================
def main():
    st.set_page_config(page_title="Betting Odds Scraper", layout="wide")
    st.sidebar.title("📌 Menu")
    
    view_mode = st.sidebar.radio(
        "Display Mode",
        ["🎨 Colored View", "📋 Copy-Paste View"]
    )
    
    menu_selection = st.sidebar.radio(
        "Choose a sport",
        ["🏠 Home", "⚽ Football", "🎾 Tennis"]
    )
    
    if menu_selection == "🏠 Home":
        st.title("Betting Odds Scraper 🏠")
        st.markdown("""
        ### How it works:
        1. **Select your favorite competitions** (marked with ⭐)
        2. **Choose bookmakers** (default: Winamax, Unibet, Betclic, PMU, Betsson)
        3. **Click "Start Scraping"**
        4. **Copy-paste directly to Google Sheets!**
        
        ### Display Modes:
        - 🎨 **Colored View** - See bookmakers with their brand colors
        - 📋 **Copy-Paste View** - Clean table ready to paste into Sheets
        
        Choose your preferred view in the sidebar!
        """)
    
    elif menu_selection == "⚽ Football":
        sport = "Football"
        outcomes_count = 3
        run_sport_section(sport, outcomes_count, view_mode)
    
    elif menu_selection == "🎾 Tennis":
        sport = "Tennis"
        outcomes_count = 2
        run_sport_section(sport, outcomes_count, view_mode)


def run_sport_section(sport: str, outcomes_count: int, view_mode: str):
    """Run the scraping section for a given sport."""
    st.title(f"📊 {sport} Betting Odds Scraper")
    
    competitions_df = get_competitions_from_sheets(sport)
    
    if competitions_df.empty:
        st.warning(f"No competitions found for {sport}. Check Google Sheet tab '{sport}'.")
        return
    
    # Check for Favorite column
    has_favorites = "Favorite" in competitions_df.columns
    
    if has_favorites:
        favorite_comps = competitions_df[competitions_df["Favorite"].str.upper() == "Y"]["Competition"].tolist()
        all_comps = competitions_df["Competition"].tolist()
        
        st.info(f"⭐ {len(favorite_comps)} favorite competition(s) auto-selected!")
        
        selected_competitions = st.multiselect(
            "📌 Select competitions",
            all_comps,
            default=favorite_comps
        )
    else:
        st.warning("⚠️ 'Favorite' column not found. Add it to Google Sheet for auto-selection.")
        selected_competitions = st.multiselect(
            "📌 Select competitions",
            competitions_df["Competition"].tolist()
        )
    
    if selected_competitions:
        bookmaker_order = ["Winamax", "Unibet", "Betclic", "Pmu", "Betsson"]
        other_bookmakers = [
            "ParionsSport", "Zebet", "Olybet", "Bwin", "Vbet", 
            "Genybet", "Feelingbet"
        ]
        all_bookmakers = bookmaker_order + [b for b in other_bookmakers if b not in bookmaker_order]
        
        selected_bookmakers = st.multiselect(
            "🎰 Select bookmakers",
            all_bookmakers,
            default=bookmaker_order
        )
        
        nb_matches = st.slider("🔢 Number of matches per competition", 1, 20, 5)
        
        if st.button("🔍 Start Scraping", type="primary", use_container_width=True):
            with st.spinner("⏳ Scraping in progress..."):
                all_odds_df = pd.DataFrame()
                
                for comp in selected_competitions:
                    comp_url = competitions_df.loc[
                        competitions_df["Competition"] == comp, "URL"
                    ].values[0]
                    
                    scraped_df = get_match_odds(
                        comp_url,
                        selected_bookmakers,
                        nb_matches=nb_matches,
                        outcomes_count=outcomes_count
                    )
                    all_odds_df = pd.concat([all_odds_df, scraped_df], ignore_index=True)
                
                if not all_odds_df.empty:
                    formatted_df = format_table_for_copy_paste(all_odds_df, outcomes_count)
                    
                    # Display based on view mode
                    if view_mode == "🎨 Colored View":
                        st.success(f"✅ Retrieved {len(formatted_df)} odds entries!")
                        display_colored_table(formatted_df)
                    else:  # Copy-Paste View
                        st.success(f"✅ Retrieved {len(formatted_df)} odds entries!")
                        display_copy_paste_table(formatted_df, outcomes_count)
                else:
                    st.info(f"❌ No odds retrieved for {sport}.")
    else:
        st.info("Please select at least one competition to begin.")


if __name__ == "__main__":
    main()