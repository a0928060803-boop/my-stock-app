import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# --- 1. 網頁配置 ---
st.set_page_config(page_title="小白股票診療室 Pro", layout="centered")

# --- 2. 常用資料庫 ---
STOCK_DB = {"2330": "台積電", "2317": "鴻海", "2454": "聯發科", "0050": "元大台灣50", "00878": "國泰高股息", "2314": "台揚", "2634": "漢翔"}

def get_real_chinese_name(symbol):
    try:
        clean_sid = symbol.split('.')[0].upper()
        if clean_sid in STOCK_DB: return STOCK_DB[clean_sid]
        url = f"https://yahoo.com{symbol}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if res.get('quotes'):
            name = res['quotes'][0].get('shortname', symbol)
            for s in ["Semiconductor", "Manufacturing", "Industry", "Co.", "Ltd.", "Holdings"]:
                name = name.replace(s, "").strip()
            return name
    except: pass
    return symbol

# --- 3. 頂部導航輸入區 ---
st.title("🏥 小白股票診療室 Pro")

quick_select = st.selectbox(
    "🔥 熱門標的快速選單",
    ["手動輸入代號", "2330 台積電", "2317 鴻海", "00878 國泰高股息", "2634 漢翔", "2314 台揚"]
)

if quick_select != "手動輸入代號":
    default_id = quick_select.split(' ')[0]
else:
    default_id = "2330"

col_input, col_btn = st.columns([3, 1])
with col_input:
    stock_id = st.text_input("輸入代號：", default_id, label_visibility="collapsed")
with col_btn:
    analyze_btn = st.button("開始診斷", type="primary", use_container_width=True)

st.divider()

# --- 4. 主畫面診斷邏輯 ---
if analyze_btn or stock_id:
    sid = stock_id.upper().strip()
    with st.spinner(f'系統深度診斷中...'):
        try:
            df = pd.DataFrame()
            if any(ext in sid for ext in [".TW", ".TWO", ".US", "^"]):
                search_list = [sid]
            else:
                search_list = [f"{sid}.TW", f"{sid}.TWO"] if not sid.endswith("B") else [f"{sid}.TWO", f"{sid}.TW"]

            final_id = sid
            for target_id in search_list:
                df = yf.download(target_id, period="1y", interval="1d", progress=False)
                if not df.empty:
                    final_id = target_id
                    break
            
            if df.empty:
                st.error("🛑 查無數據，請確認股號。")
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

                lp = float(df['Close'].iloc[-1])
                k_val = float(df['K'].iloc[-1])
                macd_h = float(df['MACD_HIST'].iloc[-1])
                bias = float(df['BIAS'].iloc[-1])
                vol = int(df['Volume'].iloc[-1])
                avg_vol = int(df['Volume'].tail(5).mean())
                stock_name = get_real_chinese_name(final_id)

                st.subheader(f"🏢 {stock_name} ({sid}) 診斷報告")
                
                # --- 圖表分頁顯示 ---
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["K線", "量能", "KD", "MACD", "乖離"])
                last_date = df.index[-1]
                start_date = last_date - pd.Timedelta(days=60)
                recent_df = df[df.index >= start_date]

                with tab1:
                    y_min, y_max = recent_df['Low'].min() * 0.97, recent_df['High'].max() * 1.03
                    fig1 = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線',
                                        increasing_line_color='#FF3232', increasing_fillcolor='#FF3232',
                                        decreasing_line_color='#00AB5E', decreasing_fillcolor='#00AB5E')])
                    fig1.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='月線'))
                    fig1.update_layout(height=400, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=10, b=0),
                                      xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[y_min, y_max]))
                    st.plotly_chart(fig1, use_container_width=True)

                with tab2:
                    v_max = recent_df['Volume'].max() * 1.1
                    fig2 = go.Figure(data=[go.Bar(x=df.index, y=df['Volume'], marker_color=['#FF3232' if c>=o else '#00AB5E' for c,o in zip(df['Close'], df['Open'])])])
                    fig2.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[0, v_max]))
                    st.plotly_chart(fig2, use_container_width=True)

                with tab3:
                    fig3 = go.Figure()
                    fig3.add_trace(go.Scatter(x=df.index, y=df['K'], line=dict(color='#FF3232', width=2), name='K值'))
                    fig3.add_trace(go.Scatter(x=df.index, y=df['D'], line=dict(color='#00AB5E', width=2), name='D值'))
                    fig3.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[0, 100]))
                    st.plotly_chart(fig3, use_container_width=True)

                with tab4:
                    st.markdown(f"**MACD >** DIF: {df['DIF'].iloc[-1]:.2f} / HIST: {macd_h:.2f}")
                    max_abs = max(recent_df['MACD_HIST'].abs().max(), recent_df['DIF'].abs().max()) * 1.4
                    fig4 = go.Figure()
                    fig4.add_trace(go.Bar(x=df.index, y=df['MACD_HIST'], marker_color=['#FF3232' if h>=0 else '#00AB5E' for h in df['MACD_HIST']]))
                    fig4.add_trace(go.Scatter(x=df.index, y=df['DIF'], line=dict(color='yellow', width=1.5)))
                    fig4.update_layout(height=350, showlegend=False, margin=dict(l=5, r=5, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[-max_abs, max_abs]))
                    st.plotly_chart(fig4, use_container_width=True)

                with tab5:
                    b_max = recent_df['BIAS'].abs().max() * 1.4
                    fig5 = go.Figure(data=[go.Scatter(x=df.index, y=df['BIAS'], line=dict(color='#FFD700', width=2))])
                    fig5.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[-b_max, b_max]))
                    st.plotly_chart(fig5, use_container_width=True)

                # --- 綜合分析報告與建議 ---
                st.divider()
                st.write("### 📝 四大指標綜合分析報告")
                c1, c2 = st.columns(2)
                with c1:
                    st.info("**📈 趨勢與動能 (KD / MACD)**")
                    st.write(f"● **KD 指標**：{'🔥 市場過熱，不宜追高' if k_val > 80 else '❄️ 市場冷清，適合撿便宜' if k_val < 20 else '✅ 熱度穩定，適合操作'}")
                    st.write(f"● **MACD 指標**：{'🚀 動能增強，具有攻擊力' if macd_h > 0 else '☁️ 動能衰退，防拉回'}")
                with c2:
                    st.info("**📊 量能與乖離 (VOL / BIAS)**")
                    st.write(f"● **成交量**：{'💥 異常爆量，關鍵轉折' if vol > avg_vol * 1.5 else '☕ 量能平穩，正常交易'}")
                    st.write(f"● **乖離率**：{'📏 乖離過大，近期校正' if abs(bias) > 5 else '穩定，趨勢健康'}")

                st.subheader("💡 最終投資建議與對策")
                score = (1 if k_val < 30 else 0) + (1 if macd_h > 0 else 0) + (1 if lp > df['MA20'].iloc[-1] else 0)
                if score >= 2:
                    st.success("**【 診斷結果：強勢格局，建議購入/續抱 】**")
                elif score <= 0:
                    st.error("**【 診斷結果：趨勢轉弱，建議賣出/觀望 】**")
                else:
                    st.warning("**【 診斷結果：區間震盪，建議中性看待 】**")

        except Exception as e:
            st.error(f"分析異常。")

st.caption("v5.2 | 功能全整合版")
