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
        clean_sid = symbol.upper().split('.')
        if clean_sid in STOCK_DB: return STOCK_DB[clean_sid]
        url = f"https://yahoo.com{symbol}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if res.get('quotes'):
            name = res['quotes'].get('shortname', symbol)
            for s in ["Semiconductor", "Manufacturing", "Industry", "Co.", "Ltd.", "Holdings"]:
                name = name.replace(s, "").strip()
            return name
    except: pass
    return symbol

# --- 3. 頂部導航輸入區 ---
st.title("🏥 小白股票診療室 Pro")
quick_select = st.selectbox("🔥 熱門標的快速選單", ["手動輸入代號", "2330 台積電", "2317 鴻海", "2634 漢翔", "00878 國泰高股息", "2314 台揚"])
default_id = quick_select.split(' ') if quick_select != "手動輸入代號" else "2330"

col_input, col_btn = st.columns(2)
with col_input:
    stock_id = st.text_input("輸入代號：", default_id, label_visibility="collapsed")
with col_btn:
    analyze_btn = st.button("開始診斷", type="primary", use_container_width=True)

st.divider()

if analyze_btn or stock_id:
    sid = stock_id.upper().strip()
    with st.spinner(f'積極策略掃描中...'):
        try:
            formatted_id = f"{sid}.TW" if sid.isdigit() else sid
            df = yf.download(formatted_id, period="1y", interval="1d", progress=False)
            if df.empty and formatted_id.endswith(".TW"):
                df = yf.download(formatted_id.replace(".TW", ".TWO"), period="1y", interval="1d", progress=False)

            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

                # --- 積極型指標計算 ---
                df['MA5'] = df['Close'].rolling(5).mean()
                df['MA20'] = df['Close'].rolling(20).mean()
                df['BIAS'] = ((df['Close'] - df['MA20']) / df['MA20']) * 100
                low_10 = df['Low'].rolling(10).min()   # 改為 10 日
                high_10 = df['High'].rolling(10).max() # 改為 10 日
                df['K'] = ((df['Close'] - df['Low'].rolling(9).min()) / (df['High'].rolling(9).max() - df['Low'].rolling(9).min()) * 100).ewm(com=2, adjust=False).mean()
                df['D'] = df['K'].rolling(3).mean()
                ema12, ema26 = df['Close'].ewm(span=12).mean(), df['Close'].ewm(span=26).mean()
                df['MACD_HIST'] = (ema12 - ema26) - (ema12 - ema26).ewm(span=9).mean()
                df['DIF'] = ema12 - ema26

                lp = float(df['Close'].iloc[-1])
                ma5_v = float(df['MA5'].iloc[-1])
                ma20_v = float(df['MA20'].iloc[-1])
                supp_10 = float(df['Low'].tail(10).min()) # 10日地板
                resi_10 = float(df['High'].tail(10).max()) # 10日天花板
                k_v = float(df['K'].iloc[-1])
                macd_h = float(df['MACD_HIST'].iloc[-1])
                bias_v = float(df['BIAS'].iloc[-1])
                vol_now = int(df['Volume'].iloc[-1])
                vol_avg = int(df['Volume'].tail(5).mean())
                stock_name = get_real_chinese_name(sid)

                st.subheader(f"🏢 {stock_name} ({sid}) 診斷報告")
                
                # --- 關鍵價格看板 (積極調整版) ---
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📌 現價", f"{lp:.2f}", f"{lp - df['Close'].iloc[-2]:.2f}")
                
                # 買點積極化：參考 5 日線 (週線)
                buy_p = ma5_v if lp > ma5_v else (ma5_v + supp_10) / 2
                c2.metric("🚀 積極買點", f"{buy_p:.2f}")
                
                # 賣點積極化：看 10 日高點或現價 + 3%
                sell_p = max(resi_10, lp * 1.03)
                c3.metric("🎯 短線賣點", f"{sell_p:.2f}")
                
                # 停損緊湊化：10 日最低價打 99.5 折 (0.5% 緩衝)
                stop_l = supp_10 * 0.995
                c4.metric("🚨 緊湊停損", f"{stop_l:.2f}")
                
                # --- 圖表分頁 ---
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["K線", "量能", "KD", "MACD", "乖離"])
                last_date, start_date = df.index[-1], df.index[-1] - pd.Timedelta(days=45)
                r_df = df[df.index >= start_date]

                with tab1:
                    y_mi, y_ma = r_df['Low'].min() * 0.98, r_df['High'].max() * 1.02
                    fig1 = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線', increasing_line_color='#FF3232', increasing_fillcolor='#FF3232', decreasing_line_color='#00AB5E', decreasing_fillcolor='#00AB5E')])
                    fig1.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='cyan', width=1), name='5MA'))
                    fig1.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='20MA'))
                    fig1.update_layout(height=400, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[y_mi, y_ma]))
                    st.plotly_chart(fig1, use_container_width=True)

                with tab4:
                    m_ma = max(r_df['MACD_HIST'].abs().max(), r_df['DIF'].abs().max()) * 1.4
                    fig4 = go.Figure()
                    fig4.add_trace(go.Bar(x=df.index, y=df['MACD_HIST'], marker_color=['#FF3232' if h>=0 else '#00AB5E' for h in df['MACD_HIST']]))
                    fig4.add_trace(go.Scatter(x=df.index, y=df['DIF'], line=dict(color='yellow', width=1.5)))
                    fig4.update_layout(height=350, showlegend=False, margin=dict(l=5, r=5, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[-m_ma, m_ma]))
                    st.plotly_chart(fig4, use_container_width=True)
                
                # ... (其餘圖表 Tab 2, 3, 5 維持 v5.7 穩定邏輯) ...
                with tab2:
                    v_ma = r_df['Volume'].max() * 1.1
                    fig2 = go.Figure(data=[go.Bar(x=df.index, y=df['Volume'], marker_color=['#FF3232' if c>=o else '#00AB5E' for c,o in zip(df['Close'], df['Open'])])])
                    fig2.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[0, v_ma])); st.plotly_chart(fig2, use_container_width=True)
                with tab3:
                    fig3 = go.Figure(); fig3.add_trace(go.Scatter(x=df.index, y=df['K'], line=dict(color='#FF3232', width=2), name='K值')); fig3.add_trace(go.Scatter(x=df.index, y=df['D'], line=dict(color='#00AB5E', width=2), name='D值')); fig3.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=)); st.plotly_chart(fig3, use_container_width=True)
                with tab5:
                    b_ma = r_df['BIAS'].abs().max() * 1.4; fig5 = go.Figure(data=[go.Scatter(x=df.index, y=df['BIAS'], line=dict(color='#FFD700', width=2))]); fig5.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[-b_ma, b_ma])); st.plotly_chart(fig5, use_container_width=True)

                # --- 積極型操作報告 ---
                st.divider()
                st.write("### 📝 實戰短線行情分析")
                a1, a2 = st.columns(2)
                with a1:
                    st.info("**📈 搶錢動能 (短線核心)**")
                    st.write(f"● **熱度**：{'過熱！短線不要再追了' if k_v > 80 else '超跌，短線反彈機會高' if k_v < 25 else '氣氛穩定，可以小試身手'}")
                    st.write(f"● **動能**：{'油門狂踩！股價衝勁很強' if macd_h > 0 else '動力衰竭，隨時會熄火'}")
                with a2:
                    st.info("**📊 籌碼與保命距離**")
                    st.write(f"● **量能**：{'大戶進場，成交量爆發' if vol_now > vol_avg * 1.5 else '量能一般，維持現狀'}")
                    st.write(f"● **防守**：{'目前離停損點非常近，請提高警覺' if (lp - stop_l)/lp < 0.02 else '距離防守位還有空間'}")

                st.subheader("💡 積極型短線對策")
                score = (1 if k_v < 45 else 0) + (1 if macd_h > 0 else 0) + (1 if lp > ma5_v else 0)
                if score >= 2:
                    st.success(f"**【 目前診斷：多頭進攻，分批切入 】**")
                    st.write(f"👉 **策略**：股價站上週線，氣勢正旺。建議在 **{buy_p:.2f}** 附近佈局，目標 **{sell_p:.2f}**。")
                    st.write(f"⚠️ **嚴格防守**：若跌破 10 日地板 **{stop_l:.2f}**，請立刻撤離，不留戀！")
                elif score <= 0:
                    st.error(f"**【 目前診斷：空方走勢，嚴禁接刀 】**")
                    st.write(f"👉 **策略**：短線結構已壞。若有持股建議於 **{lp:.2f}** 撤出。")
                    st.write(f"👉 **等待**：直到站回週線 **{ma5_v:.2f}** 再回頭看診。")
                else:
                    st.warning(f"**【 目前診斷：短線整理，不急進場 】**")
                    st.write(f"👉 **策略**：在 **{supp_10:.2f}** 與 **{resi_10:.2f}** 之間玩短打。")

        except Exception as e:
            st.error(f"分析異常。")

st.caption("v6.0 | 積極短線決策版")
