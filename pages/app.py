import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import altair as alt 
import numpy as np # np 추가됨

# --- 1. 웹페이지 설정 및 제목 ---
st.set_page_config(layout="wide")
st.title("📈 대한민국 주요 반도체 기업 총매출 성장 분석 (연간)")
st.markdown("---")
st.sidebar.header("설정 옵션")

# --- 2. 분석 대상 종목 코드 정의 ---
TICKERS = {
    "삼성전자 (Samsung Elec)": "005930.KS",
    "SK하이닉스 (SK Hynix)": "000660.KS",
    "DB하이텍 (DB Hitek)": "000990.KS",
    "리노공업 (Leeno)": "058470.KQ",
    "하나마이크론 (Hana Micron)": "067310.KQ",
}

# --- 3. 데이터 로딩 함수 (총매출 데이터 로드) ---
@st.cache_data(ttl=60*60*24) # 재무 데이터는 24시간 캐시 설정
def load_revenue_data(ticker_list):
    """지정된 티커 목록의 연간 총매출 데이터를 로드합니다."""
    data = {}
    
    for name, ticker in ticker_list.items():
        try:
            ticker_obj = yf.Ticker(ticker)
            # 연간 재무제표를 가져옵니다.
            financials_df = ticker_obj.financials
            
            # 'Total Revenue' (총매출) 항목이 있는지 확인합니다.
            if 'Total Revenue' in financials_df.index:
                # 총매출 Series를 추출합니다.
                revenue_series = financials_df.loc['Total Revenue'].T
                revenue_series.name = name
                
                # 데이터가 비어있지 않은 Series 형태인지 확인합니다.
                if isinstance(revenue_series, pd.Series) and not revenue_series.empty:
                    data[name] = revenue_series
                else:
                    st.warning(f"🚨 {name} ({ticker}): 총매출 데이터가 비어있거나 시계열 형태가 아닙니다. 로드 실패.")
            else:
                st.warning(f"🚨 {name} ({ticker}): 연간 재무제표에서 'Total Revenue'를 찾을 수 없습니다. (데이터 부족)")

        except Exception as e:
            st.error(f"❌ 데이터 로드 중 오류 발생: {name} - {e}")

    # 모든 총매출 데이터를 하나의 DataFrame으로 합치기
    if data:
        try:
            df_revenue = pd.DataFrame(data)
            
            # 인덱스(날짜)를 연도로 변환합니다.
            df_revenue.index = df_revenue.index.year 
            
            # 데이터 정렬 및 반환
            return df_revenue.sort_index()
        except ValueError as e:
            st.error(f"❌ 최종 데이터프레임 구조 오류 발생: {e}")
            st.warning("데이터 구조 문제: 딕셔너리에 Series가 아닌 다른 값이 포함되었을 수 있습니다.")
            return pd.DataFrame()
            
    return pd.DataFrame()

# --- 4. 사이드바 입력 위젯 ---

# 연도 기반 데이터이므로 슬라이더 사용
current_year = datetime.now().year
default_end_year = current_year # 현재 연도 (2025년)
default_start_year = 2021 # 👈 시작 연도를 2021년으로 명시적 설정
min_year_limit = 2000 # 👈 최소 선택 가능 연도 제한

st.sidebar.markdown("### 📅 데이터 조회 기간")
# 최대 10년 기준을 만족시키기 위해 끝 연도와 시작 연도를 함께 제한
start_year = st.sidebar.slider(
    "시작 연도 선택 (2021년 이후 권장)",
    min_value=min_year_limit, 
    max_value=default_end_year,
    value=default_start_year, # 👈 기본값을 2021년으로 설정
    step=1
)

# 4-2. 그래프 종류 선택
chart_type = st.sidebar.radio(
    "📈 그래프 종류 선택",
    ('선 그래프 (Line Chart)', '막대 그래프 (Bar Chart)'),
    index=0
)

# 4-3. 종목 필터링 (다중 선택)
default_selected_stocks = list(TICKERS.keys())
selected_stocks = st.sidebar.multiselect(
    "🔍 조회할 종목 선택 (필수)",
