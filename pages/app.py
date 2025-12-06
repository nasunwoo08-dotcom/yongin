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

# --- 3. 데이터 로딩 함수 (최종 수정 버전) ---
@st.cache_data(ttl=60*60*4) # 4시간 캐시 설정
def load_data(ticker_list, start_date, end_date):
    """지정된 티커 목록의 주식 종가 데이터를 로드합니다."""
    data = {}
    
    for name, ticker in ticker_list.items():
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            # 데이터 검증: 비어있지 않고 'Close' 컬럼이 있는지 확인
            if not df.empty and 'Close' in df.columns:
                
                close_series = df['Close']
                
                # 데이터가 Series 형태인지 명시적으로 확인하여 구조 오류 방지
                if isinstance(close_series, pd.Series):
                    data[name] = close_series
                else:
                    st.warning(f"🚨 {name} ({ticker}): 'Close' 데이터가 시계열(Series) 형태가 아닙니다. 로드 실패.")
                
            else:
                st.warning(f"🚨 {name} ({ticker}): 해당 기간의 데이터를 불러오지 못했습니다. df.empty={df.empty}")
                
        except Exception as e:
            st.error(f"❌ 데이터 로드 중 오류 발생: {name} - {e}")

    # 모든 종가 데이터를 하나의 DataFrame으로 합치기
    if data:
        try:
            df_stocks = pd.DataFrame(data)
            return df_stocks.sort_index()
        except ValueError as e:
            st.error(f"❌ 최종 데이터프레임 구조 오류: {e}")
            st.warning("데이터 구조 문제: 딕셔너리에 Series가 아닌 다른 값이 포함되었습니다.")
            
            # 문제의 원인 파악을 위한 디버깅 정보 출력
            for name, value in data.items():
                if not isinstance(value, pd.Series):
                    st.code(f"❗문제 종목: {name}, 값 유형: {type(value)}, 값: {value}")
            
            return pd.DataFrame()
            
    return pd.DataFrame()

# --- 4. 사이드바 입력 위젯 ---

# 마감 날짜를 1년 전으로 고정하여 안정성 확보
end_date_limit = datetime.now() - timedelta(days=365) 

# 기본 시작 날짜를 10년 전으로 설정
default_start_date = end_date_limit - timedelta(days=10 * 365) 

# 🚨 핵심 수정: 최소 조회 기간을 10년 전으로 고정 (최대 10년치만 조회 가능)
min_date_limit = end_date_limit - timedelta(days=10 * 365) 

start_date = st.sidebar.date_input(
    "📅 데이터 조회 시작 날짜",
    value=default_start_date,
    min_value=min_date_limit, # 👈 10년 전 날짜보다 더 과거는 선택 불가능
    max_value=end_date_limit # 최대 날짜를 1년 전으로 제한
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
st.sidebar.caption("본 웹페이지의 데이터는 주가(종가) 추이를 기반으로 하며, 투자의 책임은 사용자에게 있습니다.")


# --- 5. 데이터 로드 및 처리 ---

if not selected_stocks:
    st.warning("☝️ 먼저 왼쪽 사이드바에서 조회할 종목을 하나 이상 선택해 주세요.")
else:
    # 선택된 종목만 필터링하여 데이터 로드
    selected_tickers = {name: TICKERS[name] for name in selected_stocks}
    
    # 데이터 로드 실행
    with st.spinner('데이터를 불러오는 중입니다... 잠시만 기다려 주세요.'):
        df_stocks = load_data(
            selected_tickers, 
            start_date.strftime('%Y-%m-%d'),
            end_date_limit.strftime('%Y-%m-%d') # 마감 날짜를 1년 전으로 고정
        )
    
    # --- 6. 결과 표시 ---
    if not df_stocks.empty:
        
        # 그래프 제목
        st.header(f"💰 {start_date.strftime('%Y-%m-%d')} ~ {end_date_limit.strftime('%Y-%m-%d')} 주가(종가) 추이")
        
        # 주가 데이터를 기준일 대비 '성장률'로 변환
        first_values = df_stocks.iloc[0]
        normalized_df = (df_stocks / first_values.replace(0, 1)) * 100
        
        st.subheader("📊 주가 변화율 (시작일 = 100 기준)")
        st.caption("여러 종목의 장기간 성장을 비교하기 위해, 조회 시작 날짜의 주가를 100으로 기준화했습니다.")
        
        # 데이터 시각화를 위해 long format으로 변환
        df_long = normalized_df.reset_index().melt(
            id_vars='Date',
            var_name='Stock',
            value_name='Normalized_Price'
        )
        
        # 사용자가 선택한 그래프 종류에 따라 차트 표시
        if chart_type == '선 그래프 (Line Chart)':
            st.subheader("📉 종목별 성장률 선 그래프")
            
            # Altair를 사용한 선 그래프 (Tooltip, Interactive 기능 포함)
            chart = alt.Chart(df_long).mark_line().encode(
                x=alt.X('Date:T', title='날짜'),
                y=alt.Y('Normalized_Price:Q', title='주가 변화율 (시작일=100)'),
                color='Stock:N',
                tooltip=['Date:T', 'Stock:N', alt.Tooltip('Normalized_Price:Q', format=',.2f')]
            ).interactive() 
            
            st.altair_chart(chart, use_container_width=True)
            
        elif chart_type == '막대 그래프 (Bar Chart)':
            st.subheader("📊 일자별 종가 막대 그래프")
            st.bar_chart(normalized_df, use_container_width=True)
            
        st.markdown("---")

        # --- 7. 데이터 테이블 표시 ---
        st.subheader("📚 전체 기간 주가 데이터 (변화율 기준)")
        st.dataframe(normalized_df.style.format("{:,.2f}"), use_container_width=True)

    else:
        st.error("⚠️ 데이터를 불러오지 못했습니다. 종목 코드나 날짜 설정을 확인해 주세요.")
