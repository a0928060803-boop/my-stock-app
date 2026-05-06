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
    with st.spinner(f'策略數據計算中...'):
        try:
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
                low_10, high_10 = df['Low'].rolling(10).min(), df['High'].rolling(10).max()
                high_20 = df['High'].rolling(20).max() # 用於大波段參考
                
                # KD & MACD (維持原本邏輯)
                df['K'] = ((df['Close'] - df['Low'].rolling(9).min()) / (df['High'].rolling(9).max() - df['Low'].rolling(9).min()) * 100).ewm(com=2, adjust=False).mean()
                ema12, ema26 = df['Close'].ewm(span=12).mean(), df['Close'].ewm(span=26).mean()
                df['MACD_HIST'] = (ema12 - ema26) - (ema12 - ema26).ewm(span=9).mean()

                lp = float(df['Close'].iloc[-1])
                ma5_v = float(df['MA5'].iloc[-1])
                supp_10 = float(df['Low'].tail(10).min()) 
                k_v = float(df['K'].iloc[-1])
                macd_h = float(df['MACD_HIST'].iloc[-1])
                bias_v = float(df['BIAS'].iloc[-1])
                stock_name = get_real_chinese_name(sid)

                st.subheader(f"🏢 {stock_name} ({sid})")
                
                # --- [實戰核心] 買賣點重新定義 ---
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📌 現價", f"{lp:.2f}", f"{lp - df['Close'].iloc[-2]:.2f}")
                
                # 買點：強勢股回檔 5MA 為最佳介入點
                buy_p = ma5_v
                c2.metric("🚀 買點(5MA)", f"{buy_p:.2f}")
                
                # 賣點：改用「分批獲利」邏輯。取 10日高與 20日高的平均，或是現價 + 7% (波段目標)
                wave_target = max(float(high_20.iloc[-1]), lp * 1.07)
                c3.metric("🎯 賣點(波段)", f"{wave_target:.2f}")
                
                # 停損：維持 10日低點，因為短線結構破壞必須快逃
                stop_l = supp_10 * 0.99
                c4.metric("🚨 停損(保命)", f"{stop_l:.2f}")
                
                # --- 圖表與報告 (略，同前版邏輯) ---
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
                # ... (Tab 2-5 維持 v6.1 代碼) ...

                st.divider()
                # --- 最終對策白話文優化 ---
                st.subheader("💡 實戰操作指引")
                score = (1 if k_v < 50 else 0) + (1 if macd_h > 0 else 0) + (1 if lp > ma5_v else 0)
                
                if score >= 2:
                    st.success(f"**【 強勢進攻訊號 】**")
                    st.write(f"👉 **操作**：目前處於上升軌道，不急著賣。目標價設定在 **{wave_target:.2f}** 元。")
                    st.write(f"👉 **心法**：只要收盤沒跌破 **{ma5_v:.2f}** (5日線)，就繼續抱著讓利潤奔跑！")
                elif score <= 0:
                    st.error(f"**【 趨勢轉弱訊號 】**")
                    st.write(f"👉 **操作**：氣氛轉冷，若已持股且跌破 **{stop_l:.2f}** 務必撤離。")
                    st.write(f"👉 **心法**：空手者不要去接掉下來的刀子，等站回 5 日線再說。")
                else:
                    st.warning(f"**【 震盪整理訊號 】**")
                    st.write(f"👉 **操作**：沒有方向，適合在 **{supp_10:.2f}** 與 **{resi_10:.2f}** 之間低買高賣。")

        except Exception as e: st.error(f"錯誤：{e}")
