import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# --- 1. 網頁配置 ---
st.set_page_config(page_title="核心數據診斷終端", layout="centered")

# --- 2. 常用資料庫 ---
STOCK_DB = {"2330": "台積電", "2317": "鴻海", "2454": "聯發科", "0050": "元大台灣50", "00878": "國泰高股息", "2314": "台揚", "2634": "漢翔"}

def get_real_chinese_name(symbol):
    try:
        clean_sid = symbol.upper().split('.')[0]
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

# --- 3. 頂部導航 ---
st.title("📊 核心數據診斷終端")
stock_id = st.text_input("輸入代號：", "2330")
analyze_btn = st.button("執行深度診斷", type="primary", use_container_width=True)
st.divider()

if analyze_btn or stock_id:
    sid = stock_id.upper().strip()
    with st.spinner(f'策略數據分析中...'):
        try:
            # 搜尋邏輯
            formatted_id = f"{sid}.TW" if sid.isdigit() else sid
            df = yf.download(formatted_id, period="1y", interval="1d", progress=False)
            if df.empty and formatted_id.endswith(".TW"):
                df = yf.download(formatted_id.replace(".TW", ".TWO"), period="1y", interval="1d", progress=False)

            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

                # 指標計算
                df['MA5'] = df['Close'].rolling(5).mean()
                df['MA20'] = df['Close'].rolling(20).mean()
                df['BIAS'] = ((df['Close'] - df['MA20']) / df['MA20']) * 100
                df['K'] = ((df['Close'] - df['Low'].rolling(9).min()) / (df['High'].rolling(9).max() - df['Low'].rolling(9).min()) * 100).ewm(com=2, adjust=False).mean()
                df['D'] = df['K'].rolling(3).mean()
                ema12, ema26 = df['Close'].ewm(span=12).mean(), df['Close'].ewm(span=26).mean()
                df['DIF'] = ema12 - ema26
                df['DEA'] = df['DIF'].ewm(span=9).mean()
                df['MACD_HIST'] = df['DIF'] - df['DEA']
                high_20 = df['High'].rolling(20).max()

                # 最新數據
                lp = float(df['Close'].iloc[-1])
                ma5_v = float(df['MA5'].iloc[-1])
                k_v, macd_h, bias_v = float(df['K'].iloc[-1]), float(df['MACD_HIST'].iloc[-1]), float(df['BIAS'].iloc[-1])
                supp_10, resi_10 = float(df['Low'].tail(10).min()), float(df['High'].tail(10).max())
                stock_name = get_real_chinese_name(sid)

                st.subheader(f"🏢 {stock_name} ({sid})")
                
                # --- 關鍵價格看板 ---
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📌 現價", f"{lp:.2f}", f"{lp - df['Close'].iloc[-2]:.2f}")
                c2.metric("🚀 買點", f"{ma5_v:.2f}")
                wave_target = max(float(high_20.iloc[-1]), lp * 1.07)
                c3.metric("🎯 賣點", f"{wave_target:.2f}")
                c4.metric("🚨 停損", f"{supp_10 * 0.99:.2f}")

                # --- 圖表顯示區 (修正 X 軸與 Y 軸錯誤) ---
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["K線", "量能", "KD", "MACD", "乖離"])
                last_date = df.index[-1]
                start_date = last_date - pd.Timedelta(days=45) 
                r_df = df[df.index >= start_date]

                with tab1:
                    y_mi, y_ma = r_df['Low'].min() * 0.98, r_df['High'].max() * 1.02
                    fig1 = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線', increasing_line_color='#FF3232', increasing_fillcolor='#FF3232', decreasing_line_color='#00AB5E', decreasing_fillcolor='#00AB5E')])
                    fig1.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='cyan', width=1.5), name='5MA'))
                    fig1.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='20MA'))
                    fig1.update_layout(height=450, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[y_mi, y_ma], fixedrange=False))
                    st.plotly_chart(fig1, use_container_width=True)

                with tab2:
                    v_ma = r_df['Volume'].max() * 1.1
                    fig2 = go.Figure(data=[go.Bar(x=df.index, y=df['Volume'], marker_color=['#FF3232' if c>=o else '#00AB5E' for c,o in zip(df['Close'], df['Open'])])])
                    fig2.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[0, v_ma]))
                    st.plotly_chart(fig2, use_container_width=True)

                with tab3:
                    fig3 = go.Figure()
                    fig3.add_trace(go.Scatter(x=df.index, y=df['K'], line=dict(color='#FF3232', width=2), name='K值'))
                    fig3.add_trace(go.Scatter(x=df.index, y=df['D'], line=dict(color='#00AB5E', width=2), name='D值'))
                    fig3.add_hline(y=80, line_dash="dash", line_color="gray")
                    fig3.add_hline(y=20, line_dash="dash", line_color="gray")
                    # 【修正處】補上 [0, 100] 數值
                    fig3.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[0, 100]))
                    st.plotly_chart(fig3, use_container_width=True)

                with tab4:
                    m_ma = max(r_df['MACD_HIST'].abs().max(), r_df['DIF'].abs().max()) * 1.5
                    fig4 = go.Figure()
                    fig4.add_trace(go.Bar(x=df.index, y=df['MACD_HIST'], marker_color=['#FF3232' if h>=0 else '#00AB5E' for h in df['MACD_HIST']]))
                    fig4.add_trace(go.Scatter(x=df.index, y=df['DIF'], line=dict(color='yellow', width=1.5), name='DIF'))
                    fig4.add_trace(go.Scatter(x=df.index, y=df['DEA'], line=dict(color='cyan', width=1.5), name='DEA'))
                    fig4.update_layout(height=400, showlegend=False, margin=dict(l=5, r=5, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[-m_ma, m_ma]))
                    st.plotly_chart(fig4, use_container_width=True)

                with tab5:
                    b_ma = r_df['BIAS'].abs().max() * 1.4
                    fig5 = go.Figure(data=[go.Scatter(x=df.index, y=df['BIAS'], line=dict(color='#FFD700', width=2))])
                    fig5.add_hline(y=0, line_color="white")
                    fig5.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[-b_ma, b_ma]))
                    st.plotly_chart(fig5, use_container_width=True)

                # --- 最終操作指引 ---
                st.divider()
                st.subheader("💡 實戰操作指引")
                score = (1 if k_v < 50 else 0) + (1 if macd_h > 0 else 0) + (1 if lp > ma5_v else 0)
                if score >= 2:
                    st.success(f"**【 強勢進攻訊號 】**")
                    st.write(f"👉 **操作**：氣勢正旺，目標看 **{wave_target:.2f}** 元。沒破 **{ma5_v:.2f}** 就續抱。")
                elif score <= 0:
                    st.error(f"**【 趨勢轉弱訊號 】**")
                    st.write(f"👉 **建議**：跌破 **{supp_10 * 0.99:.2f}** 務必保命撤離。")
                else:
                    st.warning("**【 震盪整理訊號 】**")
                    st.write(f"👉 **策略**：建議於 **{supp_10:.2f}** 與 **{resi_10:.2f}** 之間操作。")

        except Exception as e: st.error(f"分析異常：{e}")

st.caption("v6.7 | 語法修正與手機視覺優化版")
