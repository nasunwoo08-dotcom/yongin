import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import altair as alt 
import numpy as np 

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
    "리노공업 (Leeno)": "042700.KQ",
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
default_end_year = current_year - 2 # 👈 2025년(미래) 제외. 2023년 데이터가 보통 최신입니다.
default_start_year = 2021 # 👈 기본 시작 연도를 2021년으로 설정
min_year_limit = 2000 

st.sidebar.markdown("### 📅 데이터 조회 기간")
# 최대 10년 기준을 만족시키기 위해 끝 연도와 시작 연도를 함께 제한
start_year = st.sidebar.slider(
    "시작 연도 선택 (기본 2021년)",
    min_value=min_year_limit, 
    max_value=default_end_year, # 👈 최대 선택 가능 연도는 2023년입니다.
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
st.sidebar.caption("본 앱은 연간 총매출 데이터를 사용합니다. 데이터 소스(yfinance)의 한계로 인해 모든 연도 데이터가 채워지지 않을 수 있습니다.")


# --- 5. 데이터 로드 및 처리 ---

if not selected_stocks:
    st.warning("☝️ 먼저 왼쪽 사이드바에서 조회할 종목을 하나 이상 선택해 주세요.")
else:
    selected_tickers = {name: TICKERS[name] for name in selected_stocks}
    
    with st.spinner('연간 총매출 데이터를 불러오는 중입니다...'):
        df_revenue_full = load_revenue_data(selected_tickers)
        
    # 날짜 필터링 (사용자 선택 연도 반영)
    if not df_revenue_full.empty:
        df_filtered = df_revenue_full[df_revenue_full.index >= start_year]
    else:
        df_filtered = pd.DataFrame()
    
    
    # --- 6. 결과 표시 ---
    if not df_filtered.empty:
        
        st.header(f"💰 {df_filtered.index.min()}년 ~ {df_filtered.index.max()}년 총매출 변화")
        
        # 데이터의 규모를 조정 (보기 쉽게 억 원 단위로 변환)
        # 1,000,000,000으로 나눈 값은 약 10억 원 단위입니다.
        df_display = df_filtered / 1_000_000_000 
        
        # 총매출 데이터를 기준 연도 대비 '성장률'로 변환
        
        # Nan이 아닌 첫 번째 유효한 값으로 기준 설정 (결측치 문제 방지)
        valid_start_values = df_display.apply(lambda x: x.dropna().iloc[0] if not x.dropna().empty else np.nan)
        normalized_df = (df_display / valid_start_values.replace(0, 1)) * 100
        
        st.subheader("📊 총매출 변화율 (시작 연도 = 100 기준)")
        st.caption("여러 종목의 성장을 비교하기 위해, 유효한 데이터가 있는 첫 연도의 총매출을 100으로 기준화했습니다.")
        
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
            chart = alt.Chart(df_long).mark_line(point=True).encode( 
                x=alt.X('Year:O', title='연도'), 
                y=alt.Y('Normalized_Revenue:Q', title='총매출 변화율 (시작 연도=100)'),
                color='Stock:N',
                tooltip=['Year:O', 'Stock:N', alt.Tooltip('Normalized_Revenue:Q', format=',.2f')]
            ).interactive() 
            
            st.altair_chart(chart, use_container_width=True)
            
        elif chart_type == '막대 그래프 (Bar Chart)':
            st.subheader("📊 연도별 총매출 막대 그래프")
            st.bar_chart(normalized_df, use_container_width=True)
            
        st.markdown("---")

        # --- 7. 데이터 테이블 표시 ---
        st.subheader(f"📚 {df_filtered.index.min()}년 이후 총매출 데이터 (단위: 억 원)")
        st.dataframe(df_display.style.format("{:,.0f} 억 원"), use_container_width=True)

    else:
        st.error(f"⚠️ 선택하신 연도({start_year}년 이후)에 해당하는 연간 총매출 데이터를 찾지 못했습니다. 시작 연도를 조정하거나 종목 선택을 확인해 주세요.")
