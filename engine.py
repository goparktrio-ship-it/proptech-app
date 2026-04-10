import os
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd
import streamlit as st

# ==========================================
# 📊 1. 기초 설정 및 방문자 수 트래킹 엔진
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
COUNTER_FILE = os.path.join(current_dir, "visitor_count.json")

API_URLS = {
    "매매": "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade",
    "전월세": "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
}

GU_CODES = {
    "송파구": "11710", "강남구": "11680", "서초구": "11650",
    "강동구": "11740", "마포구": "11440", "용산구": "11170",
    "성동구": "11200", "과천시": "41290", "수지구": "41465",
    "영통구": "41117", 
    "하남시": "41450", "분당구": "41135",
    "동탄구(화성시)": "41597"
}

REGULATED_AREAS = [
    "서울특별시 (25개 구 전 지역 재지정)", 
    "경기 과천시", "경기 광명시", "경기 하남시", "경기 의왕시",
    "경기 성남시 (분당/수정/중원구)", 
    "경기 수원시 (영통/장안/팔달구)", 
    "경기 안양시 (동안구)", 
    "경기 용인시 (수지구)", 
    "경기 화성시 (동탄 등)"
]
ALL_AREAS = REGULATED_AREAS + ["그 외 수도권 (비규제지역)", "그 외 지방 (비규제지역)"]

@st.cache_data(ttl=60)
def read_visitor_data(file_path):
    if not os.path.exists(file_path):
        return {"total": 0, "daily": {}}
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {"total": 0, "daily": {}}

def update_and_get_visitor_count():
    today = datetime.now().strftime("%Y-%m-%d")
    data = read_visitor_data(COUNTER_FILE)
        
    if today not in data["daily"]:
        data["daily"][today] = 0
        
    if 'has_visited' not in st.session_state:
        data["total"] += 1
        data["daily"][today] += 1
        st.session_state['has_visited'] = True 
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
        read_visitor_data.clear()
            
    return data["total"], data["daily"][today]

# ==========================================
# 📡 2. 공공데이터 API 수집 엔진
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

# ==========================================
# 💰 3. 세금 계산 엔진 (취득세, 보유세, 양도세)
# ==========================================
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
            if residence_y >= 2.0:
                is_exempt_eligible = True
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
# 🏦 4. 대출 및 정책자금 계산 엔진
# ==========================================
def calculate_loan_payment(loan_amount_manwon, annual_rate, years, is_interest_only=False):
    principal = loan_amount_manwon * 10000
    monthly_rate = (annual_rate / 100) / 12
    total_months = years * 12
    
    if is_interest_only:
        monthly_payment = principal * monthly_rate
        total_interest = monthly_payment * total_months
    else:
        if monthly_rate == 0:
            monthly_payment = principal / total_months
        else:
            monthly_payment = principal * (monthly_rate * (1 + monthly_rate)**total_months) / ((1 + monthly_rate)**total_months - 1)
        total_payment = monthly_payment * total_months
        total_interest = total_payment - principal
        
    return monthly_payment, total_interest

def get_max_mortgage_ltv(is_regulated, is_capital_area, is_first_time, prop_price_manwon, current_homes):
    if current_homes == "2주택 이상":
        if is_regulated:
            return 0, 0, 0
        else:
            ratio = 0.60
    elif current_homes == "1주택":
        ratio = 0.40 if is_regulated else 0.70
    else: 
        ratio = 0.40 if is_regulated else 0.70
        if is_first_time:
            ratio = 0.70 
            
    calc_limit = prop_price_manwon * ratio
    
    if is_regulated or is_capital_area:
        if prop_price_manwon > 250000:
            max_limit = 20000
        elif prop_price_manwon > 150000:
            max_limit = 40000
        else:
            max_limit = 60000
    else:
        max_limit = 60000 if is_first_time else float('inf')
        
    final_limit = min(calc_limit, max_limit)
    return final_limit, ratio, max_limit

def check_policy_loan_eligibility(prop_price, income, is_married, has_newborn, is_capital_area, is_first_time):
    results = []
    
    if has_newborn and prop_price <= 90000 and income <= 20000:
        max_limit = 50000
        ltv_limit = prop_price * (0.80 if is_first_time else 0.70)
        final_newborn_limit = min(max_limit, ltv_limit)
        
        results.append({
            "name": "👶 신생아 특례대출",
            "rate": "1.6% ~ 3.3%",
            "limit": f"최대 {int(final_newborn_limit):,}만 원",
            "desc": "수도권 방공제 규제에서 제외되어 한도가 넉넉하게 나옵니다!"
        })
        
    didim_income_limit = 8500 if is_married else 6000
    didim_price_limit = 60000 if is_married else 50000
    is_low_income_exempt = (income <= 4000 and prop_price <= 30000)
    
    if income <= didim_income_limit and prop_price <= didim_price_limit:
        base_limit = 40000 if is_married else 25000
        ltv_limit = prop_price * (0.80 if is_first_time else 0.70)
        
        deduction = 0
        if is_capital_area and not is_low_income_exempt:
            deduction = 4800 
            
        final_didim_limit = min(base_limit, ltv_limit - deduction)
        
        desc_text = "저소득/무주택자를 위한 정부 지원 대출"
        if deduction > 0:
            desc_text = f"⚠️ [2025 최신 규제 반영] 수도권 방공제 약 {deduction}만 원이 차감된 실제 한도입니다."
            
        if final_didim_limit > 0:
            results.append({
                "name": "🏠 내집마련 디딤돌대출",
                "rate": "2.45% ~ 3.55%",
                "limit": f"최대 {int(final_didim_limit):,}만 원",
                "desc": desc_text
            })
            
    return results