import streamlit as st
import requests
import pandas as pd

# Configure Streamlit Page
st.set_page_config(page_title="Derivatives Corner", page_icon="📊", layout="wide")

API_BASE = "https://nse-derivatives-api.onrender.com"

# Custom CSS for styling
st.markdown("""
    <style>
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #f97316;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    .hot-title {
        color: #fb923c;
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 5px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Derivatives Corner (Top 10)")

# ---------- DATA RETRIEVAL ----------

@st.cache_data(ttl=30)
def fetch_data(endpoint):
    try:
        res = requests.get(f"{API_BASE}{endpoint}", timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        st.error(f"Error fetching {endpoint}: {e}")
    return None

# Load all data
with st.spinner("Fetching live NSE data..."):
    gainers = fetch_data("/api/gainers") or []
    losers = fetch_data("/api/losers") or []
    active = fetch_data("/api/most-active") or []
    buildup = fetch_data("/api/buildup") or {}

# Convert to DataFrames
df_gainers = pd.DataFrame(gainers)
df_losers = pd.DataFrame(losers)
df_active = pd.DataFrame(active)

df_long = pd.DataFrame(buildup.get("longBuildup", []))
df_short = pd.DataFrame(buildup.get("shortBuildup", []))
df_covering = pd.DataFrame(buildup.get("shortCovering", []))
df_unwinding = pd.DataFrame(buildup.get("longUnwinding", []))

# ---------- SEARCH BAR ----------
search_query = st.text_input("🔍 Search by stock symbol (e.g. TCS, NIFTY)", "").strip().upper()

# ---------- HOT STOCKS (2+ Categories Overlap) ----------
st.subheader("🔥 Hot Stocks (Appearing in Multiple Categories)")

categories_map = {
    "Gainers": df_gainers,
    "Losers": df_losers,
    "Most Active": df_active,
    "Long Buildup": df_long,
    "Short Buildup": df_short,
    "Short Covering": df_covering,
    "Long Unwinding": df_unwinding
}

symbol_categories = {}
for cat_name, df in categories_map.items():
    if not df.empty and "symbol" in df.columns:
        # Check only first 10 (since we care about top performance)
        for sym in df.head(10)["symbol"].unique():
            if sym:
                if sym not in symbol_categories:
                    symbol_categories[sym] = []
                symbol_categories[sym].append(cat_name)

hot_stocks = {sym: cats for sym, cats in symbol_categories.items() if len(cats) >= 2}

if search_query:
    hot_stocks = {sym: cats for sym, cats in hot_stocks.items() if search_query in sym}

if hot_stocks:
    cols = st.columns(min(len(hot_stocks), 5))
    for idx, (sym, cats) in enumerate(hot_stocks.items()):
        col_idx = idx % 5
        with cols[col_idx]:
            cats_joined = ", ".join(cats)
            st.markdown(f"""
                <div class="metric-card">
                    <div class="hot-title">🔥 {sym}</div>
                    <span style="font-size:0.8rem; color:#cbd5e1;">{cats_joined}</span>
                </div>
            """, unsafe_allow_html=True)
else:
    st.info("No overlapping hot stocks right now.")

st.markdown("---")

# ---------- DATA PRESENTATION (STRICT TOP 10) ----------

# Apply search filter helper
def filter_and_slice(df):
    if df.empty:
        return pd.DataFrame()
    if search_query:
        df = df[df["symbol"].str.upper().str.contains(search_query, na=False)]
    return df.head(10) # strictly top 10

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📈 Gainers", "📉 Losers", "🔥 Most Active", 
    "🟢 Long Buildup", "🔴 Short Buildup", "🟡 Short Covering", "🟠 Long Unwinding"
])

# Styling dataframes
def show_styled_df(df, columns_to_show):
    sliced_df = filter_and_slice(df)
    if not sliced_df.empty:
        # Match only existing columns to avoid errors
        available_cols = [c for c in columns_to_show if c in sliced_df.columns]
        display_df = sliced_df[available_cols].copy()
        display_df.index = display_df.index + 1 # 1-based ranking index
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("No records matching search query.")

with tab1:
    st.subheader("Top 10 Gainers")
    show_styled_df(df_gainers, ["symbol", "series", "open_price", "high_price", "low_price", "ltp", "prev_price", "perChange"])

with tab2:
    st.subheader("Top 10 Losers")
    show_styled_df(df_losers, ["symbol", "series", "open_price", "high_price", "low_price", "ltp", "prev_price", "perChange"])

with tab3:
    st.subheader("Top 10 Most Active (Volume)")
    show_styled_df(df_active, ["symbol", "identifier", "lastPrice", "pChange", "quantityTraded", "totalTradedVolume"])

with tab4:
    st.subheader("Top 10 Long Buildup")
    show_styled_df(df_long, ["symbol", "instrument", "expiryDate", "ltp", "pChange", "changeInOI", "pChangeInOI"])

with tab5:
    st.subheader("Top 10 Short Buildup")
    show_styled_df(df_short, ["symbol", "instrument", "expiryDate", "ltp", "pChange", "changeInOI", "pChangeInOI"])

with tab6:
    st.subheader("Top 10 Short Covering")
    show_styled_df(df_covering, ["symbol", "instrument", "expiryDate", "ltp", "pChange", "changeInOI", "pChangeInOI"])

with tab7:
    st.subheader("Top 10 Long Unwinding")
    show_styled_df(df_unwinding, ["symbol", "instrument", "expiryDate", "ltp", "pChange", "changeInOI", "pChangeInOI"])

# Manual Refresh Button in Sidebar
if st.sidebar.button("🔄 Manual Refresh"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.markdown(f"**Last Connection:** `{API_BASE}`")
