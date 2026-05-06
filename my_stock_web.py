import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# --- 1. 網頁基礎配置 ---
st.set_page_config(page_title="小白股票診療室 Pro", layout="wide")

# --- 2. 常用台股資料庫 ---
STOCK_DB = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "0050": "元大台灣50",
    "00878": "國泰高股息", "00929": "復華科技優息", "00679B": "元大美債20年",
    "00937B": "群益ESG投等債20+", "00992B": "統一美債20年"
}

def get_real_chinese_name(symbol):
    clean_sid = symbol.split('.')[0].upper()
    if clean_sid in STOCK_DB: return STOCK_DB[clean_sid]
    try:
        url = f"https://yahoo.com{symbol}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if res.get('quotes'):
            name = res['quotes'][0].get('shortname', symbol)
            for s in ["Semiconductor", "Manufacturing", "Industry", "Co.", "Ltd.", "Holdings"]:
                name = name.replace(s, "").strip()
            return name
    except: pass
    return symbol

# --- 3. 側邊欄導航 ---
st.sidebar.header("🏥 診斷中心")
quick_select = st.sidebar.selectbox(
    "🔥 熱門標的快速選單",
    ["手動輸入代號", "2330 台積電", "2317 鴻海", "00878 國泰高股息", "00679B 元大美債", "00937B 群益債券", "00992B 統一美債"]
)

default_id = quick_select.split(' ')[0] if quick_select != "手動輸入代號" else "2330"
stock_id = st.sidebar.text_input("請輸入台股/美股/ETF代號：", default_id)
analyze_btn = st.sidebar.button("開始深度分析", type="primary")

# --- 4. 主畫面邏輯 ---
if analyze_btn or stock_id:
    sid = stock_id.upper().strip()
    
    with st.spinner(f'系統正在為您搜尋 {sid} 的歷史數據...'):
        try:
            # 【核心修正：雙向搜尋邏輯】
            df = pd.DataFrame()
            
            # A. 判斷格式
            if sid.endswith(".TW") or sid.endswith(".TWO") or sid.endswith(".US") or sid.startswith("^"):
                search_list = [sid]
            elif sid.isalpha() and len(sid) >= 2: 
                search_list = [sid] # 美股
            else:
                # 台股：債券ETF(B結尾)優先查 .TWO，其餘優先查 .TW
                if sid.endswith("B"):
                    search_list = [f"{sid}.TWO", f"{sid}.TW"]
                else:
                    search_list = [f"{sid}.TW", f"{sid}.TWO"]

            # B. 執行循環搜尋直到找到資料
            final_id = sid
            for target_id in search_list:
                df = yf.download(target_id, period="1y", interval="1d", progress=False)
                if not df.empty:
                    final_id = target_id
                    break
            
            if df.empty:
                st.error(f"🛑 查無數據。請確認代號【{stock_id}】是否正確。債券型ETF建議輸入完整的 00992B")
            else:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # 指標計算
                df['MA20'] = df['Close'].rolling(20).mean()
                df['BIAS'] = ((df['Close'] - df['MA20']) / df['MA20']) * 100
                low_9, high_9 = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
                rsv = (df['Close'] - low_9) / (high_9 - low_9) * 100
                df['K'] = rsv.ewm(com=2, adjust=False).mean()
                
                # MACD 計算
                ema12 = df['Close'].ewm(span=12, adjust=False).mean()
                ema26 = df['Close'].ewm(span=26, adjust=False).mean()
                df['DIF'] = ema12 - ema26
                df['MACD_HIST'] = df['DIF'] - df['DIF'].ewm(span=9, adjust=False).mean()

                lp = float(df['Close'].iloc[-1])
                k_val = float(df['K'].iloc[-1])
                macd_h = float(df['MACD_HIST'].iloc[-1])
                bias = float(df['BIAS'].iloc[-1])
                vol = int(df['Volume'].iloc[-1])
                avg_vol = int(df['Volume'].tail(5).mean())
                stock_name = get_real_chinese_name(final_id)

                # --- 畫面呈現 ---
                st.title(f"🏢 {stock_name} ({sid}) 專業診斷報告")
                st.divider()
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("目前價格", f"{lp:.2f}", f"{lp - df['Close'].iloc[-2]:.2f}")
                m2.metric("KD 熱度", f"{k_val:.1f}")
                m3.metric("MACD 動能", f"{macd_h:.2f}")
                m4.metric("乖離率 BIAS", f"{bias:.1f}%")

                st.write("### 📝 四大指標綜合判斷")
                c1, c2 = st.columns(2)
                with c1:
                    st.info("**📈 技術趨勢分析**")
                    st.write(f"● **KD 熱度**：{'🔥 過熱' if k_val > 80 else '❄️ 冷清' if k_val < 20 else '✅ 正常'}")
                    st.write(f"● **MACD 動能**：{'🚀 強勁' if macd_h > 0 else '☁️ 轉弱'}")
                with c2:
                    st.info("**📊 量能與乖離分析**")
                    st.write(f"● **成交量 (VOL)**：{'💥 爆量' if vol > avg_vol * 1.5 else '☕ 平穩'}")
                    st.write(f"● **乖離率 (BIAS)**：{'📏 過大' if abs(bias) > 5 else '穩定'}")

                st.divider()
                score = (1 if k_val < 30 else 0) + (1 if macd_h > 0 else 0) + (1 if lp > df['MA20'].iloc[-1] else 0)
                
                st.subheader("💡 系統最終建議")
                if score >= 2: st.success("**【 綜合評等：強勢看多 】** 適合偏多思考。")
                elif score <= 0: st.error("**【 綜合評等：偏空觀望 】** 不宜逆勢摸底。")
                else: st.warning("**【 綜合評等：區間盤整 】** 建議低買高賣。")

                st.write("### 📈 股價走勢圖")
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線')])
                fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='月線'))
                fig.update_layout(height=500, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"分析異常：請確認股號。若為債券ETF請輸入如 00679B")

st.sidebar.markdown("---")
st.sidebar.caption("小白股票診療室 v3.3 | 債券ETF修復版")
