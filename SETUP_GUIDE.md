# 📋 SETUP GUIDE - Betting Odds Scraper v2

## 🎯 What's New

✅ **Auto-select favorites** - Competitions marked `Y` appear pre-selected
✅ **Fixed table format** - Order: `Winamax | Unibet | Betclic | PMU | Betsson`
✅ **Empty cells** - Missing odds show as empty (ready for copy-paste)
✅ **Auto-calculated payout** - TRJ shown in separate column

---

## 📊 Google Sheet Structure

You must **update your Google Sheet** by adding a **"Favorite"** column:

### Football Tab:

### Tennis Tab:

---

## 🔄 Favorites = Y (Pre-selected):
- ⭐ Ligue 1
- ⭐ Premier League
- ⭐ Bundesliga
- ⭐ Serie A
- ⭐ La Liga
- ⭐ Champions League
- ⭐ ATP Madrid
- ⭐ WTA Madrid

---

## 📝 Steps to Update Google Sheet:

1. Open your Google Sheet
2. For each sport (Football, Tennis...):
   - Add column **"Favorite"** after "URL"
   - Fill with `Y` or `N`
   - Y = Pre-selected on app load
   - N = Manually select

3. Save

---

## 💻 How to Use:

1. Replace `streamlit_app.py` with this new version
2. Launch the app:
```bash
   streamlit run streamlit_app.py
```
3. Usage:
   - ⭐ Favorites appear auto-checked
   - Select bookmakers (default = Winamax, Unibet, Betclic, PMU, Betsson)
   - Click "Start scraping"
   - **Copy-paste the table directly into Google Sheets!**

---

## ✅ Checklist:

- [ ] "Favorite" column added in Google Sheet
- [ ] Y/N values filled
- [ ] Google Sheet saved
- [ ] Launch `streamlit run streamlit_app.py`
- [ ] Verify favorites are pre-selected
- [ ] Test scrape and copy-paste to Sheets

---

## ⚠️ Important Points:

- ✅ **Column name** - Must be exactly "Favorite" (capital F)
- ✅ **Fixed order** - Always same bookmaker order for consistency
- ✅ **Empty cells** - Ready for manual fill if needed
- ✅ **No export** - Direct copy-paste = simpler workflow

Let's go! 🚀