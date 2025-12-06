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
                
                # 🚨 핵심 수정: 데이터가 DataFrame이 아닌 Series인지 명시적으로 확인
                if isinstance(close_series, pd.Series):
                    data[name] = close_series
                else:
                    # 'Close'를 추출했는데도 Series가 아닌 경우 경고 (데이터 구조 오류)
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
            # 구조 오류 발생 시 디버깅 정보 출력
            st.error(f"❌ 최종 데이터프레임 구조 오류: {e}")
            st.warning("데이터 구조 문제: 딕셔너리에 Series가 아닌 다른 값이 포함되었습니다.")
            
            # 문제의 원인 파악을 위한 디버깅 정보 출력
            for name, value in data.items():
                if not isinstance(value, pd.Series):
                    st.code(f"❗문제 종목: {name}, 값 유형: {type(value)}, 값: {value}")
            
            return pd.DataFrame()
            
    return pd.DataFrame()

# --- 4. 사이드바 입력 위젯 ---

# 🚨 수정된 설정: 조회 마감 날짜를 1년 전으로 고정하여 안정성 확보
end_date_
