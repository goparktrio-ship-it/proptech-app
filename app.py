import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET

# ==========================================
# 1. 환경 설정 및 상수 정의
# ==========================================
# 🚨 본인의 '일반 인증키(Encoding)'를 여기에 쏙 넣어주세요!
SERVICE_KEY = "6185985620d6525b8af9628d96468b183acefb64c58135f6cae9fc04f844fe6a"

# 국토부 최신 공식 API 주소 (매매, 전월세)
API_URLS = {
    "매매": "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade",
    "전월세": "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
}

# 유저가 선택하기 쉬운 한글 지역구와 법정동 코드 사전 (수지구, 과천시 포함 완벽 세팅!)
GU_CODES = {
    "송파구": "11710", "강남구": "11680", "서초구": "11650",
    "강동구": "11740", "마포구": "11440", "용산구": "11170",
    "성동구": "11200", "과천시": "41290", "수지구": "41465",
    "분당구": "41135"
}

# ==========================================
# 2. 데이터 수집 엔진 (Back-end 로직)
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_real_estate_data(category, lawd_cd, deal_ym, service_key):
    url = API_URLS.get(category)
    #params = {'serviceKey': service_key, 'LAWD_CD': lawd_cd, 'DEAL_YMD': deal_ym}
    # [기존 코드] 10개만 주던 소심한 요청서
    # params = {'serviceKey': service_key, 'LAWD_CD': lawd_cd, 'DEAL_YMD': deal_ym}

    # [수정할 코드] 🚨 잔말 말고 9999개 다 내놓으라는 터프한 요청서!
    params = {
        'serviceKey': service_key, 
        'LAWD_CD': lawd_cd, 
        'DEAL_YMD': deal_ym,
        'numOfRows': '9999',  # 👈 핵심! 한 번에 최대 9999건까지 다 가져옵니다.
        'pageNo': '1'         # 1페이지부터 시작!
    }
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        err_msg = root.find('.//returnAuthMsg')
        if err_msg is not None and err_msg.text:
            return pd.DataFrame(), f"공공데이터 API 오류: {err_msg.text}"

        items = root.findall('.//item')
        if not items:
            return pd.DataFrame(), "해당 조건의 거래 데이터가 없습니다."

        data_list = [{child.tag: child.text for child in item} for item in items]
        return pd.DataFrame(data_list), None

    except requests.exceptions.Timeout:
        return pd.DataFrame(), "서버 응답 시간이 초과되었습니다. (네트워크 지연)"
    except requests.exceptions.RequestException as e:
        return pd.DataFrame(), f"네트워크 연결에 실패했습니다: {e}"
    except ET.ParseError:
        return pd.DataFrame(), "데이터 형식이 잘못되었습니다. (서버 응답 오류)"
    except Exception as e:
        return pd.DataFrame(), f"예상치 못한 오류가 발생했습니다: {e}"

# ==========================================
# 3. 화면 구성 및 실행 (Front-end 로직) - 모바일 최적화 버전 📱
# ==========================================
def main():
    st.set_page_config(page_title="프롭테크 통합 대시보드", page_icon="🏠", layout="wide")
    st.title("🏠 실거래가 통합 조회 서비스")

    # 🚨 [변경됨] 귀찮은 사이드바를 없애고 메인 화면으로 당당하게 꺼냈습니다!
    st.markdown("#### 🔍 검색 조건 설정")
    
    # 모바일 화면을 알뜰하게 쓰기 위해 입력칸을 두 칸으로 쪼갭니다.
    col1, col2 = st.columns(2)
    with col1:
        selected_gu = st.selectbox("지역구 선택", list(GU_CODES.keys()))
        lawd_cd = GU_CODES[selected_gu]
    with col2:
        deal_ym = st.text_input("조회 년월", value="202401")
        
    # 라디오 버튼도 가로로 눕혀서 공간을 절약합니다.
    category = st.radio("거래 유형 선택", ["매매", "전월세"], horizontal=True)
    
    # 버튼을 큼지막하게, 화면 너비에 꽉 차게 만듭니다! (모바일 터치 최적화)
    submit_btn = st.button("데이터 분석 시작 🚀", use_container_width=True)

    # --- 데이터 수집 및 세션 저장 ---
    if submit_btn:
        with st.spinner(f'{selected_gu} {category} 데이터를 안전하게 가져오는 중...'):
            df, error_msg = fetch_real_estate_data(category, lawd_cd, deal_ym, SERVICE_KEY)
            
            if error_msg:
                st.error(error_msg)
                st.session_state['data'] = None 
            elif not df.empty:
                st.session_state['data'] = df
                st.session_state['info'] = {'gu': selected_gu, 'ym': deal_ym, 'cat': category}
                st.success("✅ 데이터 조회를 완료했습니다!")

    # --- 화면에 데이터와 동 필터 그리기 ---
    if 'data' in st.session_state and st.session_state['data'] is not None:
        df = st.session_state['data'].copy()
        info = st.session_state['info']
        
        # (이하 영문->한글 번역 로직은 완전히 동일합니다!)
        if info['cat'] == "매매":
            target_cols = ['umdNm', 'aptNm', 'dealAmount', 'excluUseAr', 'floor', 'dealYear', 'dealMonth', 'dealDay']
            exist_cols = [c for c in target_cols if c in df.columns]
            df = df[exist_cols]
            df = df.rename(columns={
                'umdNm': '법정동', 'aptNm': '아파트명', 'dealAmount': '매매가(만원)', 
                'excluUseAr': '면적(㎡)', 'floor': '층', 
                'dealYear': '년', 'dealMonth': '월', 'dealDay': '일'
            })
            price_col = '매매가(만원)' 
            
        else:
            target_cols = ['umdNm', 'aptNm', 'deposit', 'monthlyRent', 'excluUseAr', 'floor', 'dealYear', 'dealMonth', 'dealDay']
            exist_cols = [c for c in target_cols if c in df.columns]
            df = df[exist_cols]
            df = df.rename(columns={
                'umdNm': '법정동', 'aptNm': '아파트명', 'deposit': '보증금(만원)', 'monthlyRent': '월세(만원)', 
                'excluUseAr': '면적(㎡)', 'floor': '층', 
                'dealYear': '년', 'dealMonth': '월', 'dealDay': '일'
            })
            price_col = '보증금(만원)' 

        st.markdown("---")
        st.subheader(f"🏘️ {info['gu']} 상세 동 필터링 ({info['ym']} / {info['cat']})")
        
        dong_list = sorted(df['법정동'].dropna().unique().tolist())
        selected_dong = st.selectbox("원하시는 '동'을 선택하세요", ["전체보기"] + dong_list)
        
        if selected_dong != "전체보기":
            df = df[df['법정동'] == selected_dong]
        
        if price_col in df.columns:
            temp_df = df.copy()
            temp_df['num_price'] = pd.to_numeric(temp_df[price_col].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce')
            valid_df = temp_df.dropna(subset=['num_price'])
            
            col1, col2, col3 = st.columns(3)
            col1.metric("총 거래건수", f"{len(df)} 건")
            
            if not valid_df.empty:
                max_row = valid_df.loc[valid_df['num_price'].idxmax()]
                min_row = valid_df.loc[valid_df['num_price'].idxmin()]
                
                max_p = int(max_row['num_price'])
                max_apt = max_row['아파트명']
                
                min_p = int(min_row['num_price'])
                min_apt = min_row['아파트명']
                
                col2.metric(f"최고가 🏆 ({max_apt})", f"{max_p:,} 만원")
                col3.metric(f"최저가 📉 ({min_apt})", f"{min_p:,} 만원")
            else:
                col2.metric("최고가", "데이터 없음")
                col3.metric("최저가", "데이터 없음")

        st.markdown("<br>", unsafe_allow_html=True) 
        st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
    

