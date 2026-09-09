import datetime
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="일별 박스오피스", page_icon="🎬", layout="wide")

# 인증키는 비밀 금고(secrets)에서 불러온다
API_KEY = st.secrets["KOBIS_KEY"]
URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"

# '어제'를 한국 시간 기준으로 기본값 설정
KST = datetime.timezone(datetime.timedelta(hours=9))
today_kst = datetime.datetime.now(KST).date()
default_date = today_kst - datetime.timedelta(days=1)

st.title("🎬 일별 박스오피스 조회")

# ==========================================
# 📅 [신규 추가] 달력 날짜 선택 기능
# ==========================================
selected_date = st.date_input(
    "조회할 날짜를 선택하세요",
    value=default_date,
    max_value=default_date,  # 오늘 이후 날짜는 선택 불가
    min_value=datetime.date(2004, 1, 1),
    help="KOBIS 박스오피스는 어제 날짜 데이터까지 조회할 수 있습니다."
)

target_dt = selected_date.strftime("%Y%m%d")
st.caption(f"선택한 날짜: {selected_date}")


@st.cache_data(ttl=3600)
def fetch_boxoffice(date_str):
    """KOBIS API에서 선택한 날짜의 일별 박스오피스를 받아 온다."""
    params = {
        "key": API_KEY,
        "targetDt": date_str,
        "itemPerPage": "100"  # 전체 데이터를 불러옴
    }
    res = requests.get(URL, params=params, timeout=10)
    res.raise_for_status()
    return res.json()


try:
    data = fetch_boxoffice(target_dt)
except requests.RequestException:
    st.error("서버에 연결하지 못했습니다. 인터넷 연결을 확인하고 잠시 뒤 새로고침해 주세요.")
    st.stop()

if "faultInfo" in data:
    st.error(f"API가 오류를 돌려주었습니다: {data['faultInfo'].get('message', '')}")
    st.info("비밀 금고(secrets)의 KOBIS_KEY 값이 올바른지 확인해 주세요.")
    st.stop()

movies = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])

if not movies:
    st.warning("해당 날짜의 영화 목록이 비어 있습니다. 아직 집계 전인 날짜이거나 데이터가 없는 날짜입니다.")
    st.stop()

df = pd.DataFrame(movies)

# 숫자로 변환
for col in ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]:
    df[col] = pd.to_numeric(df[col])

# 순위 변동 / 신규 진입 표시 처리
def format_rank_change(row):
    if row["rankOldAndNew"] == "NEW":
        return "🆕 NEW"
    inten = row["rankInten"]
    if inten > 0:
        return f"🔺 {inten}"
    elif inten < 0:
        return f"🔻 {abs(inten)}"
    else:
        return "-"

df["순위변동"] = df.apply(format_rank_change, axis=1)

# 1위 영화 지표 카드
top = df.sort_values("rank").iloc[0]
st.subheader(f"🥇 1위 — {top['movieNm']}")
c1, c2, c3 = st.columns(3)
c1.metric("해당 날짜 관객수", f"{top['audiCnt']:,}명")
c2.metric("누적 관객수", f"{top['audiAcc']:,}명")
c3.metric("스크린수", f"{top['scrnCnt']:,}개")

st.divider()

# ==========================================
# 🏆 1위부터 10위까지 순위표
# ==========================================
st.subheader(f"🏆 {selected_date} 박스오피스 Top 10 (1위 ~ 10위)")
df_top10 = df.sort_values("rank").head(10)[["rank", "순위변동", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]]
df_top10.columns = ["순위", "변동", "영화명", "개봉일", "당일 관객수", "누적 관객수", "스크린수"]

st.dataframe(
    df_top10,
    hide_index=True,
    use_container_width=True,
    column_config={
        "당일 관객수": st.column_config.NumberColumn(format="%d명"),
        "누적 관객수": st.column_config.NumberColumn(format="%d명"),
        "스크린수": st.column_config.NumberColumn(format="%d개"),
    }
)

st.divider()

# 📊 관객수 상위 5편 막대그래프
st.subheader("📊 관객수 상위 5편")
top5 = df.sort_values("audiCnt", ascending=False).head(5)
fig = px.bar(top5, x="movieNm", y="audiCnt", labels={"movieNm": "영화명", "audiCnt": "당일 관객수"})
st.plotly_chart(fig, use_container_width=True)

st.divider()

# 📋 전체 박스오피스 순위표
st.subheader(f"📋 전체 순위표 (총 {len(df)}편)")
table_all = df.sort_values("rank")[["rank", "순위변동", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]]
table_all.columns = ["순위", "변동", "영화명", "개봉일", "당일 관객수", "누적 관객수", "스크린수"]

st.dataframe(
    table_all,
    hide_index=True,
    use_container_width=True,
    column_config={
        "당일 관객수": st.column_config.NumberColumn(format="%d명"),
        "누적 관객수": st.column_config.NumberColumn(format="%d명"),
        "스크린수": st.column_config.NumberColumn(format="%d개"),
    }
)
