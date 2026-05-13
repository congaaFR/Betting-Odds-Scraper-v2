# 🚀 CHANGES v1 → v2

## ✨ Main Improvements:

### 1. **Auto-Select Favorites** ⭐
**Before:** Had to re-select same competitions every day
**After:** Competitions marked `Y` in Google Sheet are pre-checked

```python
favorite_comps = competitions_df[competitions_df["Favorite"].str.upper() == "Y"]["Competition"].tolist()
selected_competitions = st.multiselect(
    "📌 Select competitions",
    all_comps,
    default=favorite_comps  # ← Pre-selected!
)
```

---

### 2. **Fixed Table Format** 📊
**Before:** Bookmakers in random order (scraped order)
**After:** Always in this order: `Winamax | Unibet | Betclic | PMU | Betsson`

```python
bookmaker_order = ["Winamax", "Unibet", "Betclic", "Pmu", "Betsson"]
# Reorganizes DataFrame to this fixed order
```

---

### 3. **Empty Cells Instead of Missing Rows** 
**Before:**