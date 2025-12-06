import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import altair as alt # Altair를 사용하여 시각화 옵션을 확장

# --- 1. 웹페이지 설정 및 제목 ---
st.set_page_config(layout="wide")
st.title("📈 대한민국 주요 반도체 기업 성장 추이 분석")
st.markdown("---")
st.sidebar.header("설정 옵션")

# --- 2. 분석 대상 종목 코드 정의 ---
# 종목 코드는 '티커.KS' (코스피) 또는 '티커.KQ' (코스닥) 형태입니다.
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
def load_data(ticker_list, start_date):
    """지정된 티커 목록의 주식 종가 데이터를 로드합니다."""
    data = {}
    
    for name, ticker in ticker_list.items():
        try:
            # yfinance를 사용하여 데이터 다운로드
            # 최대 30년 분석을 위해, yfinance가 제공 가능한 가장 오래된 데이터를 요청합니다.
            df = yf.download(ticker, start=start_date, progress=False)
            
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
            # 날짜를 기준으로 정렬하고, 결측치(NaN)는 제거하지 않고 그대로 둡니다 (그래프가 자동으로 처리).
            return df_stocks.sort_index()
        except ValueError as e:
            st.error(f"❌ 데이터프레임 생성 중 구조 오류 발생: {e}")
            st.warning("데이터 구조를 확인해 주세요. yfinance가 비정상적인 데이터를 반환했을 수 있습니다.")
            return pd.DataFrame()
            
    # data가 비어있다면, 빈 DataFrame 반환
    return pd.DataFrame()

# --- 4. 사이드바 입력 위젯 ---

# 4-1. 날짜 범위 설정 (최대 30년 분석을 위한 설정)
end_date = datetime.now()
# 기본 시작 날짜를 30년 전으로 설정 (yf.download가 제공하는 최대 기간에 맞춰짐)
default_start_date = end_date - timedelta(days=30 * 365) 

start_date = st.sidebar.date_input(
    "📅 데이터 조회 시작 날짜",
    value=default_start_date,
    min_value=datetime(1990, 1, 1), # 30년 이상의 분석을 위해 최소 날짜 설정
    max_value=end_date
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
    
    # 데이터 로드 실행
    with st.spinner('데이터를 불러오는 중입니다... 잠시만 기다려 주세요.'):
        # start_date를 문자열로 변환하여 load_data에 전달 (yfinance 형식)
        df_stocks = load_data(selected_tickers, start_date.strftime('%Y-%m-%d'))
    
    if not df_stocks.empty:
        
        # --- 6. 그래프 표시 (메인 화면) ---
        
        st.header(f"💰 {start_date.strftime('%Y-%m-%d')} 이후 주요 반도체 기업의 주가(종가) 추이")
        
        # 주가 데이터를 기준일 대비 '성장률'로 변환하여 비교 용이하게 만듭니다.
        # 시작 날짜의 종가를 100으로 기준화 (Normalization)
        first_values = df_stocks.iloc[0]
        # 첫 날 값이 0인 경우를 대비하여 1로 대체하여 나눗셈 에러 방지
        normalized_df = (df_stocks / first_values.replace(0, 1)) * 100
        
        st.subheader("📊 주가 변화율 (시작일 = 100 기준)")
        st.caption("여러 종목의 장기간 성장을 비교하기 위해, 조회 시작 날짜의 주가를 100으로 기준화했습니다.")
        
        # 데이터 시각화를 위해 wide format을 long format으로 변환 (Altair/Streamlit 차트 요구사항)
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
            ).interactive() # 줌/패닝 가능
            
            st.altair_chart(chart, use_container_width=True)
            
        elif chart_type == '막대 그래프 (Bar Chart)':
            st.subheader("📊 일자별 종가 막대 그래프")
            
            # 막대 그래프는 시간의 흐름을 보기 어렵기 때문에, Streamlit의 기본 Bar Chart를 사용합니다.
            st.bar_chart(normalized_df, use_container_width=True)
            
        st.markdown("---")

        # --- 7. 데이터 테이블 표시 ---
        st.subheader("📚 전체 기간 주가 데이터 (변화율 기준)")
        st.dataframe(normalized_df.style.format("{:,.2f}"), use_container_width=True)

    else:
        st.error("⚠️ 데이터를 불러오지 못했습니다. 종목 코드, 날짜 설정, 또는 yfinance 서버 상태를 확인해 주세요.")
