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

# --- 3. 頂部導航輸入區 ---
st.title("🏥 小白股票診療室 Pro")
quick_select = st.selectbox("🔥 熱門標的快速選單", ["手動輸入代號", "2330 台積電", "2317 鴻海", "2634 漢翔", "00878 國泰高股息", "2314 台揚"])
default_id = quick_select.split(' ')[0] if quick_select != "手動輸入代號" else "2330"

col_input, col_btn = st.columns(2)
with col_input:
    stock_id = st.text_input("輸入代號：", default_id, label_visibility="collapsed")
with col_btn:
    analyze_btn = st.button("開始診斷", type="primary", use_container_width=True)

st.divider()

if analyze_btn or stock_id:
    sid = stock_id.upper().strip()
    with st.spinner(f'專業分析中...'):
        try:
            formatted_id = f"{sid}.TW" if sid.isdigit() else sid
            df = yf.download(formatted_id, period="1y", interval="1d", progress=False)
            if df.empty and formatted_id.endswith(".TW"):
                df = yf.download(formatted_id.replace(".TW", ".TWO"), period="1y", interval="1d", progress=False)

            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

                # --- 指標計算 ---
                df['MA20'] = df['Close'].rolling(20).mean()
                df['BIAS'] = ((df['Close'] - df['MA20']) / df['MA20']) * 100
                low_9, high_9 = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
                df['K'] = ((df['Close'] - low_9) / (high_9 - low_9) * 100).ewm(com=2, adjust=False).mean()
                df['D'] = df['K'].rolling(3).mean()
                ema12 = df['Close'].ewm(span=12, adjust=False).mean()
                ema26 = df['Close'].ewm(span=26, adjust=False).mean()
                df['DIF'] = ema12 - ema26
                df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
                df['MACD_HIST'] = df['DIF'] - df['DEA']

                lp, m20_v, k_v, macd_h, bias_v = float(df['Close'].iloc[-1]), float(df['MA20'].iloc[-1]), float(df['K'].iloc[-1]), float(df['MACD_HIST'].iloc[-1]), float(df['BIAS'].iloc[-1])
                supp, resi = float(df['Low'].tail(20).min()), float(df['High'].tail(20).max())
                stock_name = get_real_chinese_name(sid)

                st.subheader(f"🏢 {stock_name} ({sid}) 診斷報告")
                
                # --- 關鍵價格看板 ---
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📌 現價", f"{lp:.2f}", f"{lp - df['Close'].iloc[-2]:.2f}")
                c2.metric("💡 買點", f"{m20_v if lp > m20_v else supp:.2f}")
                c3.metric("🎯 賣點", f"{resi:.2f}")
                c4.metric("🚨 停損", f"{supp * 0.99:.2f}")
                
                # --- 圖表分頁繪製 ---
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["K線", "量能", "KD", "MACD", "乖離"])
                last_date, start_date = df.index[-1], df.index[-1] - pd.Timedelta(days=60)
                r_df = df[df.index >= start_date]

                with tab1:
                    y_mi, y_ma = r_df['Low'].min() * 0.97, r_df['High'].max() * 1.03
                    fig1 = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線', increasing_line_color='#FF3232', increasing_fillcolor='#FF3232', decreasing_line_color='#00AB5E', decreasing_fillcolor='#00AB5E')])
                    fig1.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='月線'))
                    fig1.update_layout(height=400, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[y_mi, y_ma]))
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
                    fig3.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[0, 100]))
                    st.plotly_chart(fig3, use_container_width=True)

                with tab4:
                    st.markdown(f"**MACD >** DIF:{df['DIF'].iloc[-1]:.2f} / <span style='color:#FF3232'>HIST:{macd_h:.2f}</span>", unsafe_allow_html=True)
                    m_ma = max(r_df['MACD_HIST'].abs().max(), r_df['DIF'].abs().max()) * 1.4
                    fig4 = go.Figure()
                    fig4.add_trace(go.Bar(x=df.index, y=df['MACD_HIST'], marker_color=['#FF3232' if h>=0 else '#00AB5E' for h in df['MACD_HIST']]))
                    fig4.add_trace(go.Scatter(x=df.index, y=df['DIF'], line=dict(color='yellow', width=1.5)))
                    fig4.add_trace(go.Scatter(x=df.index, y=df['DEA'], line=dict(color='cyan', width=1.5)))
                    fig4.update_layout(height=350, showlegend=False, margin=dict(l=5, r=5, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[-m_ma, m_ma]))
                    st.plotly_chart(fig4, use_container_width=True)

                with tab5:
                    b_ma = r_df['BIAS'].abs().max() * 1.4
                    fig5 = go.Figure(data=[go.Scatter(x=df.index, y=df['BIAS'], line=dict(color='#FFD700', width=2))])
                    fig5.add_hline(y=0, line_color="white")
                    fig5.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[-b_ma, b_ma]))
                    st.plotly_chart(fig5, use_container_width=True)

                # --- 分析報告 ---
                st.divider()
                st.write("### 📝 聽得懂的行情分析")
                a1, a2 = st.columns(2)
                with a1:
                    st.info("**📈 市場情緒 (KD/MACD)**")
                    st.write(f"● **熱度**：{'過熱！現在進場容易套牢' if k_v > 80 else '冷清，適合分批撿便宜' if k_v < 20 else '氣氛穩定'}")
                    st.write(f"● **動能**：{'油門踩到底，股價正在衝' if macd_h > 0 else '動力減弱，小心隨時倒車'}")
                with a2:
                    st.info("**📊 籌碼與距離 (VOL/BIAS)**")
                    st.write(f"● **成交量**：{'今日有大戶進場爆量' if int(df['Volume'].iloc[-1]) > int(df['Volume'].tail(5).mean()) * 1.5 else '量能平穩，散戶盤'}")
                    st.write(f"● **乖離率**：{'跑太遠了，小心吸回月線' if abs(bias_v) > 5 else '距離健康'}")

                st.subheader("💡 最終投資對策")
                score = (1 if k_v < 40 else 0) + (1 if macd_h > 0 else 0) + (1 if lp > m20_v else 0)
                if score >= 2: st.success(f"**強勢格局，推薦買入/續抱**。建議：{m20_v:.2f}。目標：{resi:.2f}。")
                elif score <= 0: st.error(f"**氣氛不對，建議賣出/觀望**。減碼點：{lp:.2f}。支撐：{supp:.2f}。")
                else: st.warning(f"**盤整走勢，建議低買高賣**。區間：{supp:.2f} ~ {resi:.2f}。")

        except Exception as e:
            st.error(f"分析異常：{e}")

st.caption("v5.7 | 圖表全補齊版")
