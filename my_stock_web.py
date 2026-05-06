import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# --- 網頁配置 ---
st.set_page_config(page_title="小白股票診療室 Pro", layout="wide")

# --- [終極方案] 內建常用台股中文對照表 ---
# 這樣熱門股絕對不會出現英文
STOCK_DB = {
    "2317": "鴻海", "2330": "台積電", "2454": "聯發科", "2303": "聯電", 
    "2382": "廣達", "2313": "金像電", "2603": "長榮", "2609": "陽明",
    "2615": "萬海", "2881": "富邦金", "2882": "國泰金", "2308": "台達電",
    "2357": "華碩", "2409": "友達", "3481": "群創", "2324": "仁寶",
    "2314": "台揚", "2618": "長榮航", "2610": "華航", "1101": "台泥"
}

def get_real_chinese_name(symbol):
    # 1. 先從內建資料庫找
    if symbol in STOCK_DB:
        return STOCK_DB[symbol]
    
    # 2. 如果找不到，利用 Yahoo Finance 的查詢 API (較穩定)
    try:
        url = f"https://yahoo.com{symbol}.TW"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers).json()
        # 嘗試從搜尋結果中抓取 shortname
        if res.get('quotes'):
            name = res['quotes'][0].get('shortname', symbol)
            # 過濾掉英文後綴
            for s in ["Semiconductor", "Manufacturing", "Industry", "Co.", "Ltd."]:
                name = name.replace(s, "").strip()
            return name
    except:
        pass
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
            # 1. 取得名稱
            stock_name = get_real_chinese_name(stock_id)
            
            # 2. 獲取數據
            df = yf.download(formatted_id, period="1y", interval="1d", progress=False)
            
            if df.empty:
                st.error("查無數據，請確認股號。")
            else:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # 顯眼標題
                st.title(f"🏢 {stock_name} ({stock_id}) 診斷報告")
                st.divider()

                # 3. 指標計算
                df['MA20'] = df['Close'].rolling(window=20).mean()
                low_9, high_9 = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
                rsv = (df['Close'] - low_9) / (high_9 - low_9) * 100
                df['K'] = rsv.ewm(com=2, adjust=False).mean()
                
                lp, k_val, m20 = float(df['Close'].iloc[-1]), float(df['K'].iloc[-1]), float(df['MA20'].iloc[-1])
                supp, resi = float(df['Low'].tail(20).min()), float(df['High'].tail(20).max())

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
                    if lp > m20: st.success(f"**趨勢：強勢格局**\n\n股價在月線({m20:.1f})之上，大家看好。")
                    else: st.error(f"**趨勢：偏弱格局**\n\n股價跌破月線，請看地板價 {supp:.1f}。")
                with c2:
                    if k_val > 80: st.warning(f"**熱度：太燙了**\n\n現在大家都在搶買，小心追高風險。")
                    elif k_val < 20: st.success(f"**熱度：冷冰冰**\n\n沒人要買，通常是撿便宜的好時機。")
                    else: st.write(f"**熱度：常態**\n\n目前市場情緒平穩。")

        except Exception as e:
            st.error(f"發生錯誤：{e}")

st.sidebar.markdown("---")
st.sidebar.caption("小白股票診療室 v2.8 | 終極中文名版本")
