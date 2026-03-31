import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime

st.set_page_config(
    page_title="집스탯 PRO", 
    page_icon="🏢", 
    layout="wide", 
    initial_sidebar_state="collapsed" 
)

# ==========================================
# 📊 방문자 수 트래킹 엔진
# ==========================================
COUNTER_FILE = "visitor_count.json"

def update_and_get_visitor_count():
    today = datetime.now().strftime("%Y-%m-%d")
    
    if not os.path.exists(COUNTER_FILE):
        data = {"total": 0, "daily": {}}
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
            
    with open(COUNTER_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    if today not in data["daily"]:
        data["daily"][today] = 0
        
    if 'has_visited' not in st.session_state:
        data["total"] += 1
        data["daily"][today] += 1
        st.session_state['has_visited'] = True 
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
            
    return data["total"], data["daily"][today]

# ==========================================
# 1. 글로벌 환경 설정 및 상수 정의
# ==========================================
if "DATA_API_KEY" in st.secrets:
    SERVICE_KEY = st.secrets["DATA_API_KEY"]
else:
    SERVICE_KEY = "여기에_인증키를_넣어주세요"

API_URLS = {
    "매매": "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade",
    "전월세": "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
}

GU_CODES = {
    "송파구": "11710", "강남구": "11680", "서초구": "11650",
    "강동구": "11740", "마포구": "11440", "용산구": "11170",
    "성동구": "11200", "과천시": "41290", "수지구": "41465",
    "하남시": "41450", "분당구": "41135",
    "동탄구(화성시)": "41597"
}

REGULATED_AREAS = [
    "서울특별시 (25개 구 전 지역)", "경기 과천시", "경기 광명시", "경기 하남시", "경기 의왕시",
    "경기 성남시 (분당/수정/중원구)", "경기 수원시 (영통/장안/팔달구)", "경기 안양시 (동안구)", "경기 용인시 (수지구)", "경기 화성시 (동탄 등)"
]
ALL_AREAS = REGULATED_AREAS + ["그 외 수도권 (비규제지역)", "그 외 지방 (비규제지역)"]

# ==========================================
# 2. 백엔드 데이터 수집 및 세금 계산 엔진
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

def get_last_12_months(end_ym):
    year, month = int(end_ym[:4]), int(end_ym[4:])
    months = []
    for _ in range(12):
        months.append(f"{year}{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return months

def calculate_acquisition_tax(price_manwon, is_large_area, homes_count, is_regulated):
    price = price_manwon * 10000 
    
    if price_manwon <= 60000: base_rate = 0.01
    elif price_manwon <= 90000: base_rate = ((price_manwon / 10000) * (2/3) - 3) / 100
    else: base_rate = 0.03

    tax_rate = base_rate
    if homes_count in ["1주택", "일시적 2주택"]: tax_rate = base_rate
    elif homes_count == "2주택": tax_rate = 0.08 if is_regulated else base_rate
    elif homes_count == "3주택": tax_rate = 0.12 if is_regulated else 0.08
    elif homes_count == "4주택 이상 (법인 포함)": tax_rate = 0.12     

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
    
    return acquisition_tax, edu_tax, rural_tax, total_tax, tax_rate, base_rate

def get_comp_tax_amount(tax_base):
    if tax_base <= 0: return 0
    if tax_base <= 300000000: return tax_base * 0.005
    elif tax_base <= 600000000: return 1500000 + (tax_base - 300000000) * 0.007
    elif tax_base <= 1200000000: return 3600000 + (tax_base - 600000000) * 0.01
    else: return 9600000 + (tax_base - 1200000000) * 0.013 

def calculate_holding_tax(official_price_manwon, homes_count, is_joint):
    official_price = official_price_manwon * 10000 

    is_special = (homes_count == "1주택" and official_price_manwon <= 90000)

    if homes_count == "1주택":
        if official_price_manwon <= 30000: fmv_ratio_prop = 0.43
        elif official_price_manwon <= 60000: fmv_ratio_prop = 0.44
        else: fmv_ratio_prop = 0.45
    else:
        fmv_ratio_prop = 0.60

    tax_base_prop = official_price * fmv_ratio_prop

    if is_special:
        if tax_base_prop <= 60000000: prop_tax = tax_base_prop * 0.0005
        elif tax_base_prop <= 150000000: prop_tax = 30000 + (tax_base_prop - 60000000) * 0.001
        elif tax_base_prop <= 300000000: prop_tax = 120000 + (tax_base_prop - 150000000) * 0.0015
        else: prop_tax = 345000 + (tax_base_prop - 300000000) * 0.0035
    else:
        if tax_base_prop <= 60000000: prop_tax = tax_base_prop * 0.001
        elif tax_base_prop <= 150000000: prop_tax = 60000 + (tax_base_prop - 60000000) * 0.0015
        elif tax_base_prop <= 300000000: prop_tax = 195000 + (tax_base_prop - 150000000) * 0.002
        else: prop_tax = 495000 + (tax_base_prop - 300000000) * 0.004

    city_tax = tax_base_prop * 0.0014
    edu_tax_prop = prop_tax * 0.2
    total_prop_tax = prop_tax + city_tax + edu_tax_prop

    if is_joint:
        per_person_price = official_price / 2
        per_person_deduction = 900000000 
        tax_base_comp_per_person = max(0, per_person_price - per_person_deduction) * 0.60
        comp_tax_per_person = get_comp_tax_amount(tax_base_comp_per_person)
        comp_tax = comp_tax_per_person * 2 
    else:
        deduction = 1200000000 if homes_count == "1주택" else 900000000
        tax_base_comp = max(0, official_price - deduction) * 0.60 
        comp_tax = get_comp_tax_amount(tax_base_comp)

    if comp_tax > 0:
        rural_tax_comp = comp_tax * 0.2 
        total_comp_tax = comp_tax + rural_tax_comp
    else:
        total_comp_tax = 0

    return official_price, total_prop_tax, total_comp_tax

def check_regulation_status(area_type, yyyymm_str, mode="buy"):
    try:
        ym = int(yyyymm_str)
    except:
        return False, "날짜 형식을 숫자로 정확히 입력해주세요. (예: 202105)"

    if ym < 201708:
        msg = "비규제 시기"
        is_reg = False
    elif "①" in area_type:
        msg = "지속적 조정대상지역 유지"
        is_reg = True
    elif "②" in area_type or "③" in area_type: 
        if 201708 <= ym <= 202212:
            msg = "과거 규제지역 지정 시기"
            is_reg = True
        elif 202301 <= ym <= 202509:
            msg = "2023.1.5 규제 전면 해제 시기"
            is_reg = False
        elif ym >= 202510:
            msg = "2025.10.15 대책 재지정 시기"
            is_reg = True
    elif "④" in area_type: 
        if 201708 <= ym <= 202211:
            msg = "과거 규제지역 지정 시기"
            is_reg = True
        elif 202212 <= ym <= 202509:
            msg = "22.11.14 1차 규제 해제 시기"
            is_reg = False
        elif ym >= 202510:
            msg = "2025.10.15 대책 재지정 시기"
            is_reg = True
    elif "⑤" in area_type: 
        if 201708 <= ym <= 202211:
            msg = "과거 규제지역 지정 시기"
            is_reg = True
        elif ym >= 202212:
            msg = "규제 해제 후 현재까지 비규제 유지 (25.10 재지정 제외)"
            is_reg = False
    else:
        msg = "전면 비규제 지역"
        is_reg = False

    if mode == "buy":
        if is_reg:
            return True, f"🚨 {msg} 취득 → 1주택 비과세 받으려면 **거주요건 2년 필수**"
        else:
            if ym < 201708:
                return False, f"✅ 2017.8.2 대책 이전 취득 → **거주요건 면제** (보유만 해도 됨)"
            else:
                return False, f"✅ {msg} 취득 → **거주요건 면제** (보유만 해도 됨)"
    else:
        if is_reg:
            return True, f"🚨 {msg} 양도 → **다주택자 양도세 중과 대상 (세율 폭탄 주의)**"
        else:
            return False, f"✅ {msg} 양도 → **다주택자 양도세 중과 배제 (일반세율 적용)**"

def calculate_capital_gains_tax(sell_price_m, buy_price_m, expenses_m, holding_y, residence_y, homes_count, is_reg_buy, is_reg_sell, is_suspension=False, is_joint_sell=False):
    sell_price = sell_price_m * 10000
    buy_price = buy_price_m * 10000
    expenses = expenses_m * 10000
    
    gain = sell_price - buy_price - expenses
    if gain <= 0:
        return 0, 0, 0, 0, 0, 0, "양도차익 없음 (세금 0원)", 0.0

    is_1house = homes_count in ["1주택", "일시적 2주택"]
    is_exempt_eligible = False
    
    if is_1house and holding_y >= 2.0:
        if is_reg_buy:
            if residence_y >= 2.0: is_exempt_eligible = True
        else:
            is_exempt_eligible = True

    if is_exempt_eligible:
        if sell_price_m <= 120000:
            return gain, 0, 0, 0, 0, 0, "✅ 1세대 1주택 비과세 대상 (납부세액 0원)", 0.0
        else:
            taxable_gain = gain * ((sell_price - 1200000000) / sell_price)
            status_msg = "⚠️ 1주택 비과세 요건 충족 (단, 고가주택 12억 초과분 과세)"
    else:
        taxable_gain = gain
        status_msg = "🚨 일반 과세 (비과세 요건 미충족 또는 다주택자)"

    deduction_rate = 0.0
    if holding_y >= 3.0:
        if homes_count in ["2주택", "3주택 이상"] and is_reg_sell and not is_suspension:
            deduction_rate = 0.0  
            status_msg += " + 장특공 배제"
        elif is_exempt_eligible:
            h_rate = min(int(holding_y) * 0.04, 0.40)
            r_rate = min(int(residence_y) * 0.04, 0.40) if residence_y >= 2.0 else 0.0
            deduction_rate = h_rate + r_rate
        else:
            deduction_rate = min(int(holding_y) * 0.02, 0.30)
            
    if is_suspension and homes_count in ["2주택", "3주택 이상"] and is_reg_sell:
        status_msg += " (✨ 중과 유예 적용: 일반세율 및 장특공 부활)"
            
    deduction_amount = taxable_gain * deduction_rate
    net_gain = taxable_gain - deduction_amount  
    
    if is_joint_sell:
        net_gain_per_person = net_gain / 2
        calc_tax_base = net_gain_per_person - 2500000
        if calc_tax_base <= 0:
            return gain, taxable_gain, deduction_amount, 0, 0, 0, status_msg + " (과표 0원)", deduction_rate
        status_msg = "🤝 [부부 공동명의 절세 적용] " + status_msg
    else:
        calc_tax_base = net_gain - 2500000
        if calc_tax_base <= 0:
            return gain, taxable_gain, deduction_amount, 0, 0, 0, status_msg + " (과표 0원)", deduction_rate

    if calc_tax_base <= 14000000: rate, prog_deduct = 0.06, 0
    elif calc_tax_base <= 50000000: rate, prog_deduct = 0.15, 1080000
    elif calc_tax_base <= 88000000: rate, prog_deduct = 0.24, 5580000
    elif calc_tax_base <= 150000000: rate, prog_deduct = 0.35, 15260000
    elif calc_tax_base <= 300000000: rate, prog_deduct = 0.38, 19760000
    elif calc_tax_base <= 500000000: rate, prog_deduct = 0.40, 25760000
    elif calc_tax_base <= 1000000000: rate, prog_deduct = 0.42, 35760000
    else: rate, prog_deduct = 0.45, 65760000

    surcharge = 0.0
    
    if is_reg_sell and not is_suspension:
        if homes_count == "2주택": 
            surcharge = 0.20
            status_msg += " 🚨 [2주택 중과 +20%p]"
        elif homes_count == "3주택 이상": 
            surcharge = 0.30
            status_msg += " 🚨 [3주택 중과 +30%p]"

    final_rate = rate + surcharge
    calculated_tax = (calc_tax_base * final_rate) - prog_deduct

    short_term_tax = 0
    if holding_y < 1.0:
        short_term_tax = calc_tax_base * 0.70  
    elif holding_y < 2.0:
        short_term_tax = calc_tax_base * 0.60  

    if short_term_tax > calculated_tax:
        calculated_tax = short_term_tax
        final_rate = 0.70 if holding_y < 1.0 else 0.60
        status_msg += " 💥 (단기양도 중과가 더 커서 단기세율 최우선 적용)"

    local_tax = calculated_tax * 0.1
    total_tax_per_person = calculated_tax + local_tax
    
    if is_joint_sell:
        total_tax = total_tax_per_person * 2
    else:
        total_tax = total_tax_per_person

    return gain, taxable_gain, deduction_amount, calc_tax_base, final_rate, total_tax, status_msg, deduction_rate

# ==========================================
# 3. 화면 구성 모듈 (앱 1: 실거래가/전세가율)
# ==========================================
def run_real_estate_app():
    st.subheader("🏠 실거래가/전세가율")
    st.markdown("#### 🔍 검색 조건 설정")
    
    col1, col2 = st.columns(2)
    with col1:
        selected_gu = st.selectbox("**지역구 선택**", list(GU_CODES.keys()))
        lawd_cd = GU_CODES[selected_gu]
    with col2:
        deal_ym = st.text_input("**조회 년월 (YYYYMM)**", value="202602")
        
    category = st.radio("**분석 모드 선택**", ["매매 실거래", "전월세 실거래", "전세가율(실투자금) 분석", "🚀 1년 내 최고가 분석"], horizontal=True)
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

        elif category == "전세가율(실투자금) 분석":
            with st.spinner(f'{selected_gu} 데이터 융합 분석 중...'):
                df_trade, err_trade = fetch_real_estate_data("매매", lawd_cd, deal_ym, SERVICE_KEY)
                df_rent, err_rent = fetch_real_estate_data("전월세", lawd_cd, deal_ym, SERVICE_KEY)
                
                if err_trade or err_rent:
                    st.error(f"데이터를 불러오지 못했습니다. (매매: {err_trade} / 전월세: {err_rent})")
                    st.session_state['info'] = None
                else:
                    st.session_state['data_trade'] = df_trade
                    st.session_state['data_rent'] = df_rent
                    st.session_state['info'] = {'gu': selected_gu, 'ym': deal_ym, 'mode': '전세가율'}
                    st.success("✅ 전세가율 계산 완료!")
                    
        elif category == "🚀 1년 내 최고가 분석":
            months_to_fetch = get_last_12_months(deal_ym)
            all_data = []
            
            progress_text = "과거 1년 치 실거래가 데이터를 수집 중입니다. (최대 10초 소요 🥷)"
            my_bar = st.progress(0, text=progress_text)
            
            for i, ym in enumerate(months_to_fetch):
                df, _ = fetch_real_estate_data("매매", lawd_cd, ym, SERVICE_KEY)
                if not df.empty:
                    df['조회년월'] = ym
                    all_data.append(df)
                
                my_bar.progress((i + 1) / 12, text=f"{selected_gu} {ym} 데이터 수집 완료... ({i+1}/12)")
            
            if all_data:
                df_all = pd.concat(all_data, ignore_index=True)
                st.session_state['data_high'] = df_all
                st.session_state['info'] = {'gu': selected_gu, 'ym': deal_ym, 'mode': '최고가'}
                st.success("✅ 1년 치 최고가 판독 완료!")
            else:
                st.error("데이터를 불러오지 못했습니다.")
                st.session_state['info'] = None

    if 'info' in st.session_state and st.session_state['info'] is not None:
        info = st.session_state['info']
        
        if info['mode'] == '단순조회' and 'data' in st.session_state:
            df = st.session_state['data'].copy()
            if info['cat'] == "매매":
                target_cols = ['umdNm', 'aptNm', 'dealAmount', 'excluUseAr', 'floor', 'dealYear', 'dealMonth', 'dealDay']
                exist_cols = [c for c in target_cols if c in df.columns]
                df = df[exist_cols].rename(columns={'umdNm': '법정동', 'aptNm': '아파트명', 'dealAmount': '매매가(만원)', 'excluUseAr': '면적(㎡)', 'floor': '층', 'dealYear': '년', 'dealMonth': '월', 'dealDay': '일'})
                price_col = '매매가(만원)' 
            else:
                target_cols = ['umdNm', 'aptNm', 'deposit', 'monthlyRent', 'excluUseAr', 'floor', 'dealYear', 'dealMonth', 'dealDay']
                exist_cols = [c for c in target_cols if c in df.columns]
                df = df[exist_cols].rename(columns={'umdNm': '법정동', 'aptNm': '아파트명', 'deposit': '보증금(만원)', 'monthlyRent': '월세(만원)', 'excluUseAr': '면적(㎡)', 'floor': '층', 'dealYear': '년', 'dealMonth': '월', 'dealDay': '일'})
                price_col = '보증금(만원)' 

            st.markdown("---")
            st.subheader(f"🏘️ {info['gu']} 상세 동 필터링 ({info['ym']} / {info['cat']})")
            dong_list = sorted(df['법정동'].dropna().unique().tolist())
            selected_dong = st.selectbox("**원하시는 '동'을 선택하세요**", ["전체보기"] + dong_list, key="simple_dong")
            if selected_dong != "전체보기": df = df[df['법정동'] == selected_dong]
            
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

            st.markdown("<br>", unsafe_allow_html=True) 
            st.dataframe(df, use_container_width=True)

        elif info['mode'] == '전세가율' and 'data_trade' in st.session_state:
            df_t, df_r = st.session_state['data_trade'].copy(), st.session_state['data_rent'].copy()
            if not df_t.empty and not df_r.empty:
                df_t['num_price'] = pd.to_numeric(df_t['dealAmount'].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce')
                df_r['num_deposit'] = pd.to_numeric(df_r['deposit'].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce')
                df_t['num_area'] = pd.to_numeric(df_t['excluUseAr'], errors='coerce').round(1)
                df_r['num_area'] = pd.to_numeric(df_r['excluUseAr'], errors='coerce').round(1)
                
                df_jeonse = df_r[(pd.to_numeric(df_r['monthlyRent'], errors='coerce') == 0) | (df_r['monthlyRent'].isna())]
                avg_t = df_t.dropna(subset=['num_price', 'num_area']).groupby(['umdNm', 'aptNm', 'num_area'])['num_price'].mean().reset_index()
                avg_r = df_jeonse.dropna(subset=['num_deposit', 'num_area']).groupby(['umdNm', 'aptNm', 'num_area'])['num_deposit'].mean().reset_index()
                merged = pd.merge(avg_t, avg_r, on=['umdNm', 'aptNm', 'num_area'], how='inner')
                
                if not merged.empty:
                    merged['전세가율(%)'] = (merged['num_deposit'] / merged['num_price'] * 100).round(1)
                    merged['실투자금(만원)'] = (merged['num_price'] - merged['num_deposit']).astype(int)
                    merged = merged.rename(columns={'umdNm': '법정동', 'aptNm': '아파트명', 'num_area': '전용면적(㎡)', 'num_price': '평균매매가(만원)', 'num_deposit': '평균전세가(만원)'})
                    merged = merged.sort_values('전세가율(%)', ascending=False).reset_index(drop=True)

                    year_month_str = f"{info['ym'][:4]}년 {int(info['ym'][4:]):d}월"
                    st.markdown("---")
                    st.markdown(f"#### 📊 {info['gu']} 전세가율 상위 단지")
                    st.info(f"💡 **분석 기간:** {year_month_str} 한 달간\n\n💡 **매칭 조건:** 동일 단지, **동일 면적(평수)**에서 매매와 전세가 모두 거래된 경우만 분석")
                    
                    dong_list_gap = sorted(merged['법정동'].dropna().unique().tolist())
                    sel_dong_gap = st.selectbox("**집중 분석할 '동' 선택**", ["구 전체보기"] + dong_list_gap, key="gap_dong")
                    if sel_dong_gap != "구 전체보기": merged = merged[merged['법정동'] == sel_dong_gap].reset_index(drop=True)

                    if not merged.empty:
                        st.markdown(f"#### 🏆 **{sel_dong_gap if sel_dong_gap != '구 전체보기' else info['gu']} TOP 5**")
                        for i in range(min(5, len(merged))):
                            row = merged.iloc[i]
                            st.info(f"### {'🥇🥈🥉🏅🏅'[i]} {i+1}위: {row['아파트명']}\n**📍 {row['법정동']} | 📐 {row['전용면적(㎡)']}㎡**\n\n📊 **전세가율: {row['전세가율(%)']}%**\n\n💰 **예상 실투자금: {row['실투자금(만원)']:,}만 원**")
                        with st.expander("📊 전체 데이터 보기"): st.dataframe(merged, use_container_width=True)

        elif info['mode'] == '최고가' and 'data_high' in st.session_state:
            df = st.session_state['data_high'].copy()
            df['num_price'] = pd.to_numeric(df['dealAmount'].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce')
            df['num_area'] = pd.to_numeric(df['excluUseAr'], errors='coerce').round(1)
            df = df.dropna(subset=['num_price', 'num_area'])
            
            max_p = df.groupby(['umdNm', 'aptNm', 'num_area'])['num_price'].max().reset_index().rename(columns={'num_price': '1년최고가(만원)'})
            df_t = df[df['조회년월'] == info['ym']]
            target_p = df_t.groupby(['umdNm', 'aptNm', 'num_area'])['num_price'].max().reset_index().rename(columns={'num_price': '당월최고가(만원)'})
            merged = pd.merge(target_p, max_p, on=['umdNm', 'aptNm', 'num_area'], how='inner')
            new_highs = merged[merged['당월최고가(만원)'] >= merged['1년최고가(만원)']].sort_values('당월최고가(만원)', ascending=False).reset_index(drop=True)

            st.markdown("---")
            st.markdown(f"#### 🚀 {info['gu']} 1년 내 최고가 단지")
            st.info(f"💡 **기준월:** {info['ym'][:4]}년 {int(info['ym'][4:]):d}월\n\n💡 **조건:** 최근 12개월 실거래 중 **최고가를 갱신**한 단지")
            
            if not new_highs.empty:
                dong_list_h = sorted(new_highs['umdNm'].dropna().unique().tolist())
                sel_dong_h = st.selectbox("**집중 분석할 '동' 선택**", ["구 전체보기"] + dong_list_h, key="high_dong")
                if sel_dong_h != "구 전체보기": new_highs = new_highs[new_highs['umdNm'] == sel_dong_h].reset_index(drop=True)

                if not new_highs.empty:
                    for i in range(min(5, len(new_highs))):
                        row = new_highs.iloc[i]
                        st.success(f"### {'🏆🔥'[min(1, i)]} {row['aptNm']}\n**📍 {row['umdNm']} | 📐 {row['num_area']}㎡**\n\n🚀 **최고가: {int(row['당월최고가(만원)']):,}만 원**")
                    with st.expander("📊 전체 데이터 보기"): st.dataframe(new_highs, use_container_width=True)

# ==========================================
# 4. 화면 구성 모듈 (앱 2: 취득세/보유세 계산)
# ==========================================
def run_tax_app():
    st.subheader("💰 취득세/보유세 계산")
    st.info("📌 **적용 기준: 2026년 최신 세법 기준 (재산세/종부세 포함)**")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🏢 1. 매수할 물건 정보")
        selected_area = st.selectbox("**어느 지역의 아파트를 매수하시나요?**", ALL_AREAS)
        is_regulated = selected_area in REGULATED_AREAS
        price_input = st.number_input("**매매가 (만원 단위)**", min_value=1000, value=80000, step=1000)
        st.caption(f"💡 입력 금액: {price_input/10000:.1f}억 원")
        is_large = st.checkbox("전용면적 85㎡ 초과 (농특세 부과)")

    with col2:
        st.markdown("#### 👤 2. 매수자 명의 및 주택 수")
        homes_count = st.selectbox("**취득 후 총 주택 수**", ["1주택", "일시적 2주택", "2주택", "3주택", "4주택 이상 (법인 포함)"])
        
        with st.expander("❓ 내 주택수 정확히 세는 법 (취득세 기준)"):
            st.markdown("""
            - **👨‍👩‍👧‍👦 1세대:** 주민등록표상 가족 합산 (배우자/미혼 30세 미만 자녀 포함)
            - **🎫 분양권/입주권:** **'20. 8. 12. 이후** 취득분부터 포함
            - **🏢 주거용 오피스텔:** **'20. 8. 12. 이후** 취득분부터 포함 (시가 1억 이하 제외)
            - **🛡️ 제외:** 시가표준액 1억 이하 주택, 농어촌 주택 등
            """)
            
        is_joint = st.checkbox("🤝 **부부 공동명의 (지분 50:50)**")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if is_joint and homes_count == "1주택":
            st.info("💡 공동명의 1주택: 각자 9억씩 총 **18억 원의 종부세 기본공제** 혜택이 적용됩니다.")
        if is_regulated: st.error(f"🚨 **{selected_area}**는 조정대상지역입니다.")
        else: st.success(f"✅ **{selected_area}**는 비규제지역입니다.")

    st.markdown("---")
    default_official_price = int(price_input * 0.7)
    
    with st.expander("⚙️ 상세 설정 (공시가격 직접 수정)"):
        st.markdown("보유세는 매매가가 아닌 '공시가격' 기준입니다. 기본적으로 **매매가의 70%**로 자동 계산됩니다.")
        use_manual = st.checkbox("**☑️ 정확한 공시가격을 직접 입력하겠습니다.**")
        if use_manual:
            official_price_input = st.number_input("**정확한 공시가격 (만원 단위)**", min_value=100, value=default_official_price, step=1000)
        else:
            official_price_input = default_official_price
            st.write(f"현재 자동 추정된 공시가격: **{official_price_input:,}만 원**")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("세금 정밀 계산하기 🚀", use_container_width=True, key="btn_tax"):
        acq_tax, edu_tax, rural_tax, total_tax, final_rate, base_rate = calculate_acquisition_tax(price_input, is_large, homes_count, is_regulated)
        off_p_won, prop_p_won, comp_p_won = calculate_holding_tax(official_price_input, homes_count, is_joint)
        
        st.markdown("---")
        st.markdown("#### 📊 1. 예상 취득세 결과")
        
        if final_rate > base_rate:
            st.error(f"🚨 **적용 본세율:** {final_rate * 100:.1f}% **(다주택 중과세율 적용)**")
        else:
            st.success(f"✅ **적용 본세율:** {final_rate * 100:.1f}% **(기본세율 적용)**")
            
        c1, c2, c3 = st.columns(3)
        c1.metric("① 취득세", f"{int(acq_tax):,} 원")
        c2.metric("② 지방교육세", f"{int(edu_tax):,} 원")
        c3.metric("③ 농특세", f"{int(rural_tax):,} 원")
        st.success(f"💸 **총 납부 예상 취득세: {int(total_tax):,} 원**")

        st.markdown("---")
        st.markdown("#### 📊 2. 예상 연간 보유세 결과")
        st.info(f"💡 **기준 공시가격:** {int(off_p_won):,} 원")
        h1, h2, h3 = st.columns(3)
        h1.metric("① 재산세", f"{int(prop_p_won):,} 원")
        h2.metric("② 종부세", f"{int(comp_p_won):,} 원")
        h3.metric("③ 총 보유세", f"{int(prop_p_won + comp_p_won):,} 원")
        st.error(f"💸 **매년 납부 예상 보유세: {int(prop_p_won + comp_p_won):,} 원**")

        with st.expander("📝 산출 기준 안내"):
            st.markdown("""
            **1. 다주택 취득세 중과**<br>현행 지방세법에 따라 2주택(조정 8%), 3주택(조정 12%, 비조정 8%), 4주택 이상(12%) 중과세율을 반영합니다.<br><br>
            **2. 공시가격 현실화율**<br>별도 입력이 없으면 **매매가의 70%**를 공시가로 자동 추정합니다.<br><br>
            **3. 종부세 명의별 공제액**<br>단독명의 1주택(12억), 부부 공동명의 1주택(각 9억씩 총 18억), 다주택자(9억) 기준을 적용했습니다.<br><br>
            **4. 다주택자 종부세 산출 한계**<br>본 계산기의 종부세 견적은 유저의 '기존 보유 주택 공시가격'을 알 수 없으므로, **"현재 입력한 단일 물건"**만을 기준으로 산출된 참고용 데이터입니다.<br><br>
            **5. 공정시장가액비율**<br>재산세(1주택 43~45%, 다주택 60%), 종부세(60%) 일괄 적용했습니다.<br><br>
            **6. 특례세율**<br>1주택자 9억 이하 재산세 특례세율(-0.05%p)이 자동 적용되었습니다.<br><br>
            **7. 세부담상한**<br>전년도 세액 부재로 인해 **상한선(105~150%) 미적용(MAX치)** 기준입니다.
            """, unsafe_allow_html=True)

# ==========================================
# 5. 화면 구성 모듈 (앱 3: 양도소득세 정밀 입력기)
# ==========================================
def run_capital_gains_tax_app():
    st.subheader("📈 양도소득세 계산 (Beta)")
    st.info("📌 **매수/매도 시점의 규제지역 여부**를 앱이 자동으로 판독하여 거주요건 및 중과 여부를 체크합니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🏢 1. 거래 금액 및 기간")
        sell_price = st.number_input("**매도 금액 (양도가액, 만원)**", min_value=1000, value=150000, step=1000)
        buy_price = st.number_input("**매수 금액 (취득가액, 만원)**", min_value=1000, value=80000, step=1000)
        expenses = st.number_input("**필요경비 (중개보수, 수리비 등, 만원)**", min_value=0, value=2000, step=100)
        
        profit = sell_price - buy_price - expenses
        st.caption(f"💡 단순 양도차익: **{profit/10000:.1f}억 원**")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### ⏳ 2. 보유 및 거주 기간")
        holding_period = st.number_input("**총 보유 기간 (년)**", min_value=0.0, max_value=50.0, value=3.0, step=0.5)
        residence_period = st.number_input("**총 거주 기간 (년)**", min_value=0.0, max_value=50.0, value=2.0, step=0.5)
        
        if residence_period > holding_period:
            st.error("🚨 거주 기간은 보유 기간을 초과할 수 없습니다.")

    with col2:
        st.markdown("#### 🚨 3. 자동 규제지역 판독기 (2000년~현재)")
        
        cgt_area = st.selectbox("**📍 양도 물건 지역**", [
            "① 서울 강남/서초/송파/용산",
            "② 서울 그 외 21개 자치구",
            "③ 과천/광명/하남/성남(분당·수정)",
            "④ 의왕/용인수지/안양동안/수원(영통/장안/팔달)",
            "⑤ 화성동탄/구리/세종 등 (과거해제)",
            "⑥ 전국 전면 비규제 지역"
        ])
        
        with st.expander("❓ 내 아파트, 규제지역 번호 찾기 (상세 지역 및 연혁)"):
            st.markdown("""
            **🚨 셀렉트박스 번호별 상세 구역 및 규제 연혁**<br>
            
            **① 서울 강남/서초/송파/용산**<br>
            * **상세 구역:** 서울 강남구, 서초구, 송파구, 용산구 전역<br>
            * **연혁:** 2017년 8.2 대책 이후 단 한 번도 해제된 적 없이 **지속적 조정대상지역 유지** (투기과열지구 포함)
            <br><br>
            
            **② 서울 그 외 21개 자치구**<br>
            * **상세 구역:** 종로구, 중구, 성동구, 광진구, 동대문구, 중랑구, 성북구, 강북구, 도봉구, 노원구, 은평구, 서대문구, 마포구, 양천구, 강서구, 구로구, 금천구, 영등포구, 동작구, 관악구, 강동구<br>
            * **연혁:** 과거 지정 → **23. 1. 5. 규제 전면 해제** → 25. 10. 15. 대책으로 **재지정**
            <br><br>
            
            **③ 과천/광명/하남/성남(분당·수정)**<br>
            * **상세 구역:** 경기 과천시, 광명시, 하남시, 성남시 분당구, 성남시 수정구<br>
            * **연혁:** 과거 지정 → **23. 1. 5. 규제 전면 해제** → 25. 10. 15. 대책으로 **재지정**
            <br><br>
            
            **④ 의왕/용인수지/안양동안/수원(영통/장안/팔달) 등**<br>
            * **상세 구역:** 경기 의왕시, 용인시 수지구, 안양시 동안구, 성남시 중원구, 수원시 영통구, 수원시 장안구, 수원시 팔달구<br>
            * **연혁:** 과거 지정 → **22. 11. 14. 1차 규제 해제** → 25. 10. 15. 대책으로 **재지정**
            <br><br>
            
            **⑤ 화성동탄/구리/세종 등 (과거 해제 후 영구 비규제)**<br>
            * **상세 구역:** 화성시(동탄 등), 구리시, 수원시 권선구, 안양시 만안구, 고양시, 남양주시, 평택시, 인천광역시, 세종특별자치시 등 과거 규제로 묶였던 **그 외 모든 지역**<br>
            * **연혁:** 과거 지정 → **22. 11. 14. (또는 그 이전) 전면 해제** 후 현재까지 영구 비규제 유지 (25.10 대책 재지정 제외됨)
            <br><br>
            
            **⑥ 전국 전면 비규제 지역**<br>
            * **상세 구역:** 위 ①~⑤에 단 한 번도 속한 적 없는 그 외 모든 대한민국 영토 (강원, 제주, 영호남 등)<br>
            * **연혁:** 규제지역으로 묶인 역사가 없어 취득 시점 무관하게 거주요건 2년이 무조건 면제되며, 양도세 중과도 없습니다.
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**[매수 시점 규제 확인]**")
        buy_ym = st.text_input("**매수년월 (YYYYMM)**", value="202105")
        is_reg_buy, msg_buy = check_regulation_status(cgt_area, buy_ym, mode="buy")
        
        is_pinset_buy = st.checkbox("💡 단, 매수 당시 우리 동네(읍/면/동)는 '핀셋 규제'로 지정 제외되었습니다.")
        
        with st.expander("❓ 핀셋 규제란?"):
            st.markdown("""
            구 단위로 규제지역을 묶을 때, 외곽에 위치한 읍/면/동이 억울하게 묶이는 것을 방지하기 위해 규제에서 **명시적으로 제외해 준 동네**를 뜻합니다. (예: 남양주 화도읍/수동면, 파주 문산읍, 용인 처인구 포곡읍 등)<br><br>
            *(Tip) 우리 동네가 핀셋 규제로 제외된 곳이라면, 위 체크박스를 누르시면 앱이 알아서 예외 처리(비규제 취급) 해 드립니다.*
            """, unsafe_allow_html=True)

        if is_pinset_buy:
            is_reg_buy = False
            msg_buy = "✅ 핀셋 규제 제외 지역 취득 → **거주요건 면제** (보유만 해도 됨)"

        if is_reg_buy:
            st.error(msg_buy)
        else:
            st.success(msg_buy)
            
        st.markdown("**[매도 시점 규제 확인]**")
        sell_ym = st.text_input("**매도(예정)년월 (YYYYMM)**", value="202604")
        is_reg_sell, msg_sell = check_regulation_status(cgt_area, sell_ym, mode="sell")
        
        is_pinset_sell = st.checkbox("💡 단, 매도하는 현재 우리 동네는 '핀셋 규제'로 해제되었습니다.")
        if is_pinset_sell:
            is_reg_sell = False
            msg_sell = "✅ 핀셋 규제 제외 지역 양도 → **다주택자 양도세 중과 배제 (일반세율 적용)**"

        if is_reg_sell:
            st.error(msg_sell)
        else:
            st.success(msg_sell)

        st.markdown("<br>", unsafe_allow_html=True)
        homes_count_sell = st.selectbox("**매도 시점 총 주택 수**", ["1주택", "일시적 2주택", "2주택", "3주택 이상"])
        
        with st.expander("❓ 내 주택수 정확히 세는 법 (양도세 기준)"):
            st.markdown("""
            - **👨‍👩‍👧‍👦 1세대:** 실제 생계를 같이 하는 가족 합산 (배우자는 분리해도 1세대)
            - **🎫 분양권/입주권:** 분양권은 **'21. 1. 1. 이후** 취득분부터 포함 (입주권은 상시 포함)
            - **🏢 주거용 오피스텔:** 실제 주거용 사용 시 **취득일 무관하게 모두 포함**
            - **🛡️ 중과 제외:** 수도권/광역시 외 **지방 공시가 3억 이하** 등 제외
            """)

        is_joint_sell = st.checkbox("🤝 **부부 공동명의 (지분 50:50)**", key="cgt_joint")
        
        st.markdown("<br>", unsafe_allow_html=True)
        is_suspension = st.checkbox("💡 **다주택자 양도세 중과 유예 적용** (2026. 5. 9. 양도분까지)")

    st.markdown("---")
    
    if st.button("양도세 정밀 계산하기 🚀", use_container_width=True, key="btn_cgt"):
        if holding_period <= 0:
            st.error("보유 기간은 0년보다 커야 합니다.")
        else:
            gain, tax_gain, deduct_amt, tax_base, rate, total_tax, status_msg, deduct_rate = calculate_capital_gains_tax(
                sell_price, buy_price, expenses, holding_period, residence_period, homes_count_sell, is_reg_buy, is_reg_sell, is_suspension, is_joint_sell
            )
            
            st.markdown("---")
            st.markdown(f"#### 📊 양도소득세 산출 결과")
            st.info(f"💡 **적용 상태:** {status_msg}")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("① 총 양도차익", f"{int(gain):,} 원")
            c2.metric("② 과세대상 양도차익", f"{int(tax_gain):,} 원")
            c3.metric(f"③ 장기보유특별공제 ({deduct_rate * 100:.0f}%)", f"- {int(deduct_amt):,} 원")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            c4, c5, c6 = st.columns(3)
            
            tb_label = "④ 과세표준 (1인 기준)" if is_joint_sell else "④ 과세표준 (기본공제 반영)"
            c4.metric(tb_label, f"{int(tax_base):,} 원")
            c5.metric("⑤ 적용 최고세율", f"{rate * 100:.1f}%")
            
            if is_joint_sell:
                st.error(f"💸 **⑥ 총 납부 예상 양도소득세 (부부 합산): {int(total_tax):,} 원** (지방세 포함)")
            else:
                st.error(f"💸 **⑥ 총 납부 예상 양도소득세: {int(total_tax):,} 원** (지방세 포함)")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 🚨 [UI 변경] 일시적 2주택 비과세 "1·2·3 법칙" 추가 패치!
    with st.expander("🔍 1세대 1주택 & 일시적 2주택 비과세 요건 (핵심 요약)"):
        st.markdown("""
        **📌 1세대 1주택 비과세**
        * **보유:** 취득일로부터 **2년 이상 보유** 필수
        * **거주:** 취득 당시 **조정대상지역**이었다면 **2년 이상 거주** 필수 (비규제 취득 시 면제)
        * **고가주택:** 양도가액 **12억 원** 이하 비과세 (12억 초과분은 비율만큼 과세)
        <br><br>
        **⏳ 일시적 2주택 비과세 [1·2·3 법칙]**
        * **[1] 1년 텀:** 기존 주택 취득 후 **1년 이상 지나서** 신규 주택 취득
        * **[2] 2년 보유/거주:** 기존 주택을 **2년 이상 보유** (취득 당시 조정대상지역이면 2년 거주 필수)
        * **[3] 3년 내 매도:** 신규 주택 취득일로부터 **3년 이내**에 기존 주택 매도
        """, unsafe_allow_html=True)

# ==========================================
# 6. 메인 네비게이션
# ==========================================
def main():
    st.markdown("""
    <style>
        .block-container { padding-top: 3rem !important; }
        div[data-baseweb="tab-list"] { gap: 5px; }
        button[data-baseweb="tab"] {
            font-size: 16px !important; font-weight: bold !important;
            background-color: #f0f2f6 !important; border-radius: 12px 12px 0px 0px !important;
            padding: 10px 15px !important; color: #555555 !important;
        }
        button[aria-selected="true"] { background-color: #FF4B4B !important; color: white !important; }
        @media screen and (max-width: 430px) { button[data-baseweb="tab"] { font-size: 13px !important; } }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.title("⚙️ 프롭테크 메뉴")
        total, daily = update_and_get_visitor_count()
        st.markdown("---")
        c1, c2 = st.columns(2)
        c1.metric("오늘 방문", f"{daily} 명")
        c2.metric("총 방문", f"{total} 명")

    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏢 집스탯 (ZipStat) PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555555;'>실거래가 분석부터 세금 계산까지 원클릭으로!</p>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🏠 실거래가/전세가율", "💰 취득세/보유세 계산", "📈 양도세 계산 (Beta)"])
    
    with tab1: 
        run_real_estate_app()
        
    with tab2: 
        run_tax_app()
        
    with tab3:
        run_capital_gains_tax_app()
        
    st.markdown("---")
    st.caption("💡 본 대시보드는 실무 참고용이며, 정확한 세금 계산은 세무 전문가와 상담하시기 바랍니다.")

if __name__ == "__main__":
    main()


