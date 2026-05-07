import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from streamlit_gsheets import GSheetsConnection

# --- 1. 網頁與雲端連線配置 ---
st.set_page_config(page_title="智贏股市 AI 學習終端", layout="centered")
conn = st.connection("gsheets", type=GSheetsConnection)

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
            for s in ["Semiconductor", "Manufacturing", "Co.", "Ltd."]: name = name.replace(s, "").strip()
            return name
    except: pass
    return symbol

# --- 3. 頂部輸入區 ---
st.title("📊 智贏股市 AI 學習終端")
stock_id = st.text_input("輸入代號 (系統將自動同步雲端大腦)：", "2330")
analyze_btn = st.button("執行 AI 深度診斷", type="primary", use_container_width=True)
st.divider()

if analyze_btn or stock_id:
    sid = stock_id.upper().strip()
    with st.spinner(f'AI 正在學習歷史紀錄並分析行情...'):
        try:
            formatted_id = f"{sid}.TW" if sid.isdigit() else sid
            df = yf.download(formatted_id, period="1y", interval="1d", progress=False)
            if df.empty:
                df = yf.download(formatted_id.replace(".TW", ".TWO"), period="1y", interval="1d", progress=False)

            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

                # --- 積極型指標計算 ---
                df['MA5'] = df['Close'].rolling(5).mean()
                df['MA20'] = df['Close'].rolling(20).mean()
                df['K'] = ((df['Close'] - df['Low'].rolling(9).min()) / (df['High'].rolling(9).max() - df['Low'].rolling(9).min()) * 100).ewm(com=2, adjust=False).mean()
                ema12, ema26 = df['Close'].ewm(span=12).mean(), df['Close'].ewm(span=26).mean()
                df['MACD_HIST'] = (ema12 - ema26) - (ema12 - ema26).ewm(span=9).mean()
                
                lp = float(df['Close'].iloc[-1])
                ma5_v = float(df['MA5'].iloc[-1])
                supp_10 = float(df['Low'].tail(10).min())
                resi_20 = float(df['High'].tail(20).max())
                k_v = float(df['K'].iloc[-1])
                macd_h = float(df['MACD_HIST'].iloc[-1])
                stock_name = get_real_chinese_name(sid)

                # --- A. [核心] 讀取歷史記憶與檢討 ---
                try:
                    history = conn.read(ttl=0)
                    past = history[history['股號'] == sid]
                    if not past.empty:
                        last_row = past.iloc[-1]
                        old_p = float(last_row['當時價格'])
                        p_diff = (lp - old_p) / old_p * 100
                        st.info(f"🧠 **AI 記憶回顧**：上次於 {last_row['日期']} 看診，當時建議【{last_row['建議動作']}】。目前價格變動：{p_diff:.1f}%。")
                except:
                    st.write("🔄 正在初始化雲端資料庫...")

                # --- B. 關鍵價格看板 ---
                st.subheader(f"🏢 {stock_name} ({sid})")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📌 現價", f"{lp:.2f}", f"{lp - df['Close'].iloc[-2]:.2f}")
                c2.metric("🚀 買點", f"{ma5_v:.2f}")
                wave_target = max(resi_20, lp * 1.07)
                c3.metric("🎯 賣點", f"{wave_target:.2f}")
                c4.metric("🚨 停損", f"{supp_10 * 0.99:.2f}")

                # --- C. [核心] 自動更新診斷紀錄至 Google Sheets ---
                try:
                    # 決定當下建議
                    score = (1 if k_v < 50 else 0) + (1 if macd_h > 0 else 0) + (1 if lp > ma5_v else 0)
                    action = "建議買入" if score >= 2 else "建議賣出" if score <= 0 else "觀望整理"
                    
                    new_log = pd.DataFrame([{
                        "日期": pd.Timestamp.now().strftime('%Y-%m-%d'),
                        "股號": sid,
                        "名稱": stock_name,
                        "建議動作": action,
                        "當時價格": lp,
                        "AI優化備註": f"KD:{k_v:.0f}/MACD:{macd_h:.2f}"
                    }])
                    
                    # 讀取、結合、並上傳回表格
                    all_data = pd.concat([history, new_log], ignore_index=True) if 'history' in locals() else new_log
                    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=all_data)
                    st.toast("✅ 數據已寫入雲端大腦")
                except:
                    pass

                # --- D. 圖表分頁 ---
                tab1, tab2 = st.tabs(["K線走勢", "其他指標"])
                last_date, start_date = df.index[-1], df.index[-1] - pd.Timedelta(days=45)
                r_df = df[df.index >= start_date]
                with tab1:
                    y_mi, y_ma = r_df['Low'].min() * 0.98, r_df['High'].max() * 1.02
                    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線', increasing_line_color='#FF3232', increasing_fillcolor='#FF3232', decreasing_line_color='#00AB5E', decreasing_fillcolor='#00AB5E')])
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='cyan', width=1.5), name='5MA'))
                    fig.update_layout(height=450, xaxis_rangeslider_visible=False, xaxis=dict(range=[start_date, last_date]), yaxis=dict(range=[y_mi, y_ma], fixedrange=False))
                    st.plotly_chart(fig, use_container_width=True)
                with tab2:
                    st.info("請切換分頁查看專業指標數據 (代碼同 v6.7)")

        except Exception as e:
            st.error(f"分析異常：{e}")

st.caption("v7.2 | AI 雲端大腦同步版")
