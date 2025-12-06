import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import altair as alt 

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
# 재무 데이터는 자주 변하지 않으므로 캐시 시간을 길게 설정합니다.
@st.cache_data(ttl=60*60*24) 
def load_data(ticker_list):
    """지정된 티커 목록의 연간 총매출 데이터를 로드합니다."""
    data = {}
    
    for name, ticker in ticker_list.items():
        try:
            ticker_obj = yf.Ticker(ticker)
            # yfinance에서 연간 재무제표를 가져옵니다.
            financials_df = ticker_obj.financials
            
            # 'Total Revenue' (총매출) 항목이 재무제표에 있는지 확인
            if 'Total Revenue' in financials_df.index:
                # 총매출 Series를 추출하고, Series의 이름(컬럼명)을 종목 이름으로 설정
                revenue_series = financials_df.loc['Total Revenue'].T
                revenue_series.name = name
                
                # Series가 정상적인 형태인지 확인
                if isinstance(revenue_series, pd.Series) and not revenue_series.empty:
                    data[name] = revenue_series
                else:
                    st.warning(f"🚨 {name} ({ticker}): 'Total Revenue' 데이터가 비어있거나 시계열 형태가 아닙니다. 로드 실패.")
            else:
                st.warning(f"🚨 {name} ({ticker}): 연간 재무제표에서 'Total Revenue'를 찾을 수 없습니다.")

        except Exception as e:
            st.error(f"❌ 데이터 로드 중 오류 발생: {name} - {e}")

    # 모든 총매출 데이터를 하나의 DataFrame으로 합치기
    if data:
        try:
            df_revenue = pd.DataFrame(data)
            
            # 인덱스(날짜)를 연도로 변환하고, 최근 10개 연도만 추출하여 '10년 기준' 요구 충족
            df_revenue.index = df_revenue.index.year 
            df_revenue = df_revenue.tail(10) 
            
            return df_revenue.sort_index()
        except ValueError as e:
            st.error(f"❌ 최종 데이터프레임 구조 오류: {e}")
            return pd.DataFrame()
            
    return pd.DataFrame()

# --- 4. 사이드바 입력 위젯 ---

# 총매출은 연간 데이터이므로 날짜 선택 위젯을 '연도' 선택에 가깝게 조정
current_year = datetime.now().year
default_start_year = current_year - 10 # 기본 10년 전
min_year = current_year - 30 # 최대 30년 전부터 선택 가능

st.sidebar.markdown("**데이터 조회 기간 (연간 보고서 기준)**")
start_year = st.sidebar.slider(
    "📅 시작 연도 선택",
    min_value=min_year,
    max_value=current_year - 2, # 가장 최근 연도는 아직 보고서가 나오지 않았을 수 있으므로 제한
    value=default_start_year,
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
    list(TICKERS.keys()),
    default=default_selected_stocks
)

st.sidebar.markdown("---")
st.sidebar.caption("본 앱은 연간 총매출 데이터를 사용하며, 데이터 소스에 따라 10년치 데이터가 부족할 수 있습니다.")


# --- 5. 데이터 로드 및 처리 ---

if not selected_stocks:
    st.warning("☝️ 먼저 왼쪽 사이드바에서 조회할 종목을 하나 이상 선택해 주세요.")
else:
    selected_tickers = {name: TICKERS[name] for name in selected_stocks}
    
    with st.spinner('연간 총매출 데이터를 불러오는 중입니다...'):
        df_revenue = load_data(selected_tickers)
        
    # 날짜 필터링 (데이터 로드 후 수행)
    df_filtered = df_revenue[df_revenue.index >= start_year]
    
    
    # --- 6. 결과 표시 ---
    if not df_filtered.empty:
        
        st.header(f"💰 {df_filtered.index.min()}년 이후 총매출 변화 (단위: 억 원, 가중치 조정됨)")
        
        # 데이터의 규모를 조정 (억 원 단위로 보기 쉽게)
        df_display = df_filtered / 1_000_000_000 * 10 
        
        # 총매출 데이터를 기준 연도 대비 '성장률'로 변환
        first_values = df_display.iloc[0]
        normalized_df = (df_display / first_values.replace(0, 1)) * 100
        
        st.subheader("📊 총매출 변화율 (시작 연도 = 100 기준)")
        st.caption("여러 종목의 성장을 비교하기 위해, 조회 시작 연도의 총매출을 100으로 기준화했습니다.")
        
        # 데이터 시각화를 위해 long format으로 변환
        df_long = normalized_df.reset_index().melt(
            id_vars='index',
            var_name='Stock',
            value_name='Normalized_Revenue'
        )
        df_long.rename(columns={'index': 'Year'}, inplace=True)
        
        # 사용자가 선택한 그래프 종류에 따라 차트 표시
        if chart_type == '선 그래프 (Line Chart)':
            st.subheader("📉 종목별 총매출 성장률 선 그래프")
            
            # Altair를 사용한 선 그래프 
            chart = alt.Chart(df_long).mark_line().encode(
                x=alt.X('Year:O', title='연도'), # 연도를 순서형(Ordinal) 데이터
