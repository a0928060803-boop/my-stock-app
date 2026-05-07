import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# --- 1. 網頁配置 ---
st.set_page_config(page_title="AI 學習診斷終端", layout="centered")

# --- 2. 建立連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_real_chinese_name(symbol):
    STOCK_DB = {"2330": "台積電", "2317": "鴻海", "2454": "聯發科", "0050": "元大台灣50", "00878": "國泰高股息", "2314": "台揚"}
    clean_sid = symbol.upper().split('.')[0]
    return STOCK_DB.get(clean_sid, symbol)

# --- 3. 介面 ---
st.title("📊 智贏股市 AI 學習終端")
stock_id = st.text_input("輸入代號：", "2330")
analyze_btn = st.button("執行診斷並記錄", type="primary", use_container_width=True)

if analyze_btn or stock_id:
    sid = stock_id.upper().strip()
    with st.spinner(f'AI 正在讀取數據...'):
        try:
            formatted_id = f"{sid}.TW" if sid.isdigit() else sid
            df = yf.download(formatted_id, period="1y", interval="1d", progress=False)

            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                
                # 指標計算
                df['MA5'] = df['Close'].rolling(5).mean()
                lp = float(df['Close'].iloc[-1])
                ma5_v = float(df['MA5'].iloc[-1])
                stock_name = get_real_chinese_name(sid)

                # --- A. 讀取記憶 ---
                try:
                    history_df = conn.read(ttl=0)
                    # 避免空表格報錯
                    if not history_df.empty and '股號' in history_df.columns:
                        past = history_df[history_df['股號'] == sid]
                        if not past.empty:
                            last_row = past.iloc[-1]
                            st.info(f"🧠 AI 記憶：上次於 {last_row['日期']} 診斷，當時價格 {last_row['當時價格']}")
                except Exception as e:
                    st.warning(f"讀取資料庫時遇到一點問題（可能是首次建立）：{e}")

                st.subheader(f"🏢 {stock_name} ({sid})")
                st.metric("📌 現價", f"{lp:.2f}")

                # --- B. 【核心除錯】寫入資料庫 ---
                try:
                    new_entry = pd.DataFrame([{
                        "日期": pd.Timestamp.now().strftime('%Y-%m-%d'),
                        "股號": sid,
                        "名稱": stock_name,
                        "建議動作": "買入" if lp > ma5_v else "觀望",
                        "當時價格": lp,
                        "AI優化備註": "系統自動記錄"
                    }])
                    
                    # 重新讀取確保資料最新，然後結合
                    current_df = conn.read(ttl=0)
                    updated_df = pd.concat([current_df, new_entry], ignore_index=True).dropna(axis=1, how='all')
                    
                    # 執行上傳
                    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=updated_df)
                    st.toast("✅ 診斷已存入 Google 表格！")
                except Exception as e:
                    # 如果寫入失敗，這裡會顯示原因
                    st.error(f"❌ 無法寫入試算表：{e}")
                    st.info("請確認：1. 表格共用設為『編輯者』 2. Secrets 網址正確")

                # --- C. 圖表 ---
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線', increasing_line_color='#FF3232', increasing_fillcolor='#FF3232', decreasing_line_color='#00AB5E', decreasing_fillcolor='#00AB5E')])
                fig.update_layout(height=400, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

        except Exception as e: st.error(f"分析異常：{e}")

st.caption("v7.3 | 除錯強化版")
