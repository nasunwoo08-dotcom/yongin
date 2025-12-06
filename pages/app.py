import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 웹페이지 설정 및 제목 ---
st.set_page_config(layout="wide")
st.title("💡 한국 반도체 주식 동향 분석 웹페이지")
st.markdown("---")
st.sidebar.header("설정 옵션")

# --- 2. 반도체 종목 코드 정의 (예시) ---
# 실제 시장에서 '반도체'로 분류되는 종목 코드를 사용합니다.
# 종목 코드는 '티커.KS' (코스피) 또는 '티커.KQ' (코스닥) 형태입니다.
TICKERS = {
    "삼성전자 (Samsung Elec)": "005930.KS",
    "SK하이닉스 (SK Hynix)": "000660.KS",
    "한미반도체 (Hanmi Semi)": "042700.KQ",
    "DB하이텍 (DB Hitek)": "000990.KS",
    "리노공업 (Leeno)": "058470.KQ"
}

# --- 3. 데이터 로딩 함수 ---
@st.cache_data(ttl=60*60*4) # 4시간 캐시 설정 (데이터 빈번 호출 방지)
def load_data(ticker_list, start_date):
    """지정된 티커 목록의 주식 데이터를 로드합니다."""
    data = {}
    for name, ticker in ticker_list.items():
        try:
            # yfinance를 사용하여 데이터 다운로드
            df = yf.download(ticker, start=start_date, progress=False)
            if not df.empty:
                # 종가만 저장하고, 컬럼 이름을 종목 이름으로 변경
                data[name] = df['Close']
            else:
                st.warning(f"🚨 {name} ({ticker}): 데이터를 불러오지 못했습니다. 티커를 확인하세요.")
        except Exception as e:
            st.error(f"❌ 데이터 로드 중 오류 발생: {name} - {e}")

    # 모든 종가 데이터를 하나의 DataFrame으로 합치기
    if data:
        return pd.DataFrame(data)
    return pd.DataFrame()

# --- 4. 사이드바 입력 위젯 ---

# 4-1. 날짜 범위 설정
end_date = datetime.now()
# 기본 시작 날짜를 1년 전으로 설정
default_start_date = end_date - timedelta(days=365) 

start_date = st.sidebar.date_input(
    "📊 데이터 조회 시작 날짜",
    value=default_start_date,
    min_value=datetime(2000, 1, 1),
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
st.sidebar.caption("본 웹페이지는 투자 참고용이며, 투자의 책임은 사용자에게 있습니다.")


# --- 5. 데이터 로드 및 처리 ---

if not selected_stocks:
    st.warning("☝️ 먼저 왼쪽 사이드바에서 조회할 종목을 하나 이상 선택해 주세요.")
else:
    # 선택된 종목만 필터링하여 데이터 로드
    selected_tickers = {name: TICKERS[name] for name in selected_stocks}
    
    # 데이터 로드 실행
    with st.spinner('데이터를 불러오는 중입니다... 잠시만 기다려 주세요.'):
        df_stocks = load_data(selected_tickers, start_date.strftime('%Y-%m-%d'))
    
    if not df_stocks.empty:
        
        # --- 6. 그래프 표시 (메인 화면) ---
        
        st.header(f"📅 {start_date.strftime('%Y-%m-%d')} 이후 종가 변화")
        
        # DataFrame 헤드 표시 (최신 데이터 확인용)
        st.subheader("📌 최신 종가 데이터")
        st.dataframe(df_stocks.tail(5).T.style.format("{:,.0f} 원"), use_container_width=True)


        # 사용자가 선택한 그래프 종류에 따라 차트 표시
        if chart_type == '선 그래프 (Line Chart)':
            st.subheader("📉 종목별 종가 선 그래프")
            st.line_chart(df_stocks, use_container_width=True)
            
        elif chart_type == '막대 그래프 (Bar Chart)':
            st.subheader("📊 일자별 종가 막대 그래프")
            # 막대 그래프는 각 종목의 일별 종가를 막대로 표시합니다.
            st.bar_chart(df_stocks, use_container_width=True)
            
        st.markdown("---")

        # --- 7. 데이터 테이블 표시 ---
        st.subheader("📚 전체 기간 주식 데이터")
        st.dataframe(df_stocks.style.format("{:,.0f} 원"), use_container_width=True)

    else:
        st.error("⚠️ 데이터를 불러오지 못했습니다. 종목 코드나 날짜 설정을 확인해 주세요.")
