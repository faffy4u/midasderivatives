import streamlit as st
import requests
import pandas as pd

# Configure Streamlit Page
st.set_page_config(page_title="Derivatives Corner", page_icon="📊", layout="wide")

API_BASE = "https://nse-derivatives-api.onrender.com"

# Custom CSS for styling
st.markdown("""
    <style>
    /* Hot Stocks Card */
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #f97316;
        border-radius: 8px;
        padding: 8px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        margin-bottom: 8px;
    }
    .hot-title {
        color: #fb923c;
        font-weight: bold;
        font-size: 0.95rem;
        margin-bottom: 2px;
    }

    /* 7-Column Stock Cards */
    .column-title {
        font-size: 0.92rem;
        font-weight: 700;
        margin-bottom: 10px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        text-align: center;
    }
    .stock-card {
        border-radius: 7px;
        padding: 6px 8px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        min-height: 48px;
    }
    .stock-card-green {
        background-color: #f0fdf4;
        border: 1.2px solid #22c55e;
    }
    .stock-card-red {
        background-color: #fef2f2;
        border: 1.2px solid #ef4444;
    }
    .stock-left {
        display: flex;
        align-items: center;
        overflow: hidden;
        margin-right: 4px;
    }
    .stock-symbol {
        font-weight: 700;
        font-size: 0.78rem;
        color: #0f172a;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .stock-rank {
        color: #64748b;
        font-weight: 700;
        font-size: 0.75rem;
        margin-right: 4px;
        white-space: nowrap;
    }
    .stock-right {
        text-align: right;
        flex-shrink: 0;
    }
    .stock-change-green {
        color: #16a34a;
        font-weight: 700;
        font-size: 0.8rem;
        line-height: 1.1;
    }
    .stock-change-red {
        color: #dc2626;
        font-weight: 700;
        font-size: 0.8rem;
        line-height: 1.1;
    }
    .stock-vol {
        font-size: 0.65rem;
        color: #94a3b8;
        line-height: 1;
        margin-top: 2px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Derivatives Corner")

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

with st.spinner("Fetching live NSE data..."):
    gainers = fetch_data("/api/gainers") or []
    losers = fetch_data("/api/losers") or []
    active = fetch_data("/api/most-active") or []
    buildup = fetch_data("/api/buildup") or {}

# Deduplicate by symbol so names don't repeat
def prepare_df(data):
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if "symbol" in df.columns:
        df["symbol"] = df["symbol"].astype(str).str.strip()
        df = df.drop_duplicates(subset=["symbol"], keep="first")
    return df

df_gainers = prepare_df(gainers)
df_losers = prepare_df(losers)
df_active = prepare_df(active)
df_long = prepare_df(buildup.get("longBuildup", []))
df_short = prepare_df(buildup.get("shortBuildup", []))
df_covering = prepare_df(buildup.get("shortCovering", []))
df_unwinding = prepare_df(buildup.get("longUnwinding", []))

# ---------- SEARCH BAR ----------
search_query = st.text_input("🔍 Search by stock symbol (e.g. TCS, NIFTY)", "").strip().upper()

def filter_df(df):
    if df.empty:
        return pd.DataFrame()
    if search_query:
        df = df[df["symbol"].str.upper().str.contains(search_query, na=False)]
    return df.head(10)

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
        for sym in df.head(10)["symbol"].dropna().unique():
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
            st.markdown(f"""
                <div class="metric-card">
                    <div class="hot-title">🔥 {sym}</div>
                    <span style="font-size:0.75rem; color:#cbd5e1;">{', '.join(cats)}</span>
                </div>
            """, unsafe_allow_html=True)
else:
    st.info("No overlapping hot stocks right now.")

st.markdown("---")

# ---------- 7-COLUMN DASHBOARD ----------

def render_stock_cards(df, default_positive=True):
    sliced_df = filter_df(df)
    if sliced_df.empty:
        st.write("")  # Keep completely empty if no data
        return

    for idx, (_, row) in enumerate(sliced_df.iterrows(), start=1):
        sym = row.get("symbol", "-")
        
        # Percentage Change
        raw_pchange = row.get("perChange", row.get("pChange", 0.0))
        try:
            pchange = float(raw_pchange)
        except (ValueError, TypeError):
            pchange = 0.0

        # Volume / OI formatting
        vol = row.get("totalTradedVolume", row.get("quantityTraded", row.get("changeInOI", "-")))
        if isinstance(vol, (int, float)) and vol != "-":
            vol_abs = abs(vol)
            if vol_abs >= 1_000_000:
                vol_str = f"{vol/1_000_000:.1f}M"
            elif vol_abs >= 1_000:
                vol_str = f"{vol/1_000:.1f}k"
            else:
                vol_str = f"{vol:.0f}"
        else:
            vol_str = "-"

        # Card theme selection
        is_positive = pchange > 0 if pchange != 0.0 else default_positive
        card_class = "stock-card-green" if is_positive else "stock-card-red"
        change_class = "stock-change-green" if is_positive else "stock-change-red"
        sign = "+" if pchange > 0 else ""

        st.markdown(f"""
            <div class="stock-card {card_class}">
                <div class="stock-left">
                    <span class="stock-rank">#{idx}</span>
                    <span class="stock-symbol" title="{sym}">{sym}</span>
                </div>
                <div class="stock-right">
                    <div class="{change_class}">{sign}{pchange:.2f}%</div>
                    <div class="stock-vol">Vol: {vol_str}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

# 7 side-by-side columns
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

with c1:
    st.markdown('<div class="column-title">🟢 Top Gainers</div>', unsafe_allow_html=True)
    render_stock_cards(df_gainers, default_positive=True)

with c2:
    st.markdown('<div class="column-title">🔴 Top Losers</div>', unsafe_allow_html=True)
    render_stock_cards(df_losers, default_positive=False)

with c3:
    st.markdown('<div class="column-title">🔥 Most Active</div>', unsafe_allow_html=True)
    render_stock_cards(df_active, default_positive=True)

with c4:
    st.markdown('<div class="column-title">🟢 Long Buildup</div>', unsafe_allow_html=True)
    render_stock_cards(df_long, default_positive=True)

with c5:
    st.markdown('<div class="column-title">🔴 Short Buildup</div>', unsafe_allow_html=True)
    render_stock_cards(df_short, default_positive=False)

with c6:
    st.markdown('<div class="column-title">🟡 Short Covering</div>', unsafe_allow_html=True)
    render_stock_cards(df_covering, default_positive=True)

with c7:
    st.markdown('<div class="column-title">🟠 Long Unwinding</div>', unsafe_allow_html=True)
    render_stock_cards(df_unwinding, default_positive=False)

# Sidebar Refresh
if st.sidebar.button("🔄 Manual Refresh"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.markdown(f"**Last Connection:** `{API_BASE}`")
