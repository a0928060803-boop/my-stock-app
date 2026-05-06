import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# --- 1. 網頁配置 ---
st.set_page_config(page_title="小白股票診療室 Pro", layout="centered")

# --- 2. 常用資料庫 (維持穩定性) ---
STOCK_DB = {"2330": "台積電", "2317": "鴻海", "2454": "聯發科", "0050": "元大台灣50", "00878": "國泰高股息", "2314": "台揚", "2634": "漢翔"}

def get_real_chinese_name(symbol):
    try:
        clean_sid = symbol.split('.').upper()
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
quick_select = st.selectbox("🔥 熱門標的快速選單", ["手動輸入代號", "2330 台積電", "2317 鴻海", "2634 漢翔", "2314 台揚"])
default_id = quick_select.split(' ') if quick_select != "手動輸入代號" else "2330"

col_input, col_btn = st.columns()
with col_input:
    stock_id = st.text_input("輸入代號：", default_id, label_visibility="collapsed")
with col_btn:
    analyze_btn = st.button("開始診斷", type="primary", use_container_width=True)

st.divider()

if analyze_btn or stock_id:
    sid = stock_id.upper().strip()
    with st.spinner(f'專業分析中...'):
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
                low_9, high_9 = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
                df['K'] = ((df['Close'] - low_9) / (high_9 - low_9) * 100).ewm(com=2).mean()
                ema12, ema26 = df['Close'].ewm(span=12).mean(), df['Close'].ewm(span=26).mean()
                df['MACD_HIST'] = (ema12 - ema26) - (ema12 - ema26).ewm(span=9).mean()

                # 最新數據
                lp = float(df['Close'].iloc[-1])
                k_val = float(df['K'].iloc[-1])
                macd_h = float(df['MACD_HIST'].iloc[-1])
                bias = float(df['BIAS'].iloc[-1])
                vol = int(df['Volume'].iloc[-1])
                avg_vol = int(df['Volume'].tail(5).mean())
                supp = float(df['Low'].tail(20).min()) # 支撐(地板)
                resi = float(df['High'].tail(20).max()) # 壓力(天花板)
                ma20_val = float(df['MA20'].iloc[-1])

                st.subheader(f"🏢 {get_real_chinese_name(sid)} ({sid}) 診斷報告")
                
                # 圖表分頁 (保持前版穩定繪圖)
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["K線", "量能", "KD", "MACD", "乖離"])
                # ... (圖表繪製代碼同 v5.2，此處為求回覆簡潔省略，請維持原狀) ...

                # --- 核心更新：超白話分析報告 ---
                st.divider()
                st.write("### 📝 聽得懂的行情分析")
                c1, c2 = st.columns(2)
                with c1:
                    st.info("**📈 錢往哪裡跑？ (KD/MACD)**")
                    st.write(f"● **市場熱度**：{'大家瘋了！現在進場容易套在山頂' if k_val > 80 else '冷冷清清，反而可以趁現在偷偷撿便宜' if k_val < 20 else '氣氛很穩，大家都在觀望，適合分批買'}")
                    st.write(f"● **衝勁動能**：{'油門踩到底！股價正在往上衝，氣勢很強' if macd_h > 0 else '車速慢下來了，小心股價隨時會倒車'}")
                with c2:
                    st.info("**📊 籌碼與距離 (VOL/BIAS)**")
                    st.write(f"● **成交量**：{'今天有大戶進場！量多到嚇人，要變盤了' if vol > avg_vol * 1.5 else '今天都是小散戶在玩，沒什麼大動作'}")
                    st.write(f"● **月線距離**：{'跑太遠了！離月線太遠，隨時會被吸回來' if abs(bias) > 5 else '跟月線保持安全距離，走得很健康'}")

                # --- 核心更新：明確買賣點與對策 ---
                st.subheader("💡 最終投資對策與建議價格")
                score = (1 if k_val < 40 else 0) + (1 if macd_h > 0 else 0) + (1 if lp > ma20_val else 0)

                # 買賣建議邏輯
                if score >= 2:
                    st.success(f"**【 目前診斷：趨勢強勁，推薦買入/續抱 】**")
                    st.write(f"👉 **怎麼做？**：目前是送分題，氣氛很好。如果還沒買，可以等回測到 **{ma20_val:.2f}** 元附近分批進場。")
                    st.write(f"👉 **看哪裡？**：停利看壓力位 **{resi:.2f}**，如果跌破地板 **{supp:.2f}** 就停損逃命。")
                elif score <= 0:
                    st.error(f"**【 目前診斷：氣氛不對，建議賣出/觀望 】**")
                    st.write(f"👉 **怎麼做？**：現在買的人都在賠錢，別當接盤俠！建議空手等待。若有持股，建議在 **{lp:.2f}** 附近減碼。")
                    st.write(f"👉 **看哪裡？**：等股價跌到支撐 **{supp:.2f}** 有撐住再來考慮。")
                else:
                    st.warning(f"**【 目前診斷：盤整走勢，建議低買高賣 】**")
                    st.write(f"👉 **怎麼做？**：現在沒有大方向，別追高。適合在 **{supp:.2f}** 附近買，**{resi:.2f}** 附近賣。")
                    st.write(f"👉 **看哪裡？**：密切關注股價是否能站穩月線 **{ma20_val:.2f}**。")

        except Exception as e:
            st.error(f"分析異常。")

st.caption("v5.3 | 終極導師版")
