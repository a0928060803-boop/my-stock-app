import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# --- 1. 網頁配置 ---
st.set_page_config(page_title="小白股票診療室 Pro", layout="wide")

# --- 2. 常用資料庫 ---
STOCK_DB = {"2330": "台積電", "2317": "鴻海", "2454": "聯發科", "0050": "元大台灣50", "00878": "國泰高股息", "2314": "台揚"}

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

# --- 3. 側邊欄 ---
st.sidebar.header("🏥 診斷中心")
quick_select = st.sidebar.selectbox("🔥 熱門標的快速選單", ["手動輸入代號", "2330 台積電", "2317 鴻海", "00878 國泰高股息", "2314 台揚"])
default_id = quick_select.split(' ')[0] if quick_select != "手動輸入代號" else "2330"
stock_id = st.sidebar.text_input("請輸入台股/美股/ETF代號：", default_id)
analyze_btn = st.sidebar.button("開始深度分析", type="primary")

# --- 4. 主畫面邏輯 ---
if analyze_btn or stock_id:
    sid = stock_id.upper().strip()
    with st.spinner(f'數據診療中...'):
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
                st.error("🛑 查無數據。")
            else:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # 指標計算
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

                # 提取最新數值
                last_dif, last_dea, last_hist = df['DIF'].iloc[-1], df['DEA'].iloc[-1], df['MACD_HIST'].iloc[-1]

                # 設定區間
                last_date = df.index[-1]
                start_date = last_date - pd.Timedelta(days=60)
                recent_df = df[df.index >= start_date]

                st.title(f"🏢 {get_real_chinese_name(final_id)} ({sid}) 診斷")
                st.divider()

                tab1, tab2, tab3, tab4, tab5 = st.tabs(["K線", "量能", "KD", "MACD", "乖離"])

                with tab1:
                    y_min, y_max = recent_df['Low'].min() * 0.97, recent_df['High'].max() * 1.03
                    fig1 = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線',
                                        increasing_line_color='#FF3232', increasing_fillcolor='#FF3232',
                                        decreasing_line_color='#00AB5E', decreasing_fillcolor='#00AB5E')])
                    fig1.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='月線'))
                    fig1.update_layout(height=450, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=10, b=0),
                                      xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[y_min, y_max], fixedrange=False))
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
                    # --- MACD 專業顯示區 ---
                    h_col = "#FF3232" if last_hist >= 0 else "#00AB5E"
                    st.markdown(f"**MACD(12,26,9) >** <span style='color:yellow'>DIF: {last_dif:.2f}</span>  <span style='color:cyan'>DEA: {last_dea:.2f}</span>  <span style='color:{h_col}'>HIST: {last_hist:.2f}</span>", unsafe_allow_html=True)
                    
                    # 智慧 Y 軸：同時計算柱狀體與曲線
                    max_abs = max(recent_df['MACD_HIST'].abs().max(), recent_df['DIF'].abs().max(), recent_df['DEA'].abs().max())
                    m_range = max_abs * 1.4 if max_abs > 0 else 1.0
                    
                    fig4 = go.Figure()
                    fig4.add_trace(go.Bar(x=df.index, y=df['MACD_HIST'], marker_color=['#FF3232' if h>=0 else '#00AB5E' for h in df['MACD_HIST']]))
                    fig4.add_trace(go.Scatter(x=df.index, y=df['DIF'], line=dict(color='yellow', width=1.5)))
                    fig4.add_trace(go.Scatter(x=df.index, y=df['DEA'], line=dict(color='cyan', width=1.5)))
                    fig4.update_layout(height=450, showlegend=False, margin=dict(l=5, r=5, t=10, b=0), 
                                      xaxis=dict(range=[start_date, last_date], showgrid=False), 
                                      yaxis=dict(range=[-m_range, m_range], gridcolor='#333', zerolinecolor='white'))
                    st.plotly_chart(fig4, use_container_width=True)
                
                with tab5:
                    b_max = recent_df['BIAS'].abs().max() * 1.4
                    fig5 = go.Figure(data=[go.Scatter(x=df.index, y=df['BIAS'], line=dict(color='#FFD700', width=2))])
                    fig5.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[-b_max, b_max]))
                    st.plotly_chart(fig5, use_container_width=True)

                st.divider()
                st.subheader("💡 系統建議")
                k_val, macd_h, lp = float(df['K'].iloc[-1]), float(df['MACD_HIST'].iloc[-1]), float(df['Close'].iloc[-1])
                score = (1 if k_val < 30 else 0) + (1 if macd_h > 0 else 0) + (1 if lp > df['MA20'].iloc[-1] else 0)
                if score >= 2: st.success("強勢看多")
                elif score <= 0: st.error("偏空觀望")
                else: st.warning("區間盤整")

        except Exception as e:
            st.error(f"分析異常。")

st.sidebar.caption("小白股票診療室 v4.5 | 終極視覺版")
