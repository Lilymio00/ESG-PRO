import io

import pandas as pd
import requests
import streamlit as st
import urllib3

# ------------------------------------------------------------------
# 頁面設定
# ------------------------------------------------------------------
st.set_page_config(page_title="公開資訊資料檢視器", page_icon="📊", layout="wide")
st.title("📊 公開資訊資料檢視器")

DEFAULT_URL = "https://mopsfin.twse.com.tw/opendata/t187ap46_O_1.csv"  # 換連結

# ------------------------------------------------------------------
# 側邊欄
# ------------------------------------------------------------------
with st.sidebar:
    st.header("設定")
    url = st.text_input("CSV 連結", value=DEFAULT_URL)
    verify_ssl = st.checkbox(
        "驗證 SSL 憑證",
        value=False,
        help="原程式使用 verify=False。若來源網站憑證正常，建議勾選。",
    )
    drop_na = st.checkbox("移除含空值的列 (dropna)", value=True)
    if st.button("🔄 重新抓取資料"):
        st.cache_data.clear()
        st.rerun()

if not verify_ssl:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ------------------------------------------------------------------
# 抓取資料（快取 1 小時，避免每次互動都重新下載）
# ------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner="資料下載中...")
def load_data(url: str, verify: bool) -> pd.DataFrame:
    response = requests.get(url, verify=verify, timeout=30)
    response.raise_for_status()
    # 直接從記憶體讀取，不需寫入檔案（Streamlit Cloud 的檔案系統是暫時性的）
    return pd.read_csv(io.BytesIO(response.content), encoding="utf-8-sig")  # 繁體中文


try:
    df = load_data(url, verify_ssl)
except requests.exceptions.SSLError:
    st.error("SSL 憑證驗證失敗，請取消勾選側邊欄的「驗證 SSL 憑證」後再試。")
    st.stop()
except requests.exceptions.RequestException as e:
    st.error(f"下載失敗：{e}")
    st.stop()
except Exception as e:
    st.error(f"資料解析失敗：{e}")
    st.stop()

if drop_na:
    df = df.dropna()

# ------------------------------------------------------------------
# 顯示資料
# ------------------------------------------------------------------
col1, col2 = st.columns(2)
col1.metric("資料筆數", f"{len(df):,}")
col2.metric("欄位數", f"{df.shape[1]:,}")

keyword = st.text_input("🔍 關鍵字搜尋（搜尋所有欄位）")
if keyword:
    mask = df.astype(str).apply(
        lambda col: col.str.contains(keyword, case=False, na=False)
    ).any(axis=1)
    df_show = df[mask]
    st.caption(f"符合 {len(df_show):,} 筆")
else:
    df_show = df

st.dataframe(df_show, use_container_width=True, height=500)

st.download_button(
    label="⬇️ 下載 CSV",
    data=df_show.to_csv(index=False).encode("utf-8-sig"),  # utf-8-sig 讓 Excel 開啟不亂碼
    file_name="data01.csv",
    mime="text/csv",
)
