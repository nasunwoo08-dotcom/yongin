
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import altair as alt 

# --- 1. 웹페이지 설정 및 제목 ---
st.set_page_config(layout="wide")
st.title("📈 대한민국 주요 반도체 기업 성장 추이 분석")
st.markdown("---")
st.sidebar.header("설정 옵션")

# --- 2. 분석 대상 종목 코드 정의 ---
TICKERS = {
    "삼성전자 (Samsung Elec)": "005930.KS",
    "SK하이닉스 (SK Hynix)": "000660.KS",
    "한미반도체 (Hanmi Semi)": "042700.KQ",
    "DB하이텍 (DB Hitek)": "000990.KS",
    "리노공업 (Leeno)": "058470.KQ",
    "하나마이크론 (Hana Micron)": "067310.KQ",
}

# --- 3. 데이터 로딩 함수 (에러 방지 안전장치 포함) ---
@st.cache_data(ttl=60*60*4) # 4시간 캐시 설정
def load_data(ticker_list, start_date, end_date):
    """지정된 티커 목록의 주식 종가 데이터를 로드합니다."""
    data = {}
    
    for name, ticker in ticker_list.items():
        try:
            # yfinance를 사용하여 데이터 다운로드 (종료 날짜 추가)
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            # 데이터 검증: 비어있지 않고 'Close' 컬럼이 있는지 확인
            if not df.empty and 'Close' in df.columns:
                # 종가(Close) Series만 저장하고, 컬럼 이름을 종목 이름으로 변경
                data[name] = df['Close']
            else:
                st.warning(f"🚨 {name} ({ticker}): 해당 기간의 데이터를 불러오지 못했습니다.")
                
        except Exception as e:
            st.error(f"❌ 데이터 로드 중 오류 발생: {name} - {e}")

    # 모든 종가 데이터를 하나의 DataFrame으로 합치기
    if data:
        try:
            # Series 딕셔너리를 DataFrame으로 변환 시도
            df_stocks = pd.DataFrame(data)
            return df_stocks.sort_index()
        except ValueError as e:
            st.error(f"❌ 데이터프레임 생성 중 구조 오류 발생: {e}")
            st.warning("데이터 구조를 확인해 주세요. yfinance가 비정상적인 데이터를 반환했을 수 있습니다.")
            return pd.DataFrame()
            
    return pd.DataFrame()

# --- 4. 사이드바 입력 위젯 ---

# **수정 1: 조회 마감 날짜를 1년 전으로 고정**
end_date_limit = datetime.now() - timedelta(days=365) # 현재 날짜가 아닌 1년 전 날짜

# **수정 2: 기본 시작 날짜를 10년 전으로 설정**
default_start_date = end_date_limit - timedelta(days=10 * 365) 

start_date = st.sidebar.date_input(
    "📅 데이터 조회 시작 날짜",
    value=default_start_date,
    min_value=datetime(1990, 1, 1), 
    max_value=end_date_limit # 최대 날짜를 1년 전으로 제한
)

# 4-2. 그래프 종류 선택
chart_type = st.sidebar.radio(
    "📈 그래프 종류 선택",
    ('선 그래프 (Line Chart)', '막대 그래프 (Bar Chart)'),
    index=0
)

# 4-3. 종목 필터링 (다중 선택)
selected_stocks = st.sidebar.multiselect(
    "🔍 조회할 종목 선택 (필수)",
    list(TICKERS.keys()),
    default=list(TICKERS.keys())
)

st.sidebar.markdown("---")
st.sidebar.caption("본 웹페이지의 데이터는 주가(종가) 추이를 기반으로 하며, 투자 참고용입니다.")


# --- 5. 데이터 로드 및 처리 ---

if not selected_stocks:
    st.warning("☝️ 먼저 왼쪽 사이드바에서 조회할 종목을 하나 이상 선택해 주세요.")
else:
    # 선택된 종목만 필터링하여 데이터 로드
    selected_tickers = {name: TICKERS[name] for name in selected_stocks}
