import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.title("🛠️ 連線連通性測試")

# 1. 建立引擎連線
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    st.success("✅ 成功建立 gsheets 連線引擎")
except Exception as e:
    st.error(f"❌ 引擎初始化失敗：{e}")

# 2. 測試按鈕
if st.button("點我測試寫入"):
    try:
        # 讀取現有內容 (測試讀取權限)
        df = conn.read(ttl=0)
        st.write("目前表內資料筆數:", len(df))
        
        # 準備一行新資料
        new_row = pd.DataFrame([{"日期": "2026-05-07", "股號": "TEST", "建議動作": "連線成功"}])
        
        # 結合並寫入 (測試寫入權限)
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=updated_df)
        
        st.balloons()
        st.success("🎉 寫入成功！請查看你的 Google 表格！")
    except Exception as e:
        st.error(f"❌ 執行過程出錯：{e}")
        st.info("如果看到 'KeyError: connections'，代表 Secrets 沒存好。")
