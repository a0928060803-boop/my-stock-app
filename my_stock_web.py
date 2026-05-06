import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# --- 1. 網頁基礎配置 ---
st.set_page_config(page_title="小白股票診療室 Pro", layout="wide")

# --- 2. 常用台股資料庫 ---
STOCK_DB = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "0050": "元大台灣50",
    "00878": "國泰高股息", "00929": "復華科技優息", "00679B": "元大美債20年",
    "00937B": "群益ESG投等債20+", "00992B": "統一美債20年", "2314": "台揚"
}

def get_real_chinese_name(symbol):
    clean_sid = symbol.split('.')[0].upper()
    if clean_sid in STOCK_DB: return STOCK_DB[clean_sid]
    try:
        url = f"https://yahoo.com{symbol}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if res.get('quotes'):
            name = res['quotes'][0].get('shortname', symbol)
            for s in ["Semiconductor", "Manufacturing", "Industry", "Co.", "Ltd.", "Holdings"]:
                name = name.replace(s, "").strip()
            return name
    except: pass
    return symbol

# --- 3. 側邊欄導航 ---
st.sidebar.header("🏥 診斷中心")
quick_select = st.sidebar.selectbox(
    "🔥 熱門標的快速選單",
    ["手動輸入代號", "2330 台積電", "2317 鴻海", "00878 國泰高股息", "00679B 元大美債", "00937B 群益債券", "00992B 統一美債", "2314 台揚"]
)

default_id = quick_select.split(' ')[0] if quick_select != "手動輸入代號" else "2330"
stock_id = st.sidebar.text_input("請輸入台股/美股/ETF代號：", default_id)
analyze_btn = st.sidebar.button("開始深度分析", type="primary")

# --- 4. 主畫面邏輯 ---
if analyze_btn or stock_id:
    sid = stock_id.upper().strip()
    
    with st.spinner(f'系統正在為您搜尋 {sid} 的歷史數據...'):
        try:
            df = pd.DataFrame()
            if sid.endswith(".TW") or sid.endswith(".TWO") or sid.endswith(".US") or sid.startswith("^"):
                search_list = [sid]
            elif sid.isalpha() and len(sid) >= 2: 
                search_list = [sid] 
            else:
                if sid.endswith("B"):
                    search_list = [f"{sid}.TWO", f"{sid}.TW"]
                else:
                    search_list = [f"{sid}.TW", f"{sid}.TWO"]

            final_id = sid
            for target_id in search_list:
                df = yf.download(target_id, period="1y", interval="1d", progress=False)
                if not df.empty:
                    final_id = target_id
                    break
            
            if df.empty:
                st.error(f"🛑 查無數據。請確認代號【{stock_id}】。")
            else:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # --- 指標計算 ---
                df['MA20'] = df['Close'].rolling(20).mean()
                df['BIAS'] = ((df['Close'] - df['MA20']) / df['MA20']) * 100
                low_9, high_9 = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
                rsv = (df['Close'] - low_9) / (high_9 - low_9) * 100
                df['K'] = rsv.ewm(com=2, adjust=False).mean()
                df['D'] = df['K'].ewm(com=2, adjust=False).mean()
                
                ema12 = df['Close'].ewm(span=12, adjust=False).mean()
                ema26 = df['Close'].ewm(span=26, adjust=False).mean()
                df['DIF'] = ema12 - ema26
                df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
                df['MACD_HIST'] = df['DIF'] - df['DEA']

                lp, k_val, macd_h, bias = float(df['Close'].iloc[-1]), float(df['K'].iloc[-1]), float(df['MACD_HIST'].iloc[-1]), float(df['BIAS'].iloc[-1])
                vol, avg_vol = int(df['Volume'].iloc[-1]), int(df['Volume'].tail(5).mean())
                stock_name = get_real_chinese_name(final_id)

                # --- 畫面呈現 ---
                st.title(f"🏢 {stock_name} ({sid}) 專業診斷報告")
                st.divider()
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("目前價格", f"{lp:.2f}", f"{lp - df['Close'].iloc[-2]:.2f}")
                m2.metric("KD 熱度", f"{k_val:.1f}")
                m3.metric("MACD 動能", f"{macd_h:.2f}")
                m4.metric("乖離率 BIAS", f"{bias:.1f}%")

                # --- 核心更新：使用分頁按鈕切換圖表 ---
                st.write("### 📈 專業指標分析圖表")
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["K線走勢", "成交量 (VOL)", "隨機指標 (KD)", "平滑指標 (MACD)", "乖離率 (BIAS)"])

                # 設定顯示區間 (最近 60 天)
                last_date = df.index[-1]
                start_date = last_date - pd.Timedelta(days=60)
                recent_df = df[df.index >= start_date]
                y_min, y_max = recent_df['Low'].min() * 0.97, recent_df['High'].max() * 1.03

                with tab1:
                    fig1 = go.Figure(data=[go.Candlestick(
                        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線',
                        increasing_line_color='#FF3232', increasing_fillcolor='#FF3232', 
                        decreasing_line_color='#00AB5E', decreasing_fillcolor='#00AB5E'
                    )])
                    fig1.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='月線'))
                    fig1.update_layout(height=500, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0),
                                      xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[y_min, y_max], fixedrange=False))
                    st.plotly_chart(fig1, use_container_width=True)

                with tab2:
                    colors = ['#FF3232' if c >= o else '#00AB5E' for c, o in zip(df['Close'], df['Open'])]
                    fig2 = go.Figure(data=[go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color=colors)])
                    fig2.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(range=[start_date, last_date]))
                    st.plotly_chart(fig2, use_container_width=True)

                with tab3:
                    fig3 = go.Figure()
                    fig3.add_trace(go.Scatter(x=df.index, y=df['K'], line=dict(color='#FF3232', width=2), name='K值'))
                    fig3.add_trace(go.Scatter(x=df.index, y=df['D'], line=dict(color='#00AB5E', width=2), name='D值'))
                    fig3.add_hline(y=80, line_dash="dash", line_color="gray")
                    fig3.add_hline(y=20, line_dash="dash", line_color="gray")
                    fig3.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(range=[start_date, last_date]))
                    st.plotly_chart(fig3, use_container_width=True)

                with tab4:
                    fig4 = go.Figure()
                    colors = ['#FF3232' if h >= 0 else '#00AB5E' for h in df['MACD_HIST']]
                    fig4.add_trace(go.Bar(x=df.index, y=df['MACD_HIST'], name='柱狀體', marker_color=colors))
                    fig4.add_trace(go.Scatter(x=df.index, y=df['DIF'], line=dict(color='white', width=1.5), name='DIF'))
                    fig4.add_trace(go.Scatter(x=df.index, y=df['DEA'], line=dict(color='yellow', width=1.5), name='DEA'))
                    fig4.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(range=[start_date, last_date]))
                    st.plotly_chart(fig4, use_container_width=True)
                
                with tab5:
                    fig5 = go.Figure()
                    fig5.add_trace(go.Scatter(x=df.index, y=df['BIAS'], line=dict(color='#FFD700', width=2), name='乖離率%'))
                    fig5.add_hline(y=0, line_color="white")
                    fig5.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(range=[start_date, last_date]))
                    st.plotly_chart(fig5, use_container_width=True)

                # --- 指標文字建議 ---
                st.divider()
                st.write("### 📝 指標綜合判斷")
                c1, c2 = st.columns(2)
                with c1:
                    st.info("**📈 技術與趨勢**")
                    st.write(f"● **KD 熱度**：{'🔥 過熱' if k_val > 80 else '❄️ 冷清' if k_val < 20 else '✅ 正常'}")
                    st.write(f"● **MACD 動能**：{'🚀 強勁' if macd_h > 0 else '☁️ 轉弱'}")
                with c2:
                    st.info("**📊 量能與乖離**")
                    st.write(f"● **成交量**：{'💥 爆量' if vol > avg_vol * 1.5 else '☕ 平穩'}")
                    st.write(f"● **乖離率**：{'📏 過大' if abs(bias) > 5 else '穩定'}")

                score = (1 if k_val < 30 else 0) + (1 if macd_h > 0 else 0) + (1 if lp > df['MA20'].iloc[-1] else 0)
                st.subheader("💡 系統最終建議")
                if score >= 2: st.success("**【 綜合評等：強勢看多 】** 適合偏多思考。")
                elif score <= 0: st.error("**【 綜合評等：偏空觀望 】** 指標轉弱，不宜逆勢。")
                else: st.warning("**【 綜合評等：區間盤整 】** 低買高賣。")

        except Exception as e:
            st.error(f"分析異常，原因：{e}")

st.sidebar.markdown("---")
st.sidebar.caption("小白股票診療室 v4.0 | 專業多圖切換版")
