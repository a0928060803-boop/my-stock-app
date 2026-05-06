import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# --- 1. 網頁配置 ---
st.set_page_config(page_title="核心數據診斷終端", layout="centered")

# --- 2. 常用資料庫 ---
STOCK_DB = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "0050": "元大台灣50", 
    "00878": "國泰高股息", "2314": "台揚", "2634": "漢翔", "00992B": "統一美債20年"
}

def get_real_chinese_name(symbol):
    try:
        # 處理代號比對 (例如 2317.TW -> 2317)
        clean_sid = symbol.upper().split('.')[0]
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

# --- 3. 頂部導航輸入區 (已取消快速選單) ---
st.title("📊 核心數據診斷終端")
st.write("請輸入股票或 ETF 代號進行深度數據診斷")

col_input, col_btn = st.columns([3, 1]) # 設定比例讓輸入框寬一點
with col_input:
    stock_id = st.text_input("輸入代號 (如: 2330, 00878, TSLA)：", "2330", label_visibility="collapsed")
with col_btn:
    analyze_btn = st.button("執行診斷", type="primary", use_container_width=True)

st.divider()

# --- 4. 主畫面診斷邏輯 ---
if analyze_btn or stock_id:
    sid = stock_id.upper().strip()
    with st.spinner(f'數據流分析中...'):
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
                low_9 = df['Low'].rolling(9).min()
                high_9 = df['High'].rolling(9).max()
                df['K'] = ((df['Close'] - low_9) / (high_9 - low_9) * 100).ewm(com=2, adjust=False).mean()
                df['D'] = df['K'].rolling(3).mean()
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

                st.subheader(f"🏢 {stock_name} ({sid})")
                
                # --- 關鍵價格看板 ---
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📌 現價", f"{lp:.2f}", f"{lp - df['Close'].iloc[-2]:.2f}")
                buy_p = ma5_v if lp > ma5_v else (ma5_v + supp_10) / 2
                c2.metric("🚀 買點", f"{buy_p:.2f}")
                c3.metric("🎯 賣點", f"{max(resi_10, lp * 1.03):.2f}")
                c4.metric("🚨 停損", f"{supp_10 * 0.99:.2f}")
                
                # --- 圖表分頁 ---
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["K線", "量能", "KD", "MACD", "乖離"])
                last_date, start_date = df.index[-1], df.index[-1] - pd.Timedelta(days=60)
                r_df = df[df.index >= start_date]

                with tab1:
                    y_mi, y_ma = r_df['Low'].min() * 0.98, r_df['High'].max() * 1.02
                    fig1 = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線', increasing_line_color='#FF3232', increasing_fillcolor='#FF3232', decreasing_line_color='#00AB5E', decreasing_fillcolor='#00AB5E')])
                    fig1.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='cyan', width=1), name='5MA'))
                    fig1.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='20MA'))
                    fig1.update_layout(height=400, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[y_mi, y_ma]))
                    st.plotly_chart(fig1, use_container_width=True)

                with tab2:
                    v_max = r_df['Volume'].max() * 1.1
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
                    m_max = max(r_df['MACD_HIST'].abs().max(), r_df['DIF'].abs().max()) * 1.5
                    fig4 = go.Figure()
                    fig4.add_trace(go.Bar(x=df.index, y=df['MACD_HIST'], marker_color=['#FF3232' if h>=0 else '#00AB5E' for h in df['MACD_HIST']]))
                    fig4.add_trace(go.Scatter(x=df.index, y=df['DIF'], line=dict(color='yellow', width=1.5)))
                    fig4.add_trace(go.Scatter(x=df.index, y=df['DEA'], line=dict(color='cyan', width=1.5)))
                    fig4.update_layout(height=400, showlegend=False, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[-m_max, m_max]))
                    st.plotly_chart(fig4, use_container_width=True)

                with tab5:
                    b_max = r_df['BIAS'].abs().max() * 1.5
                    fig5 = go.Figure(data=[go.Scatter(x=df.index, y=df['BIAS'], line=dict(color='#FFD700', width=2))])
                    fig5.add_hline(y=0, line_color="white")
                    fig5.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[-b_max, b_max]))
                    st.plotly_chart(fig5, use_container_width=True)

                # --- 綜合分析報告 ---
                st.divider()
                st.write("### 📝 實戰短線行情分析")
                a1, a2 = st.columns(2)
                with a1:
                    st.info("**📈 市場情緒**")
                    st.write(f"● **熱度**：{'過熱！短線宜觀望' if k_v > 80 else '超跌，短線有反彈機會' if k_v < 25 else '氣氛穩定'}")
                    st.write(f"● **動能**：{'油門踩到底，衝勁強' if macd_h > 0 else '動力衰竭，隨時熄火'}")
                with a2:
                    st.info("**📊 籌碼與保命距離**")
                    st.write(f"● **成交量**：{'爆量變盤訊號' if vol_now > vol_avg * 1.5 else '量能平穩'}")
                    st.write(f"● **防守**：{'目前離停損點非常近' if (lp - (supp_10*0.99))/lp < 0.02 else '距離防守位還有空間'}")

                st.subheader("💡 積極型短線對策")
                score = (1 if k_v < 45 else 0) + (1 if macd_h > 0 else 0) + (1 if lp > ma5_v else 0)
                if score >= 2:
                    st.success(f"**強勢多頭，分批切入**。買點建議：{buy_p:.2f}。")
                elif score <= 0:
                    st.error(f"**趨勢轉弱，建議賣出**。若有持股請考慮於 {lp:.2f} 附近減碼。")
                else:
                    st.warning(f"**盤整走勢，建議觀望**。適合在 {supp_10:.2f} ~ {resi_10:.2f} 低買高賣。")

        except Exception as e:
            st.error(f"分析異常。")

st.caption("核心數據診斷終端 | 視覺與邏輯優化版")
