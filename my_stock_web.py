import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup

# --- 網頁配置 ---
st.set_page_config(page_title="小白股票診療室 Pro", layout="wide")

# --- [核心更新] 強力中文股名爬蟲 ---
def get_chinese_name(symbol):
    try:
        # 爬取 Yahoo 股市個股頁面
        url = f"https://yahoo.com{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找 H1 標籤 (Yahoo 股名的位置)
        h1_text = soup.find('h1').text.strip()
        
        # 如果內容是 "鴻海 2317" 或 "鴻海 (2317)"，只切出中文部分
        # 我們用空格或左括號來切分
        clean_name = h1_text.split(' ')[0].split('(')[0]
        return clean_name
    except:
        return symbol

# --- 側邊欄 ---
st.sidebar.header("🔍 診斷中心")
stock_id = st.sidebar.text_input("請輸入台股代號：", "2317")
analyze_btn = st.sidebar.button("開始看診", type="primary")

# --- 主畫面邏輯 ---
if analyze_btn or stock_id:
    formatted_id = f"{stock_id}.TW" if len(stock_id) <= 4 else stock_id
    
    with st.spinner(f'正在分析 {stock_id} ...'):
        try:
            # 1. 抓取中文名稱
            stock_name = get_chinese_name(stock_id)
            
            # 2. 獲取股價數據
            df = yf.download(formatted_id, period="1y", interval="1d", progress=False)
            
            if df.empty:
                st.error("查無數據，請確認股號。")
            else:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # 顯示標題 (這下一定是中文了！)
                st.title(f"🏢 {stock_name} ({stock_id}) 診斷報告")
                st.divider()

                # 3. 指標計算
                df['MA20'] = df['Close'].rolling(window=20).mean()
                low_9 = df['Low'].rolling(window=9).min()
                high_9 = df['High'].rolling(window=9).max()
                rsv = (df['Close'] - low_9) / (high_9 - low_9) * 100
                df['K'] = rsv.ewm(com=2, adjust=False).mean()
                
                lp = float(df['Close'].iloc[-1])
                k_val = float(df['K'].iloc[-1])
                m20 = float(df['MA20'].iloc[-1])
                supp = float(df['Low'].tail(20).min())
                resi = float(df['High'].tail(20).max())

                # 4. 數據儀表板
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("目前股價", f"{lp:.2f}", f"{lp - df['Close'].iloc[-2]:.2f}")
                col_b.metric("月均線 (20MA)", f"{m20:.2f}")
                col_c.metric("近期壓力位", f"{resi:.2f}")

                # 5. K 線圖
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線')])
                fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='月線'))
                fig.update_layout(height=450, margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

                # 6. 白話診斷
                st.write("### 📝 醫生診斷說明")
                c1, c2 = st.columns(2)
                with c1:
                    if lp > m20: st.success(f"**趨勢：強勢格局**\n\n股價在月線({m20:.1f})之上，氣氛很好。")
                    else: st.error(f"**趨勢：偏弱格局**\n\n股價跌破月線，請觀察地板價 {supp:.1f}。")
                with c2:
                    if k_val > 80: st.warning(f"**熱度：太燙了**\n\nKD值 {k_val:.1f}，小心不要追高。")
                    elif k_val < 20: st.success(f"**熱度：冷冰冰**\n\nKD值 {k_val:.1f}，適合進場撿便宜。")
                    else: st.write(f"**熱度：常態**\n\nKD值 {k_val:.1f}，情緒平穩。")

        except Exception as e:
            st.error(f"發生錯誤：{e}")

st.sidebar.markdown("---")
st.sidebar.caption("小白股票診療室 v2.7 | 中文名稱強化版")
