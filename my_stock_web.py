import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# --- 網頁配置 ---
st.set_page_config(page_title="小白股票診療室 Pro", layout="wide")

# --- 內建台股中文名資料庫 (確保名稱正確) ---
STOCK_DB = {
    "2317": "鴻海", "2330": "台積電", "2454": "聯發科", "2303": "聯電", 
    "2382": "廣達", "2313": "金像電", "2603": "長榮", "2609": "陽明",
    "2615": "萬海", "2881": "富邦金", "2882": "國泰金", "2308": "台達電",
    "2357": "華碩", "2409": "友達", "3481": "群創", "2324": "仁寶",
    "2314": "台揚", "2618": "長榮航", "2610": "華航", "1101": "台泥"
}

def get_real_chinese_name(symbol):
    if symbol in STOCK_DB: return STOCK_DB[symbol]
    try:
        url = f"https://yahoo.com{symbol}.TW"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if res.get('quotes'):
            name = res['quotes'][0].get('shortname', symbol)
            for s in ["Semiconductor", "Manufacturing", "Industry", "Co.", "Ltd."]:
                name = name.replace(s, "").strip()
            return name
    except: pass
    return symbol

# --- 側邊欄 ---
st.sidebar.header("🔍 診斷中心")
stock_id = st.sidebar.text_input("請輸入台股代號：", "2317")
analyze_btn = st.sidebar.button("開始深度分析", type="primary")

if analyze_btn or stock_id:
    formatted_id = f"{stock_id}.TW" if len(stock_id) <= 4 else stock_id
    
    with st.spinner(f'系統計算中，請稍候...'):
        try:
            df = yf.download(formatted_id, period="1y", interval="1d", progress=False)
            if df.empty:
                st.error("查無數據，請確認股號。")
            else:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # --- 1. 計算所有專業指標 ---
                # MA20 (月線)
                df['MA20'] = df['Close'].rolling(20).mean()
                # BIAS (乖離率)
                df['BIAS'] = ((df['Close'] - df['MA20']) / df['MA20']) * 100
                # KD (9, 3, 3)
                low_9, high_9 = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
                rsv = (df['Close'] - low_9) / (high_9 - low_9) * 100
                df['K'] = rsv.ewm(com=2, adjust=False).mean()
                df['D'] = df['K'].rolling(3).mean()
                # MACD
                ema12 = df['Close'].ewm(span=12, adjust=False).mean()
                ema26 = df['Close'].ewm(span=26, adjust=False).mean()
                df['DIF'] = ema12 - ema26
                df['MACD_DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
                df['MACD_HIST'] = df['DIF'] - df['MACD_DEA']

                # 提取最新數據
                lp = float(df['Close'].iloc[-1])
                k_val = float(df['K'].iloc[-1])
                d_val = float(df['D'].iloc[-1])
                macd_hist = float(df['MACD_HIST'].iloc[-1])
                bias = float(df['BIAS'].iloc[-1])
                vol = int(df['Volume'].iloc[-1])
                avg_vol = int(df['Volume'].tail(5).mean()) # 5日均量
                stock_name = get_real_chinese_name(stock_id)

                # --- 2. 顯示標題與基礎數據 ---
                st.title(f"🏢 {stock_name} ({stock_id}) 專業診斷報告")
                st.divider()
                
                # 儀表板
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("目前價格", f"{lp:.2f}")
                col2.metric("KD熱度 (K值)", f"{k_val:.1f}")
                col3.metric("MACD 動能", f"{macd_hist:.2f}")
                col4.metric("乖離率 BIAS", f"{bias:.1f}%")

                # --- 3. 核心診斷說明 ---
                st.write("### 📝 四大指標綜合判斷")
                c1, c2 = st.columns(2)
                
                with c1:
                    st.info("**📈 技術趨勢分析**")
                    # KD 建議
                    if k_val > 80: st.write("● **KD 指標**：現在處於「過熱區」，大家都在搶，不建議追高。")
                    elif k_val < 20: st.write("● **KD 指標**：處於「超跌區」，沒人要買，是撿便宜的時機。")
                    else: st.write("● **KD 指標**：熱度適中，盤整走勢中。")

                    # MACD 建議
                    if macd_hist > 0: st.write("● **MACD 動能**：紅柱成長中，代表股價「正在衝」，動能強勁。")
                    else: st.write("● **MACD 動能**：綠柱或縮減中，代表動能減弱，可能要回檔了。")

                with c2:
                    st.info("**📊 量能與乖離分析**")
                    # VOL 建議
                    if vol > avg_vol * 1.5: st.write(f"● **成交量 (VOL)**：今日「爆量」！比平時大很多，是大變盤的訊號。")
                    else: st.write(f"● **成交量 (VOL)**：量能平穩，屬於正常的日常交易。")

                    # BIAS 建議
                    if bias > 5: st.write(f"● **乖離率 (BIAS)**：股價跑得比月線快太多，小心會像橡皮彈回來。")
                    elif bias < -5: st.write(f"● **乖離率 (BIAS)**：跌得太離譜，離月線太遠，隨時可能反彈。")
                    else: st.write(f"● **乖離率 (BIAS)**：與月線距離正常。")

                # --- 4. 最終買賣動作建議 ---
                st.divider()
                score = 0
                if k_val < 30: score += 1
                if macd_hist > 0: score += 1
                if lp > df['MA20'].iloc[-1]: score += 1
                
                st.subheader("💡 系統最終操作建議")
                if score >= 2:
                    st.success(f"**【 綜合評等：強勢看多 】**\n\n指標顯示動能與趨勢都在你這邊。建議參考價：{lp:.2f} 元附近，目標看短期高點。")
                elif score <= 0:
                    st.error(f"**【 綜合評等：偏空觀望 】**\n\n指標顯示氣氛轉弱，買盤縮手。目前不急著進場，先守住現金。")
                else:
                    st.warning(f"**【 綜合評等：中性操作 】**\n\n目前沒有明顯方向，建議在支撐與壓力之間「低買高賣」即可。")

                # --- 5. 圖表區 ---
                st.write("### 📈 股價走勢與指標圖")
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線')])
                fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='月線'))
                fig.update_layout(height=500, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"分析失敗，原因：{e}")

st.sidebar.markdown("---")
st.sidebar.caption("小白股票診療室 v3.0 | 專業指標版")
