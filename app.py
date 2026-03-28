import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET

# 🚨 스트림릿 기본 설정은 파일 맨 위에서 단 한 번만 실행해야 합니다!
st.set_page_config(page_title="프롭테크 통합 플랫폼", page_icon="🏢", layout="wide")

# ==========================================
# 1. 글로벌 환경 설정 및 상수 정의
# ==========================================
# 🚨 본인의 '일반 인증키(Encoding)'를 여기에 쏙 넣어주세요!
SERVICE_KEY = "6185985620d6525b8af9628d96468b183acefb64c58135f6cae9fc04f844fe6a"

API_URLS = {
    "매매": "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade",
    "전월세": "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
}

GU_CODES = {
    "송파구": "11710", "강남구": "11680", "서초구": "11650",
    "강동구": "11740", "마포구": "11440", "용산구": "11170",
    "성동구": "11200", "과천시": "41290", "수지구": "41465",
    "하남시": "41450", "분당구": "41135",
    "동탄구(화성시)": "41597"  # 👈 2025년 과거 데이터까지 모두 뚫어버리는 통합 만능 코드!
}

# 2025년 10월 지정 최신 조정대상지역 (2026년 기준)
REGULATED_AREAS = [
    "서울특별시 (25개 구 전 지역)", "경기 과천시", "경기 광명시", "경기 하남시", "경기 의왕시",
    "경기 성남시 (분당/수정/중원구)", "경기 수원시 (영통/장안/팔달구)", "경기 안양시 (동안구)", "경기 용인시 (수지구)"
]
ALL_AREAS = REGULATED_AREAS + ["그 외 수도권 (비규제지역)", "그 외 지방 (비규제지역)"]

# ==========================================
# 2. 백엔드(Back-end) 계산 및 데이터 수집 엔진
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_real_estate_data(category, lawd_cd, deal_ym, service_key):
    url = API_URLS.get(category)
    params = {
        'serviceKey': service_key, 'LAWD_CD': lawd_cd, 'DEAL_YMD': deal_ym,
        'numOfRows': '9999', 'pageNo': '1'
    }
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        err_msg = root.find('.//returnAuthMsg')
        if err_msg is not None and err_msg.text:
            return pd.DataFrame(), f"API 오류: {err_msg.text}"

        items = root.findall('.//item')
        if not items:
            return pd.DataFrame(), "해당 조건의 거래 데이터가 없습니다."

        data_list = [{child.tag: child.text for child in item} for item in items]
        return pd.DataFrame(data_list), None

    except Exception as e:
        return pd.DataFrame(), f"오류 발생: {e}"

def calculate_acquisition_tax(price_manwon, is_large_area, homes_count, is_regulated):
    price = price_manwon * 10000 
    
    if price_manwon <= 60000:
        base_rate = 0.01
    elif price_manwon <= 90000:
        base_rate = ((price_manwon / 10000) * (2/3) - 3) / 100
    else:
        base_rate = 0.03

    tax_rate = base_rate
    if homes_count in ["1주택 (무주택자 포함)", "일시적 2주택"]:
        tax_rate = base_rate
    elif homes_count == "2주택":
        tax_rate = 0.08 if is_regulated else base_rate
    elif homes_count == "3주택":
        tax_rate = 0.12 if is_regulated else 0.08
    elif homes_count == "4주택 이상 (법인 포함)":
        tax_rate = 0.12     

    if tax_rate == base_rate: 
        edu_rate = tax_rate * 0.1
        rural_rate = 0.002 if is_large_area else 0.0
    elif tax_rate == 0.08:
        edu_rate = 0.004
        rural_rate = 0.006 if is_large_area else 0.0
    elif tax_rate == 0.12:
        edu_rate = 0.004
        rural_rate = 0.010 if is_large_area else 0.0

    acquisition_tax = price * tax_rate
    edu_tax = price * edu_rate
    rural_tax = price * rural_rate
    total_tax = acquisition_tax + edu_tax + rural_tax
    
    return acquisition_tax, edu_tax, rural_tax, total_tax, tax_rate

# ==========================================
# 3. 화면 구성 모듈 (앱 1: 실거래가 및 전세가율)
# ==========================================
def run_real_estate_app():
    st.header("🏠 실거래가 및 갭투자 분석")
    st.markdown("#### 🔍 검색 조건 설정")
    
    col1, col2 = st.columns(2)
    with col1:
        selected_gu = st.selectbox("지역구 선택", list(GU_CODES.keys()))
        lawd_cd = GU_CODES[selected_gu]
    with col2:
        deal_ym = st.text_input("조회 년월 (YYYYMM)", value="202603")
        
    category = st.radio("분석 모드 선택", ["매매 실거래", "전월세 실거래", "🔥 갭투자 전세가율 분석"], horizontal=True)
    submit_btn = st.button("데이터 분석 시작 🚀", use_container_width=True)

    if submit_btn:
        if category in ["매매 실거래", "전월세 실거래"]:
            api_cat = "매매" if category == "매매 실거래" else "전월세"
            with st.spinner(f'{selected_gu} {api_cat} 데이터를 가져오는 중...'):
                df, error_msg = fetch_real_estate_data(api_cat, lawd_cd, deal_ym, SERVICE_KEY)
                
                if error_msg:
                    st.error(error_msg)
                    st.session_state['info'] = None 
                elif not df.empty:
                    st.session_state['data'] = df
                    st.session_state['info'] = {'gu': selected_gu, 'ym': deal_ym, 'cat': api_cat, 'mode': '단순조회'}
                    st.success("✅ 데이터 조회를 완료했습니다!")

        elif category == "🔥 갭투자 전세가율 분석":
            with st.spinner(f'{selected_gu} 매매 및 전세 데이터를 융합 분석 중...'):
                df_trade, err_trade = fetch_real_estate_data("매매", lawd_cd, deal_ym, SERVICE_KEY)
                df_rent, err_rent = fetch_real_estate_data("전월세", lawd_cd, deal_ym, SERVICE_KEY)
                
                if err_trade or err_rent:
                    st.error(f"데이터를 불러오지 못했습니다. (매매: {err_trade} / 전월세: {err_rent})")
                    st.session_state['info'] = None
                else:
                    st.session_state['data_trade'] = df_trade
                    st.session_state['data_rent'] = df_rent
                    st.session_state['info'] = {'gu': selected_gu, 'ym': deal_ym, 'mode': '전세가율'}
                    st.success("✅ 매매/전세 데이터 융합 및 전세가율 계산 완료!")

    # ==============================
    # 📊 데이터 화면 출력 로직
    # ==============================
    if 'info' in st.session_state and st.session_state['info'] is not None:
        info = st.session_state['info']
        
        # --- 1. 단순 실거래가 조회 모드 ---
        if info['mode'] == '단순조회' and 'data' in st.session_state:
            df = st.session_state['data'].copy()
            
            if info['cat'] == "매매":
                target_cols = ['umdNm', 'aptNm', 'dealAmount', 'excluUseAr', 'floor', 'dealYear', 'dealMonth', 'dealDay']
                exist_cols = [c for c in target_cols if c in df.columns]
                df = df[exist_cols]
                df = df.rename(columns={'umdNm': '법정동', 'aptNm': '아파트명', 'dealAmount': '매매가(만원)', 'excluUseAr': '면적(㎡)', 'floor': '층', 'dealYear': '년', 'dealMonth': '월', 'dealDay': '일'})
                price_col = '매매가(만원)' 
            else:
                target_cols = ['umdNm', 'aptNm', 'deposit', 'monthlyRent', 'excluUseAr', 'floor', 'dealYear', 'dealMonth', 'dealDay']
                exist_cols = [c for c in target_cols if c in df.columns]
                df = df[exist_cols]
                df = df.rename(columns={'umdNm': '법정동', 'aptNm': '아파트명', 'deposit': '보증금(만원)', 'monthlyRent': '월세(만원)', 'excluUseAr': '면적(㎡)', 'floor': '층', 'dealYear': '년', 'dealMonth': '월', 'dealDay': '일'})
                price_col = '보증금(만원)' 

            st.markdown("---")
            st.subheader(f"🏘️ {info['gu']} 상세 동 필터링 ({info['ym']} / {info['cat']})")
            
            dong_list = sorted(df['법정동'].dropna().unique().tolist())
            selected_dong = st.selectbox("원하시는 '동'을 선택하세요", ["전체보기"] + dong_list, key="simple_dong")
            
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
                    col2.metric(f"최고가 🏆 ({max_row['아파트명']})", f"{int(max_row['num_price']):,} 만원")
                    col3.metric(f"최저가 📉 ({min_row['아파트명']})", f"{int(min_row['num_price']):,} 만원")
                else:
                    col2.metric("최고가", "데이터 없음")
                    col3.metric("최저가", "데이터 없음")

            st.markdown("<br>", unsafe_allow_html=True) 
            st.dataframe(df, use_container_width=True)

        # --- 2. 🚨 갭투자 전세가율 분석 모드 ---
        elif info['mode'] == '전세가율' and 'data_trade' in st.session_state:
            df_t = st.session_state['data_trade'].copy()
            df_r = st.session_state['data_rent'].copy()
            
            if not df_t.empty and not df_r.empty:
                df_t['num_price'] = pd.to_numeric(df_t['dealAmount'].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce')
                df_r['num_deposit'] = pd.to_numeric(df_r['deposit'].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce')
                
                # 🚨 핵심 업데이트: 면적(평수) 데이터 추출! (소수점 첫째 자리까지만 맞춰서 같은 평수로 묶기)
                df_t['num_area'] = pd.to_numeric(df_t['excluUseAr'], errors='coerce').round(1)
                df_r['num_area'] = pd.to_numeric(df_r['excluUseAr'], errors='coerce').round(1)
                
                if 'monthlyRent' in df_r.columns:
                    df_r['num_rent'] = pd.to_numeric(df_r['monthlyRent'].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce')
                    df_jeonse = df_r[(df_r['num_rent'] == 0) | (df_r['num_rent'].isna())]
                else:
                    df_jeonse = df_r

                # 🚨 단지명 + '전용면적'까지 완벽하게 일치하는 것끼리 그룹화!
                avg_trade = df_t.dropna(subset=['num_price', 'num_area']).groupby(['umdNm', 'aptNm', 'num_area'])['num_price'].mean().reset_index()
                avg_jeonse = df_jeonse.dropna(subset=['num_deposit', 'num_area']).groupby(['umdNm', 'aptNm', 'num_area'])['num_deposit'].mean().reset_index()

                # 🚨 동, 아파트명, 면적이 '모두' 똑같은 데이터만 융합!
                merged = pd.merge(avg_trade, avg_jeonse, on=['umdNm', 'aptNm', 'num_area'], how='inner')
                
                if not merged.empty:
                    merged['전세가율(%)'] = (merged['num_deposit'] / merged['num_price']) * 100
                    merged['필요갭(만원)'] = merged['num_price'] - merged['num_deposit']
                    
                    # 칼럼 이름 예쁘게 다듬기
                    merged = merged.rename(columns={'umdNm': '법정동', 'aptNm': '아파트명', 'num_area': '전용면적(㎡)'})
                    merged['평균매매가(만원)'] = merged['num_price'].astype(int)
                    merged['평균전세가(만원)'] = merged['num_deposit'].astype(int)
                    merged['필요갭(만원)'] = merged['필요갭(만원)'].astype(int)
                    merged['전세가율(%)'] = merged['전세가율(%)'].round(1)
                    
                    merged = merged[['법정동', '아파트명', '전용면적(㎡)', '평균매매가(만원)', '평균전세가(만원)', '필요갭(만원)', '전세가율(%)']]
                    merged = merged.sort_values('전세가율(%)', ascending=False).reset_index(drop=True)

                    # 🚨 조회 년월을 사람이 읽기 편하게 변환 (예: 202602 -> 2026년 2월)
                    year_month_str = f"{info['ym'][:4]}년 {int(info['ym'][4:]):d}월"

                    st.markdown("---")
                    st.subheader(f"🔥 {info['gu']} 갭투자 랭킹 (전세가율 기준)")
                    st.info(f"💡 **분석 기간:** {year_month_str} 한 달간\n💡 **매칭 조건:** 동일 단지, **동일 면적(평수)**에서 매매와 전세가 모두 거래된 경우만 분석")
                    
                    dong_list_gap = sorted(merged['법정동'].dropna().unique().tolist())
                    selected_dong_gap = st.selectbox("📍 집중 분석할 '동'을 선택하세요", ["구 전체보기"] + dong_list_gap, key="gap_dong")
                    
                    if selected_dong_gap != "구 전체보기":
                        merged = merged[merged['법정동'] == selected_dong_gap].reset_index(drop=True)

                    if not merged.empty:
                        st.markdown(f"#### 🏆 **{selected_dong_gap if selected_dong_gap != '구 전체보기' else info['gu']} TOP 5**")
                        top_n = min(5, len(merged)) 
                        
                        for i in range(top_n):
                            row = merged.iloc[i]
                            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🏅"
                            
                            # 🚨 아파트명 옆에 [면적]을 똭! 기간도 똭! 명시합니다.
                            st.success(f"{medal} **{i+1}위 | {row['아파트명']} ({row['전용면적(㎡)']}㎡)** - {row['법정동']}\n"
                                       f"👉 **전세가율: {row['전세가율(%)']}%** / **필요 갭 자금: {row['필요갭(만원)']:,}만 원**\n\n"
                                       f"*(기준: {year_month_str} | 평균 매매가: {row['평균매매가(만원)']:,}만 / 평균 전세가: {row['평균전세가(만원)']:,}만)*")

                        st.markdown("<br>", unsafe_allow_html=True)
                        st.dataframe(merged, use_container_width=True)
                    else:
                        st.warning(f"🚨 선택하신 '{selected_dong_gap}'에는 {year_month_str}에 매매와 전세가 '동일 면적'으로 거래된 데이터가 없습니다.")
                else:
                    st.warning(f"🚨 {year_month_str}에 매매와 전세가 '완벽히 같은 면적'으로 거래된 아파트 단지가 없습니다. (예: 84㎡는 매매만, 59㎡는 전세만 거래된 경우 매칭 제외)")
            else:
                st.warning("데이터가 부족하여 전세가율을 계산할 수 없습니다.")
                
               
# ==========================================
# 4. 화면 구성 모듈 (앱 2: 세금 계산기)
# ==========================================
def run_tax_app():
    st.header("💰 주택 취득세 계산")
    st.info("📌 **적용 기준: 2025년 10월 대책 반영 (2026년 최신 기준)**")
    st.markdown("매수 지역과 주택 수만 선택하세요. **최신 규제지역 여부와 중과세율을 앱이 자동으로 판단**합니다.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. 매수할 물건 정보")
        selected_area = st.selectbox("어느 지역의 아파트를 매수하시나요?", ALL_AREAS)
        is_regulated = selected_area in REGULATED_AREAS
        
        price_input = st.number_input("매매가 (만원 단위)", min_value=1000, value=80000, step=1000)
        st.caption(f"💡 입력 금액: {price_input/10000:.1f}억 원")
        is_large = st.checkbox("전용면적 85㎡ 초과 (농특세 부과)")

    with col2:
        st.subheader("2. 매수자 주택 수")
        homes_count = st.selectbox("취득 후 총 주택 수", [
            "1주택 (무주택자 포함)", "일시적 2주택", "2주택", "3주택", "4주택 이상 (법인 포함)"
        ])
        
        st.markdown("<br>", unsafe_allow_html=True)
        if is_regulated:
            st.error(f"🚨 **{selected_area}**는 현재 **조정대상지역**입니다.")
            if homes_count == "일시적 2주택":
                st.info("💡 **[일시적 2주택 혜택]** 기한 내 기존 주택 처분 조건으로 **기본세율(1~3%)**이 적용됩니다!")
            elif homes_count in ["2주택", "3주택"]:
                st.warning("⚠️ 다주택자 조정지역 중과세율이 무겁게 적용됩니다.")
        else:
            st.success(f"✅ **{selected_area}**는 **비규제지역**입니다.")
            if homes_count == "2주택":
                st.info("💡 비규제지역 2주택까지는 중과 없이 **기본세율(1~3%)**이 적용됩니다.")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("세금 정밀 계산하기 🚀", use_container_width=True):
        acq_tax, edu_tax, rural_tax, total_tax, final_rate = calculate_acquisition_tax(
            price_input, is_large, homes_count, is_regulated
        )
        
        st.markdown("---")
        st.subheader("📊 예상 취득세 분석 결과")
        st.warning(f"**적용된 취득세 본세율:** {final_rate * 100:.1f}%")
        
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("① 취득세", f"{int(acq_tax):,} 원")
        m_col2.metric("② 지방교육세", f"{int(edu_tax):,} 원")
        m_col3.metric("③ 농어촌특별세", f"{int(rural_tax):,} 원")
        
        st.success(f"💸 **총 납부 예상 세금 (합계): {int(total_tax):,} 원**")

    st.markdown("---")
    st.info(
        "📌 **[다주택자 취득세 중과 시점 안내]**\n"
        "- **2주택부터 중과:** 계약일과 잔금일 **모두 조정지역**인 경우\n"
        "- **3주택부터 중과:** 계약일 또는 잔금일 중 **하루라도 비규제지역**인 경우"
    )

# ==========================================
# 5. 메인 네비게이션 (상단 탭으로 모바일 가독성 극대화!)
# ==========================================
def main():
    # 🎨 CSS 마법: 윗통수 잘림 방지용 '안전 여백' 적용!
    st.markdown("""
    <style>
        /* 🚨 1. 너무 바짝 붙이지 않고 숨 쉴 공간(3rem)을 줍니다! */
        .block-container {
            padding-top: 3rem !important; 
            padding-bottom: 1rem !important;
        }
        
        /* 2. 입체형 버튼 탭 디자인 유지 */
        div[data-baseweb="tab-list"] { gap: 10px; }
        button[data-baseweb="tab"] {
            font-size: 18px !important;
            font-weight: bold !important;
            background-color: #f0f2f6 !important;
            border-radius: 12px 12px 0px 0px !important;
            padding: 12px 20px !important;
            color: #555555 !important;
            border-bottom: none !important;
        }
        button[aria-selected="true"] {
            background-color: #FF4B4B !important;
            color: white !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # 🚨 대문 제목: 마이너스(-20px)로 멱살 잡던 걸 풀고(0px) 안전하게 내려놨습니다.
    st.markdown("<h1 style='text-align: center; color: #1E3A8A; margin-top: 0px;'>🏢 집스탯 (ZipStat) PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555555; font-size: 16px; margin-bottom: 20px;'>실거래가 분석부터 취득세 계산까지 원클릭으로!</p>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🏠 실거래가 조회", "💰 주택 취득세 계산"])
    
    with tab1:
        run_real_estate_app()
        
    with tab2:
        run_tax_app()
        
    st.markdown("---")
    st.caption("💡 본 대시보드는 실무 참고용이며, 정확한 세금 계산은 세무 전문가와 상담하시기 바랍니다.")

if __name__ == "__main__":
    main()
    
    
    
