import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# ==========================================
# 1. UI SETUP & CUSTOM CSS
# ==========================================
st.set_page_config(page_title="Quant Dashboard", layout="wide", initial_sidebar_state="expanded")

# Inject custom CSS to make the metrics look like floating dark-mode cards
st.markdown("""
<style>
div[data-testid="metric-container"] {
    background-color: #1E1E1E;
    border: 1px solid #333333;
    padding: 15px;
    border-radius: 8px;
    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.4);
}
</style>
""", unsafe_allow_html=True)

st.title("🏛️ Institutional Asset Forecaster")
st.markdown("Algorithmic historical analysis and future value projections.")
st.divider()

# ==========================================
# 2. SIDEBAR CONFIGURATION
# ==========================================
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2422/2422183.png", width=80) 
st.sidebar.header("Terminal Controls")

# Upgraded to accept full company names
user_input = st.sidebar.text_input("Target Asset (Name or Ticker)", "AAPL")

st.sidebar.subheader("Backtest Parameters")
history_years = st.sidebar.slider("Historical Data Range (Years)", 1, 10, 5)

st.sidebar.subheader("Forecasting Parameters")
monthly_sip = st.sidebar.number_input("Monthly Capital Allocation ($)", min_value=10, value=100)
forecast_years = st.sidebar.slider("Projection Horizon (Years)", 1, 30, 10)

# ==========================================
# 3. SMART SEARCH & DATA ACQUISITION
# ==========================================
def get_ticker_symbol(query):
    """Pings Yahoo Finance to convert a name like 'Netflix' into 'NFLX'"""
    search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(search_url, headers=headers)
        data = response.json()
        if 'quotes' in data and len(data['quotes']) > 0:
            return data['quotes'][0]['symbol']
    except Exception:
        pass
    return query.upper()

# Resolve the user's text into an official ticker
ticker_symbol = get_ticker_symbol(user_input)
st.sidebar.success(f"Matched Ticker: **{ticker_symbol}**")

@st.cache_data
def load_data(ticker, years):
    stock_data = yf.download(ticker, period=f"{years}y")
    return stock_data

data = load_data(ticker_symbol, history_years)

# ==========================================
# 4. MATH & DASHBOARD UI
# ==========================================
if not data.empty:
    try:
        # Calculate Moving Averages
        data['SMA_50'] = data['Close'].squeeze().rolling(window=50).mean()
        data['SMA_200'] = data['Close'].squeeze().rolling(window=200).mean()

        # Force pure Python floats to prevent Pandas formatting errors
        start_price = float(data['Close'].squeeze().iloc[0])
        end_price = float(data['Close'].squeeze().iloc[-1])
        prev_price = float(data['Close'].squeeze().iloc[-2])
        
        daily_change = float(end_price - prev_price)
        cagr = float((end_price / start_price) ** (1 / history_years) - 1)
        high_52 = float(data['Close'].squeeze().tail(252).max())

        # The Dashboard Tabs
        tab1, tab2 = st.tabs(["📊 Market Overview", "🔮 Predictive Analytics"])

        # --- TAB 1: THE MARKET OVERVIEW ---
        with tab1:
            st.subheader(f"Asset Performance: {ticker_symbol}")
            
            # Metric Cards
            col1, col2, col3 = st.columns(3)
            col1.metric("Current Price", f"${end_price:,.2f}", f"{daily_change:,.2f} Today")
            col2.metric(f"{history_years}-Year CAGR", f"{(cagr * 100):.2f}%")
            col3.metric("52-Week High", f"${high_52:,.2f}")
            
            st.markdown("<br>", unsafe_allow_html=True) 
            
            # Professional Candlestick Chart
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=data.index, open=data['Open'].squeeze(), high=data['High'].squeeze(), 
                low=data['Low'].squeeze(), close=data['Close'].squeeze(), name='Price Action'
            ))
            fig.add_trace(go.Scatter(x=data.index, y=data['SMA_50'].squeeze(), mode='lines', name='50 SMA', line=dict(color='orange', width=1.5)))
            fig.add_trace(go.Scatter(x=data.index, y=data['SMA_200'].squeeze(), mode='lines', name='200 SMA', line=dict(color='cyan', width=1.5)))
            
            fig.update_layout(
                height=600, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0),
                xaxis_rangeslider_visible=False, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        # --- TAB 2: THE PREDICTION MODEL ---
        with tab2:
            st.subheader("Quantitative Growth Projection")
            st.info(f"Assuming **{ticker_symbol}** maintains its historical CAGR of **{(cagr * 100):.2f}%** over the next **{forecast_years} years**.")
            
            monthly_rate = cagr / 12
            total_months = forecast_years * 12
            
            # Compound Interest Math
            if monthly_rate > 0:
                future_value = monthly_sip * (((1 + monthly_rate) ** total_months) - 1) / monthly_rate * (1 + monthly_rate)
            else:
                future_value = monthly_sip * total_months
                
            total_invested = monthly_sip * total_months
            profit = future_value - total_invested

            # Projection Metrics
            p_col1, p_col2, p_col3 = st.columns(3)
            p_col1.metric("Capital Deployed", f"${total_invested:,.2f}")
            p_col2.metric("Projected Portfolio Value", f"${future_value:,.2f}", f"+${profit:,.2f} Profit")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.write("### Wealth Composition")
            st.progress(min(total_invested / future_value, 1.0))
            st.caption("Bar represents the ratio of your deployed capital (solid) vs compound growth generated by the asset.")

    except Exception as e:
        st.error(f"Data processing error: Ensure the asset name is valid. Details: {e}")

else:
    st.error("No data found. Please check your spelling or try a different asset.")

    
