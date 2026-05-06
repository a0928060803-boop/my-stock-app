import os
import sys
import subprocess

# --- [自救程序] 自動安裝缺失套件 ---
def install_packages():
    required = {"yfinance", "pandas_ta", "plotly", "beautifulsoup4", "requests", "pandas"}
    for package in required:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_packages()

# --- [主程式開始] ---
import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup

# --- 網頁配置 ---
st.set_page_config(page_title="小白股票診療室 Pro", layout="wide")

# --- 側邊欄：輸入區 ---
st.sidebar.header("🔍 診斷中心")
stock_id = st.sidebar.text_input("請輸入台股代號：", "2330")
analyze_btn = st.sidebar.button("開始看診", type="primary")

# --- 功能函數 ---
def get_stock_name(symbol):
    try:
        url = f"https://yahoo.com{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        target = soup.find('h1')
        if target:
            full_text = target.text.strip()
            name = full_text.split(' ')[0]
            return name
        return symbol
    except: return symbol

def get_news(symbol):
    try:
        url = f"https://yahoo.com{symbol}/news"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        titles = soup.find_all('h3')
        return [t.text for t in titles[:5] if len(t.text) > 5]
    except: return []

# --- 主畫面邏輯 ---
if analyze_btn or stock_id:
    formatted_id = f"{stock_id}.TW" if len(stock_id) <= 4 else stock_id
    
    with st.spinner(f'正在讀取 {stock_id} 的大數據...'):
        try:
            # 1. 抓取資料與名稱
            name = get_stock_name(stock_id)
            df = yf.download(formatted_id, period="6mo", interval="1d", progress=False)
            
            if df.empty:
                st.error("查無數據，請確認股號是否正確。")
            else:
                if isinstance(df.columns, pd.MultiIndex): 
                    df.columns = df.columns.get_level_values(0)

                # 2. 顯示標題
                st.title(f"🏢 {name} ({stock_id}) 診斷報告")
                st.write(f"數據更新時間：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
                st.divider()

                # 3. 技術指標計算
                kd = df.ta.stoch()
                df['MA5'] = df['Close'].rolling(5).mean()
                df['MA20'] = df['Close'].rolling(20).mean()
                
                lp = float(df['Close'].iloc[-1])
                k_val = float(kd.iloc[-1, 0])
                m5 = float(df['MA5'].iloc[-1])
                m20 = float(df['MA20'].iloc[-1])
                supp = float(df['Low'].tail(20).min())
                resi = float(df['High'].tail(20).max())

                # 4. 數據儀表板
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("目前股價", f"{lp:.2f}", f"{lp-df['Close'].iloc[-2]:.2f}")
                m2.metric("5日均價", f"{m5:.2f}")
                m3.metric("月均線 (20MA)", f"{m20:.2f}")
                m4.metric("近期壓力位", f"{resi:.2f}")

                # 5. K線圖表
                st.write("### 📈 近期股價走勢圖")
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'),
                                     go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1), name='月線')])
                fig.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)

                # 6. 白話診斷
                c1, c2 = st.columns(2)
                with c1:
                    st.info("### 📝 趨勢解析")
                    if lp > m20: st.success(f"**強勢格局**：股價穩守月線之上，氣氛正向。")
                    else: st.error(f"**弱勢格局**：目前在月線下方掙扎，先看地板 {supp:.1f} 是否守住。")
                with c2:
                    st.info("### 🔥 市場熱度")
                    if k_val > 80: st.warning(f"KD值 {k_val:.1f}：**太熱了！** 容易追高被套牢。")
                    elif k_val < 20: st.success(f"KD值 {k_val:.1f}：**夠冷了。** 適合慢慢進場撿便宜。")
                    else: st.write(f"KD值 {k_val:.1f}：目前溫度適中。")

                # 7. 即時新聞
                st.write("### 📰 相關財經頭條")
                news = get_news(stock_id)
                if news:
                    for n in news: st.markdown(f"- {n}")
                else: st.write("目前無即時新聞資訊。")

        except Exception as e:
            st.error(f"看診發生錯誤：{e}")

# --- 底部 ---
st.sidebar.markdown("---")
st.sidebar.caption("小白股票診療室 v2.3 | 數據僅供參考")
