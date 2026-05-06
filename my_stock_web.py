import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup

# --- 網頁配置 ---
st.set_page_config(page_title="小白股票診療室 Pro", layout="wide")

# --- 功能函數 ---
def get_stock_name(symbol):
    try:
        url = f"https://yahoo.com{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        soup = BeautifulSoup(requests.get(url, headers=headers, timeout=5).text, 'html.parser')
        target = soup.find('h1')
        return target.text.strip().split(' ') if target else symbol
    except: return symbol

def get_news(symbol):
    try:
        url = f"https://yahoo.com{symbol}/news"
        headers = {'User-Agent': 'Mozilla/5.0'}
        soup = BeautifulSoup(requests.get(url, headers=headers, timeout=5).text, 'html.parser')
        return [t.text for t in soup.find_all('h3')[:5] if len(t.text) > 5]
    except: return []

# --- 側邊欄 ---
st.sidebar.header("🔍 診斷中心")
stock_id = st.sidebar.text_input("請輸入台股代號：", "2330")
analyze_btn = st.sidebar.button("開始看診", type="primary")

# --- 主邏輯 ---
if analyze_btn or stock_id:
    formatted_id = f"{stock_id}.TW" if len(stock_id) <= 4 else stock_id
    with st.spinner(f'正在讀取 {stock_id} 數據...'):
        try:
            df = yf.download(formatted_id, period="1y", interval="1d", progress=False)
            if df.empty:
                st.error("查無數據，請確認股號。")
            else:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                
                # --- [自力救濟：不使用 pandas-ta 計算指標] ---
                # 1. 計算 MA20
                df['MA20'] = df['Close'].rolling(window=20).mean()
                # 2. 計算 KD (9, 3, 3)
                low_9 = df['Low'].rolling(window=9).min()
                high_9 = df['High'].rolling(window=9).max()
                rsv = (df['Close'] - low_9) / (high_9 - low_9) * 100
                df['K'] = rsv.ewm(com=2, adjust=False).mean() # 簡單平滑處理
                
                lp, k_val, m20 = float(df['Close'].iloc[-1]), float(df['K'].iloc[-1]), float(df['MA20'].iloc[-1])
                supp, resi = float(df['Low'].tail(20).min()), float(df['High'].tail(20).max())
                name = get_stock_name(stock_id)

                # --- 畫面呈現 ---
                st.title(f"🏢 {name} ({stock_id}) 診斷報告")
                st.divider()
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("目前股價", f"{lp:.2f}", f"{lp - df['Close'].iloc[-2]:.2f}")
                col_b.metric("月均線 (20MA)", f"{m20:.2f}")
                col_c.metric("近期壓力位", f"{resi:.2f}")

                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線')])
                fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='月線'))
                st.plotly_chart(fig, use_container_width=True)

                st.info("### 📝 醫生診斷建議")
                c1, c2 = st.columns(2)
                with c1:
                    if lp > m20: st.success(f"**趨勢：偏多格局**\n\n股價高於月線({m20:.1f})，表現強勁。")
                    else: st.error(f"**趨勢：偏弱格局**\n\n目前低於月線，請留意地板價 {supp:.1f}。")
                with c2:
                    if k_val > 80: st.warning(f"**熱度：太燙了**\n\nKD值 {k_val:.1f}，小心追高風險。")
                    elif k_val < 20: st.success(f"**熱度：冷冰冰**\n\nKD值 {k_val:.1f}，適合撿便宜。")
                    else: st.write(f"**熱度：常態**\n\nKD值 {k_val:.1f}，目前氣氛平穩。")

                st.write("### 📰 相關頭條")
                for n in get_news(stock_id): st.markdown(f"- {n}")
        except Exception as e:
            st.error(f"發生錯誤：{e}")
