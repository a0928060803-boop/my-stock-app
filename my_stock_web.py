import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup

# --- 網頁基礎配置 ---
st.set_page_config(page_title="小白股票診療室 Pro", layout="wide")

# --- 功能函數：抓取股名與新聞 ---
def get_stock_name(symbol):
    try:
        url = f"https://yahoo.com{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        target = soup.find('h1')
        if target:
            # 取得如 "鴻海 (2317)" 並只取名稱部分
            return target.text.strip().split(' ')[0]
        return symbol
    except:
        return symbol

def get_news(symbol):
    try:
        url = f"https://yahoo.com{symbol}/news"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        titles = soup.find_all('h3')
        return [t.text for t in titles[:5] if len(t.text) > 5]
    except:
        return []

# --- 側邊欄輸入區 ---
st.sidebar.header("🔍 診斷中心")
stock_id = st.sidebar.text_input("請輸入台股代號：", "2330")
analyze_btn = st.sidebar.button("開始看診", type="primary")

# --- 主畫面邏輯 ---
if analyze_btn or stock_id:
    # 判斷輸入是否為台股，自動補上後綴
    formatted_id = f"{stock_id}.TW" if len(stock_id) <= 4 else stock_id
    
    with st.spinner(f'正在為您調閱 {stock_id} 的深度數據...'):
        try:
            # 1. 抓取資料
            name = get_stock_name(stock_id)
            df = yf.download(formatted_id, period="6mo", interval="1d", progress=False)
            
            if df.empty:
                st.error("查無數據，請確認股號是否正確（例如：2330）。")
            else:
                # 處理 yfinance 可能產生的多層索引
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # 2. 頁面標題
                st.title(f"🏢 {name} ({stock_id}) 診斷報告")
                st.write(f"數據更新時間：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
                st.divider()

                # 3. 計算技術指標
                kd = df.ta.stoch()
                df['MA20'] = df['Close'].rolling(20).mean()
                
                # 提取最新數值
                lp = float(df['Close'].iloc[-1])
                k_val = float(kd.iloc[-1, 0])
                m20 = float(df['MA20'].iloc[-1])
                supp = float(df['Low'].tail(20).min())
                resi = float(df['High'].tail(20).max())

                # 4. 數據儀表板
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("目前股價", f"{lp:.2f}", f"{lp - df['Close'].iloc[-2]:.2f}")
                col_b.metric("月均線 (20MA)", f"{m20:.2f}")
                col_c.metric("近期壓力位", f"{resi:.2f}")

                # 5. K線圖表
                st.write("### 📈 近期股價走勢圖")
                fig = go.Figure(data=[go.Candlestick(
                    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'
                )])
                fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='月線'))
                fig.update_layout(height=450, margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

                # 6. 白話診斷說明
                st.write("### 📝 醫生診斷建議")
                c1, c2 = st.columns(2)
                with c1:
                    if lp > m20:
                        st.success(f"**趨勢：偏多格局**\n\n股價現在站穩在月線({m20:.1f})之上，代表市場氣氛不錯。")
                    else:
                        st.error(f"**趨勢：偏弱格局**\n\n股價目前在月線之下，建議多看少動，觀察地板價 {supp:.1f}。")
                with c2:
                    if k_val > 80:
                        st.warning(f"**熱度：太燙了**\n\nKD值來到 {k_val:.1f}，大家都在搶買，小心追高。")
                    elif k_val < 20:
                        st.success(f"**熱度：冷冰冰**\n\nKD值只有 {k_val:.1f}，沒人要買，通常是撿便宜的好時機。")
                    else:
                        st.write(f"**熱度：常態**\n\n目前市場情緒平穩，沒有過熱或過冷。")

                # 7. 財經新聞
                st.write("### 📰 相關財經頭條")
                news_list = get_news(stock_id)
                if news_list:
                    for n in news_list:
                        st.markdown(f"- {n}")
                else:
                    st.write("目前無相關新聞。")

        except Exception as e:
            st.error(f"診療過程發生錯誤：{e}")

# --- 頁尾 ---
st.sidebar.markdown("---")
st.sidebar.caption("小白股票診療室 v2.5 | 數據僅供參考")
