import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# --- 1. 網頁配置 ---
st.set_page_config(page_title="小白股票診療室 Pro", layout="centered")

# --- 2. 常用資料庫 ---
STOCK_DB = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "0050": "元大台灣50", 
    "00878": "國泰高股息", "2314": "台揚", "2634": "漢翔", "00992B": "統一美債20年"
}

def get_real_chinese_name(symbol):
    try:
        # 修正：處理清單與大小寫邏輯
        sid_raw = symbol.upper().split('.')
        clean_sid = sid_raw[0]
        if clean_sid in STOCK_DB:
            return STOCK_DB[clean_sid]
        
        url = f"https://yahoo.com{symbol}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if res.get('quotes'):
            name = res['quotes'][0].get('shortname', symbol)
            for s in ["Semiconductor", "Manufacturing", "Industry", "Co.", "Ltd.", "Holdings"]:
                name = name.replace(s, "").strip()
            return name
    except:
        pass
    return symbol

# --- 3. 頂部導航輸入區 ---
st.title("🏥 小白股票診療室 Pro")
quick_select = st.selectbox("🔥 熱門標的快速選單", ["手動輸入代號", "2330 台積電", "2317 鴻海", "2634 漢翔", "00878 國泰高股息", "00992B 統一美債", "2314 台揚"])

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

if analyze_btn or stock_id:
    sid = stock_id.upper().strip()
    with st.spinner(f'積極策略掃描中...'):
        try:
            # 搜尋邏輯
            if sid.endswith("B"):
                search_list = [f"{sid}.TWO", f"{sid}.TW"]
            else:
                search_list = [f"{sid}.TW", f"{sid}.TWO", sid]

            df = pd.DataFrame()
            final_sid = sid
            for target in search_list:
                df = yf.download(target, period="1y", interval="1d", progress=False)
                if not df.empty:
                    final_sid = target
                    break

            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # --- 積極型指標計算 ---
                df['MA5'] = df['Close'].rolling(5).mean()
                df['MA20'] = df['Close'].rolling(20).mean()
                df['BIAS'] = ((df['Close'] - df['MA20']) / df['MA20']) * 100
                
                # 計算 KD
                low_9 = df['Low'].rolling(9).min()
                high_9 = df['High'].rolling(9).max()
                df['K'] = ((df['Close'] - low_9) / (high_9 - low_9) * 100).ewm(com=2, adjust=False).mean()
                df['D'] = df['K'].rolling(3).mean()
                
                # 計算 MACD
                ema12 = df['Close'].ewm(span=12, adjust=False).mean()
                ema26 = df['Close'].ewm(span=26, adjust=False).mean()
                df['DIF'] = ema12 - ema26
                df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
                df['MACD_HIST'] = df['DIF'] - df['DEA']

                # 數據提取
                lp = float(df['Close'].iloc[-1])
                ma5_v = float(df['MA5'].iloc[-1])
                ma20_v = float(df['MA20'].iloc[-1])
                supp_10 = float(df['Low'].tail(10).min()) 
                resi_10 = float(df['High'].tail(10).max()) 
                k_v = float(df['K'].iloc[-1])
                macd_h = float(df['MACD_HIST'].iloc[-1])
                bias_v = float(df['BIAS'].iloc[-1])
                vol_now = int(df['Volume'].iloc[-1])
                vol_avg = int(df['Volume'].tail(5).mean())
                stock_name = get_real_chinese_name(final_sid)

                st.subheader(f"🏢 {stock_name} ({sid}) 診斷報告")
                
                # --- 關鍵價格看板 (積極版) ---
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📌 現價", f"{lp:.2f}", f"{lp - df['Close'].iloc[-2]:.2f}")
                
                # 買點積極：參考 5 日線
                buy_p = ma5_v if lp > ma5_v else (ma5_v + supp_10) / 2
                c2.metric("🚀 買點", f"{buy_p:.2f}")
                
                # 賣點積極：10日高或+3%
                sell_p = max(resi_10, lp * 1.03)
                c3.metric("🎯 賣點", f"{sell_p:.2f}")
                
                # 停損緊湊：10日地板價
                c4.metric("🚨 停損", f"{supp_10 * 0.99:.2f}")
                
                # --- 圖表分頁 ---
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["K線", "量能", "KD", "MACD", "乖離"])
                last_date = df.index[-1]
                start_date = last_date - pd.Timedelta(days=45)
                r_df = df[df.index >= start_date]

                with tab1:
                    y_mi = r_df['Low'].min() * 0.98
                    y_ma = r_df['High'].max() * 1.02
                    fig1 = go.Figure(data=[go.Candlestick(
                        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線',
                        increasing_line_color='#FF3232', increasing_fillcolor='#FF3232',
                        decreasing_line_color='#00AB5E', decreasing_fillcolor='#00AB5E'
                    )])
                    fig1.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='cyan', width=1), name='5MA'))
                    fig1.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='20MA'))
                    fig1.update_layout(height=400, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=10, b=0),
                                      xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[y_mi, y_ma]))
                    st.plotly_chart(fig1, use_container_width=True)

                with tab2:
                    v_max = r_df['Volume'].max() * 1.1
                    fig2 = go.Figure(data=[go.Bar(
                        x=df.index, y=df['Volume'], 
                        marker_color=['#FF3232' if c>=o else '#00AB5E' for c,o in zip(df['Close'], df['Open'])]
                    )])
                    fig2.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), 
                                      xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[0, v_max]))
                    st.plotly_chart(fig2, use_container_width=True)

                with tab3:
                    fig3 = go.Figure()
                    fig3.add_trace(go.Scatter(x=df.index, y=df['K'], line=dict(color='#FF3232', width=2), name='K值'))
                    fig3.add_trace(go.Scatter(x=df.index, y=df['D'], line=dict(color='#00AB5E', width=2), name='D值'))
                    fig3.add_hline(y=80, line_dash="dash", line_color="gray")
                    fig3.add_hline(y=20, line_dash="dash", line_color="gray")
                    fig3.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), 
                                      xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[0, 100]))
                    st.plotly_chart(fig3, use_container_width=True)

                with tab4:
                    h_col = "#FF3232" if macd_h >= 0 else "#00AB5E"
                    st.markdown(f"**MACD >** DIF:{df['DIF'].iloc[-1]:.2f} / <span style='color:{h_col}'>HIST:{macd_h:.2f}</span>", unsafe_allow_html=True)
                    m_max = max(r_df['MACD_HIST'].abs().max(), r_df['DIF'].abs().max()) * 1.5
                    fig4 = go.Figure()
                    fig4.add_trace(go.Bar(x=df.index, y=df['MACD_HIST'], marker_color=['#FF3232' if h>=0 else '#00AB5E' for h in df['MACD_HIST']]))
                    fig4.add_trace(go.Scatter(x=df.index, y=df['DIF'], line=dict(color='yellow', width=1.5)))
                    fig4.add_trace(go.Scatter(x=df.index, y=df['DEA'], line=dict(color='cyan', width=1.5)))
                    fig4.update_layout(height=350, showlegend=False, margin=dict(l=5, r=5, t=10, b=0), 
                                      xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[-m_max, m_max]))
                    st.plotly_chart(fig4, use_container_width=True)

                with tab5:
                    b_max = r_df['BIAS'].abs().max() * 1.5
                    fig5 = go.Figure(data=[go.Scatter(x=df.index, y=df['BIAS'], line=dict(color='#FFD700', width=2))])
                    fig5.add_hline(y=0, line_color="white")
                    fig5.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), 
                                      xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[-b_max, b_max]))
                    st.plotly_chart(fig5, use_container_width=True)

                # --- 綜合分析 ---
                st.divider()
                st.write("### 📝 實戰短線行情分析")
                a1, a2 = st.columns(2)
                with a1:
                    st.info("**📈 市場熱度與動能**")
                    st.write(f"● **市場氣氛**：{'大家瘋了！現在進場容易套牢' if k_v > 80 else '超跌，短線反彈機會高' if k_v < 25 else '氣氛穩定'}")
                    st.write(f"● **衝勁動能**：{'油門狂踩！股價衝勁很強' if macd_h > 0 else '動力衰竭，隨時會倒車'}")
                with a2:
                    st.info("**📊 籌碼與保命距離**")
                    st.write(f"● **成交量**：{'大戶進場！爆量變盤訊號' if vol_now > vol_avg * 1.5 else '量能平穩，散戶盤'}")
                    st.write(f"● **防守距離**：{'目前離停損點非常近，請提高警覺' if (lp - (supp_10*0.99))/lp < 0.02 else '距離防守位還有空間'}")

                st.subheader("💡 積極型短線對策")
                score = (1 if k_v < 45 else 0) + (1 if macd_h > 0 else 0) + (1 if lp > ma5_v else 0)
                if score >= 2:
                    st.success(f"**【 目前診斷：多頭進攻，分批切入 】**")
                    st.write(f"👉 **怎麼做？**：股價站在週線({ma5_v:.2f})上。建議在 **{buy_p:.2f}** 附近佈局，目標 **{sell_p:.2f}**。")
                    st.write(f"⚠️ **嚴格防守**：若意外跌破 **{supp_10*0.99:.2f}**，請立刻撤離。")
                elif score <= 0:
                    st.error(f"**【 目前診斷：趨勢轉弱，建議賣出/觀望 】**")
                    st.write(f"👉 **怎麼做？**：買的人都在賠錢。建議在 **{lp:.2f}** 附近減碼，等跌到 **{supp_10:.2f}** 撐住再說。")
                else:
                    st.warning(f"**【 目前診斷：盤整走勢，低買高賣 】**")
                    st.write(f"👉 **怎麼做？**：不追高。在 **{supp_10:.2f}** ~ **{resi_10:.2f}** 區間震盪操作。")

        except Exception as e:
            st.error(f"分析發生異常：{e}")

st.caption("v6.1 | 積極策略全功能版")
