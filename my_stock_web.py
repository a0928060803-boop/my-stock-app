import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 建立連線
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🚀 AI 雲端寫入測試")

# 按下按鈕後，會多一行紀錄到你的表格
if st.button("點我測試寫入表格"):
    try:
        # 1. 讀取現有資料
        df = conn.read(ttl=0) 
        
        # 2. 準備新資料
        new_data = pd.DataFrame([{
            "日期": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
            "股號": "TEST",
            "建議動作": "測試成功"
        }])
        
        # 3. 結合並上傳
        updated_df = pd.concat([df, new_data], ignore_index=True)
        conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=updated_df)
        
        st.success("✅ 太棒了！請去打開你的 Google 表格，看看是不是多了一行？")
    except Exception as e:
        st.error(f"❌ 寫入失敗，請檢查 Secrets 設定：{e}")
