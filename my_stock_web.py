import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- 網頁配置 (手機版自動適應) ---
st.set_page_config(page_title="小白股票診療室 Pro", layout="wide")

# --- 功能函數：更穩定的股名獲取 ---
def get_clean_name(ticker_obj, symbol):
    try:
        # yfinance 的 shortName 欄位通常存有台股中文名
        info = ticker_obj.info
        name = info.get('shortName') or info.get('longName') or symbol
        # 移除常見的英文商業後綴，讓中文更純粹
        for s in ["Semiconductor", "Manufacturing", "Industry", "Co.", "Ltd.", "Holdings", "Precision"]:
            name = name.replace(s, "").strip()
        return name
    except:
        return symbol

# --- 側邊欄：診斷輸入 ---
st.sidebar.header("🔍 診斷中心")
stock_id = st.sidebar.text_input("請輸入台股代號：", "2330")
analyze_btn = st.sidebar.button("開始看診", type="primary")

# --- 主畫面邏輯 ---
if analyze_btn or stock_id:
    # 台股代號處理
    formatted_id = f"{stock_id}.TW" if len(stock_id) <= 4 else stock_id
    
    with st.spinner(f'正在調閱 {stock_id} 雲端數據...'):
        try:
            # 1. 初始化 yfinance 並獲取名稱
            ticker = yf.Ticker(formatted_id)
            stock_name = get_clean_name(ticker, stock_id)
            
            # 2. 獲取股價數據
            df = ticker.history(period="1y")
            
            if df.empty:
                st.error("查無數據，請確認股號是否正確。")
            else:
                # 處理索引與欄位
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # 顯示顯眼的標題 (確保中文股名出現)
                st.title(f"🏢 {stock_name} ({stock_id}) 診斷報告")
                st.divider()

                # 3. [自力救濟] 指標計算 (不依賴 pandas-ta)
                # 計算 MA20 (月線)
                df['MA20'] = df['Close'].rolling(window=20).mean()
                # 計算 KD 指標 (9, 3, 3)
                low_9 = df['Low'].rolling(window=9).min()
                high_9 = df['High'].rolling(window=9).max()
                rsv = (df['Close'] - low_9) / (high_9 - low_9) * 100
                df['K'] = rsv.ewm(com=2, adjust=False).mean()
                
                # 取得最新數值
                lp = float(df['Close'].iloc[-1])
                k_val = float(df['K'].iloc[-1])
                m20 = float(df['MA20'].iloc[-1])
                supp = float(df['Low'].tail(20).min())
                resi = float(df['High'].tail(20).max())

                # 4. 數據儀表板
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("目前股價", f"{lp:.2f}", f"{lp - df['Close'].iloc[-2]:.2f}")
                col_b.metric("月均線 (20MA)", f"{m20:.2f}")
                col_c.metric("近期壓力位", f"{resi:.2f}")

                # 5. 精美 K 線圖表
                st.write("### 📈 近期股價走勢圖")
                fig = go.Figure(data=[go.Candlestick(
                    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'
                )])
                fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='月線'))
                fig.update_layout(height=450, margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

                # 6. 白話診斷建議
                st.write("### 📝 醫生診斷說明")
                c1, c2 = st.columns(2)
                with c1:
                    if lp > m20:
                        st.success(f"**趨勢：強勢格局**\n\n股價目前站穩在月線({m20:.1f})之上，代表近期市場氣氛很好，大家看好。")
                    else:
                        st.error(f"**趨勢：偏弱格局**\n\n股價掉到月線之下，代表最近買的人都在賠錢，請觀察地板價 {supp:.1f} 是否守住。")
                with c2:
                    if k_val > 80:
                        st.warning(f"**熱度：太燙了**\n\nKD值 {k_val:.1f}：現在大家都在搶，買進成本較高，小心追高。")
                    elif k_val < 20:
                        st.success(f"**熱度：冷冰冰**\n\nKD值 {k_val:.1f}：沒人要買，但通常是撿便宜的好時機。")
                    else:
                        st.write(f"**熱度：常態**\n\nKD值 {k_val:.1f}：目前市場情緒平穩，沒有過熱或過冷。")

        except Exception as e:
            st.error(f"診療過程發生錯誤：{e}")

# --- 頁尾 ---
st.sidebar.markdown("---")
st.sidebar.caption("小白股票診療室 v2.6 | 數據僅供參考")
