import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime

from PIL import Image  # 이미지를 불러오기 위한 모듈 추가

# 1. 현재 실행 중인 app.py 파일이 있는 폴더 경로를 자동으로 가져옵니다.
# (이 코드를 사용하면 터미널을 어디서 실행하든 상관없어집니다!)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. 그 폴더 경로와 'logo.png' 이름을 합쳐서 전체 경로를 만듭니다.
logo_path = os.path.join(current_dir, "logo.png")

try:
    # 3. 계산된 전체 경로로 이미지를 불러옵니다.
    logo_img = Image.open(logo_path)
    
    # 4. 페이지 설정에 적용합니다.
    st.set_page_config(
        page_title="집스탯 PRO V2.1",
        page_icon=logo_img,
        layout="wide",
        initial_sidebar_state="expanded"
    )
except FileNotFoundError:
    # 혹시라도 파일이 정말 없을 때를 대비한 예외 처리
    st.error(f"이미지 파일을 찾을 수 없습니다: {logo_path}")
    st.set_page_config(page_title="집스탯 PRO V2.1", page_icon="🏢")

# 이후 나머지 앱 코드 작성...


#{
#"component": "LlmGeneratedComponent",
#"props": {
#"height": "650px",
#"prompt": "Create an interactive tutor widget to help a user debug a FileNotFoundError in a Streamlit app. \n\n1. Objective: Visualize the project folder structure, show a simplified app.py code snippet, and simulate different run scenarios to illustrate how the working directory affects relative file paths.\n2. Structure: \n    * Main Section:\n        * Visual representation of the folder structure (e.g., Main/, app.py, logo.png in the same directory).\n        * A Code Snippet Viewer displaying the essential from PIL import Image and logo_img = Image.open(\"logo.png\") lines, with the filename parameter highlighted.\n        * Simulation Controls: Two buttons labeled '프로젝트 루트에서 실행' (Run from Project Root) and '외부 폴더에서 실행' (Run from Outside).\n    * Output Section:\n        * An App Preview area below the controls. \n    * Explanation Section: A text area below the preview.\n3. Behavior:\n    * Initial State: Visual structure shows app.py and logo.png in the same directory. The Code Viewer highlights 'logo.png'. The App Preview is empty or shows a generic placeholder. The Explanation states that running from the correct directory is crucial.\n    * User Action (프로젝트 루트에서 실행): When this button is clicked, simulate success: the visual structure highlights logo.png, the Code Viewer might show a subtle success indicator (no horizontal layout splits), the App Preview displays a generic simulated logo image (not a named color/specific design), and the Explanation explains that because the app ran from the root, logo.png was found relative to app.py as coded. Avoid horizontal splits. Use only generic functional language for styling.\n    * User Action (외부 폴더에서 실행): When this button is clicked, simulate failure: The visual structure shows a missing or failed indicator for logo.png, the App Preview shows a clear 'ERROR: 파일을 찾을 수 없습니다' (FileNotFoundError) overlay, and the Explanation explains that because the app ran from outside the project folder, it looked for logo.png in the wrong place and failed, even though the files are in the same folder on disk. Avoid horizontal splits. Use only generic functional language for styling.\n4. Data: Use the user's specific filenames logo.png and app.py and directory structure description. Use generalized code snippets. All UI text and explanations must be in Korean, translating terms like 'File Not Found Error', 'Working Directory', 'Relative Path', 'Project Root', 'Run', 'Code', 'Output', 'Preview' where appropriate, or keeping them in English if they are technical standard terms common in Korean context and better left as is for user clarity (like app.py, logo.png, FileNotFoundError). Be precise and consistent with terms like 앱 파일, 이미지 파일, 실행 위치. Do not use named colors, fonts, horizontal splits, placeholders like 'Sample Data', persistence, or suggest external resources."
#}
#}

# 내가 만든 로고 이미지 파일 불러오기
logo_img = Image.open("logo.png")

# ==========================================
# 0. 기본 설정 및 스타일링
# ==========================================
#st.set_page_config(
#   page_title="집스탯 PRO V2.1", 
#    page_icon="🏢", 
#    layout="wide", 
#    initial_sidebar_state="expanded" 
#)

# page_icon 자리에 이모지 대신 img 변수를 쏙 넣기
st.set_page_config(
    page_title="집스탯 PRO V2.1", 
    page_icon=logo_img,  # 👈 여기가 핵심!
    layout="wide", 
    initial_sidebar_state="expanded" 
)
# 공통 설명문 CSS 스타일 (모바일 최적화: 14px, 줄간격 1.6, 순수 HTML 사용)
DETAIL_STYLE = "<div style='font-size: 14px; line-height: 1.6; color: #444;'>"

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
    SERVICE_KEY = ""

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
# 3. 대출 및 정책자금 계산 엔진
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

# ==========================================
# 4. 화면 구성 (앱 1: 실거래가)
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
    submit_btn = st.button("데이터 분석 시작 🚀", use_container_width=True, type="primary")

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
                    st.error("데이터를 불러오지 못했습니다.")
                    st.session_state['info'] = None
                else:
                    st.session_state['data_trade'] = df_trade
                    st.session_state['data_rent'] = df_rent
                    st.session_state['info'] = {'gu': selected_gu, 'ym': deal_ym, 'mode': '전세가율'}
                    st.success("✅ 전세가율 계산 완료!")
                    
        elif category == "🚀 1년 내 최고가 분석":
            months_to_fetch = get_last_12_months(deal_ym)
            all_data = []
            my_bar = st.progress(0, text="과거 1년 치 실거래가 데이터를 수집 중입니다.")
            
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
            st.subheader(f"🏘️ {info['gu']} 상세 동 필터링")
            dong_list = sorted(df['법정동'].dropna().unique().tolist())
            selected_dong = st.selectbox("**'동'을 선택하세요**", ["전체보기"] + dong_list, key="simple_dong")
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
                    col2.metric(f"최고가 🏆", f"{int(max_row['num_price']):,} 만원")
                    col3.metric(f"최저가 📉", f"{int(min_row['num_price']):,} 만원")

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

                    st.markdown("---")
                    st.markdown(f"#### 📊 {info['gu']} 전세가율 상위 단지")
                    dong_list_gap = sorted(merged['법정동'].dropna().unique().tolist())
                    sel_dong_gap = st.selectbox("**'동' 선택**", ["구 전체보기"] + dong_list_gap, key="gap_dong")
                    if sel_dong_gap != "구 전체보기":
                        merged = merged[merged['법정동'] == sel_dong_gap].reset_index(drop=True)

                    if not merged.empty:
                        for i in range(min(5, len(merged))):
                            row = merged.iloc[i]
                            st.info(f"### {i+1}위: {row['아파트명']}\n**📍 {row['법정동']} | 📐 {row['전용면적(㎡)']}㎡**\n\n📊 **전세가율: {row['전세가율(%)']}%**\n💰 **예상 실투자금: {row['실투자금(만원)']:,}만 원**")
                        with st.expander("📊 전체 데이터 보기"):
                            st.dataframe(merged, use_container_width=True)

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
            
            if not new_highs.empty:
                dong_list_h = sorted(new_highs['umdNm'].dropna().unique().tolist())
                sel_dong_h = st.selectbox("**'동' 선택**", ["구 전체보기"] + dong_list_h, key="high_dong")
                if sel_dong_h != "구 전체보기":
                    new_highs = new_highs[new_highs['umdNm'] == sel_dong_h].reset_index(drop=True)

                if not new_highs.empty:
                    for i in range(min(5, len(new_highs))):
                        row = new_highs.iloc[i]
                        st.success(f"### 🏆 {row['aptNm']}\n**📍 {row['umdNm']} | 📐 {row['num_area']}㎡**\n🚀 **최고가: {int(row['당월최고가(만원)']):,}만 원**")
                    with st.expander("📊 전체 데이터 보기"):
                        st.dataframe(new_highs, use_container_width=True)

# ==========================================
# 5. 화면 구성 (앱 2: 취득세/보유세)
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
        is_large = st.checkbox("전용면적 85㎡ 초과 (농특세 부과)")

    with col2:
        st.markdown("#### 👤 2. 매수자 명의 및 주택 수")
        homes_count = st.selectbox("**취득 후 총 주택 수**", ["1주택", "일시적 2주택", "2주택", "3주택", "4주택 이상 (법인 포함)"])
        
        with st.expander("❓ 내 주택수 정확히 세는 법 (취득세 기준)"):
            st.markdown(f"""{DETAIL_STYLE}
            <ul style='margin-top: 0; padding-left: 20px;'>
                <li><b>1세대:</b> 등본상 가족 (배우자/미혼 30세 미만 자녀 포함)</li>
                <li><b>분양권/입주권:</b> '20. 8. 12. 이후 취득분부터 포함</li>
                <li><b>주거용 오피스텔:</b> '20. 8. 12. 이후 취득분부터 포함 (시가 1억 이하 제외)</li>
                <li><b>제외:</b> 시가표준액 1억 이하 주택, 농어촌 주택 등</li>
            </ul>
            </div>""", unsafe_allow_html=True)
            
        is_joint = st.checkbox("🤝 **부부 공동명의 (지분 50:50)**")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if is_joint and homes_count == "1주택":
            st.info("💡 공동명의 1주택: 각자 9억씩 총 **18억 원의 종부세 기본공제** 혜택 적용")
        if is_regulated:
            st.error(f"🚨 **{selected_area}**는 조정대상지역입니다.")
        else:
            st.success(f"✅ **{selected_area}**는 비규제지역입니다.")

    st.markdown("---")
    default_official_price = int(price_input * 0.7)
    
    with st.expander("⚙️ 상세 설정 (공시가격 직접 수정)"):
        use_manual = st.checkbox("**☑️ 정확한 공시가격을 직접 입력하겠습니다.**")
        if use_manual:
            official_price_input = st.number_input("**정확한 공시가격 (만원 단위)**", min_value=100, value=default_official_price, step=1000)
        else:
            official_price_input = default_official_price
            st.write(f"현재 자동 추정된 공시가격: **{official_price_input:,}만 원**")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("세금 정밀 계산하기 🚀", use_container_width=True, key="btn_tax", type="primary"):
        acq_tax, edu_tax, rural_tax, total_tax, final_rate, base_rate = calculate_acquisition_tax(price_input, is_large, homes_count, is_regulated)
        off_p_won, prop_p_won, comp_p_won = calculate_holding_tax(official_price_input, homes_count, is_joint)
        
        st.markdown("---")
        st.markdown("#### 📊 1. 예상 취득세 결과")
        if final_rate > base_rate:
            st.error(f"🚨 **적용 본세율:** {final_rate * 100:.1f}% **(다주택 중과세율 적용)**")
        else:
            st.success(f"✅ **적용 본세율:** {final_rate * 100:.1f}% **(기본세율 적용)**")
            
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"<span style='font-size: 14px; color: #555;'>① 취득세</span><br><span style='font-size: 18px; font-weight: bold;'>{int(acq_tax):,} 원</span>", unsafe_allow_html=True)
        with c2: st.markdown(f"<span style='font-size: 14px; color: #555;'>② 지방교육세</span><br><span style='font-size: 18px; font-weight: bold;'>{int(edu_tax):,} 원</span>", unsafe_allow_html=True)
        with c3: st.markdown(f"<span style='font-size: 14px; color: #555;'>③ 농특세</span><br><span style='font-size: 18px; font-weight: bold;'>{int(rural_tax):,} 원</span>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="background-color: #fef9c3; padding: 20px; border-radius: 15px; border-left: 10px solid #facc15; margin-top: 15px;">
            <p style="margin: 0; color: #854d0e; font-weight: bold;">💸 총 납부 예상 취득세</p>
            <h2 style="margin: 0; color: #ca8a04; font-size: 2.2rem;">{int(total_tax):,} 원</h2>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📊 2. 예상 연간 보유세 결과")
        h1, h2, h3 = st.columns(3)
        with h1: st.markdown(f"<span style='font-size: 14px; color: #555;'>① 재산세</span><br><span style='font-size: 18px; font-weight: bold;'>{int(prop_p_won):,} 원</span>", unsafe_allow_html=True)
        with h2: st.markdown(f"<span style='font-size: 14px; color: #555;'>② 종부세</span><br><span style='font-size: 18px; font-weight: bold;'>{int(comp_p_won):,} 원</span>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="background-color: #fee2e2; padding: 20px; border-radius: 15px; border-left: 10px solid #ef4444; margin-top: 15px;">
            <p style="margin: 0; color: #991b1b; font-weight: bold;">💸 매년 납부 예상 총 보유세</p>
            <h2 style="margin: 0; color: #dc2626; font-size: 2.2rem;">{int(prop_p_won + comp_p_won):,} 원</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📝 산출 기준 요약 안내"):
        st.markdown(f"""{DETAIL_STYLE}
        <ul style='margin-top: 0; padding-left: 20px;'>
            <li><b>다주택 중과:</b> 2주택(조정 8%), 3주택(조정 12%, 비조정 8%), 4주택 이상(12%)</li>
            <li><b>공시가격:</b> 입력 없으면 매매가의 70% 추정</li>
            <li><b>종부세 공제:</b> 단독 12억, 부부공동 18억, 다주택 9억</li>
            <li><b>재산세/종부세 비율:</b> 재산세(43~60%), 종부세(60%) 및 1주택 특례세율 반영</li>
            <li><b>세부담상한:</b> 전년도 세액 부재로 상한선 미적용(MAX 산출)</li>
        </ul>
        </div>""", unsafe_allow_html=True)

# ==========================================
# 6. 화면 구성 (앱 3: 양도소득세)
# ==========================================
def run_capital_gains_tax_app():
    st.subheader("📈 양도소득세 계산")
    st.info("📌 **매수/매도 시점의 규제지역 여부**를 자동으로 판독하여 거주요건 및 중과 여부를 체크합니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🏢 1. 거래 금액 및 기간")
        sell_price = st.number_input("**매도 금액 (양도가액, 만원)**", min_value=1000, value=150000, step=1000)
        buy_price = st.number_input("**매수 금액 (취득가액, 만원)**", min_value=1000, value=80000, step=1000)
        expenses = st.number_input("**필요경비 (중개보수, 수리비 등, 만원)**", min_value=0, value=2000, step=100)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### ⏳ 2. 보유 및 거주 기간")
        holding_period = st.number_input("**총 보유 기간 (년)**", min_value=0.0, max_value=50.0, value=3.0, step=0.5)
        residence_period = st.number_input("**총 거주 기간 (년)**", min_value=0.0, max_value=50.0, value=2.0, step=0.5)

    with col2:
        st.markdown("#### 🚨 3. 자동 규제지역 판독기")
        cgt_area = st.selectbox("**📍 양도 물건 지역**", [
            "① 서울 강남/서초/송파/용산", "② 서울 그 외 21개 자치구", "③ 과천/광명/하남/성남(분당·수정)",
            "④ 의왕/용인수지/안양동안/수원(영통/장안/팔달)", "⑤ 화성동탄/구리/세종 등 (과거해제)", "⑥ 전국 전면 비규제 지역"
        ])
        
        with st.expander("❓ 규제지역 번호별 상세 연혁"):
            st.markdown(f"""{DETAIL_STYLE}
            <ul style='margin-top: 0; padding-left: 20px;'>
                <li><b>① 강남3구+용산:</b> 지속 유지</li>
                <li><b>② 서울 21개구:</b> 과거 지정 → '23.1 해제 → '25.10 재지정</li>
                <li><b>③ 과천/광명/성남:</b> 과거 지정 → '23.1 해제 → '25.10 재지정</li>
                <li><b>④ 안양/수원/의왕:</b> 과거 지정 → '22.11 해제 → '25.10 재지정</li>
                <li><b>⑤ 동탄/구리 등:</b> 과거 해제 후 현재까지 비규제 유지</li>
                <li><b>⑥ 전국 비규제:</b> 규제 이력 없어 거주요건 무조건 면제</li>
            </ul>
            </div>""", unsafe_allow_html=True)
        
        st.markdown("**[매수 시점 규제 확인]**")
        buy_ym = st.text_input("**매수년월 (YYYYMM)**", value="202105")
        is_reg_buy, msg_buy = check_regulation_status(cgt_area, buy_ym, mode="buy")
        
        is_pinset_buy = st.checkbox("💡 단, 매수 당시 우리 동네는 '핀셋 규제'로 지정 제외되었습니다.")
        
        with st.expander("❓ 핀셋 규제란?"):
            st.markdown(f"{DETAIL_STYLE}구 단위 규제 시 억울하게 묶이는 것을 막기 위해 명시적으로 제외해 준 외곽 동네(예: 파주 문산읍)입니다. 체크 시 비규제로 취급됩니다.</div>", unsafe_allow_html=True)
        
        if is_pinset_buy:
            is_reg_buy = False
            msg_buy = "✅ 핀셋 규제 제외 지역 취득 → 거주요건 면제"
            
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
            msg_sell = "✅ 핀셋 규제 제외 지역 양도 → 다주택자 양도세 중과 배제"
            
        if is_reg_sell:
            st.error(msg_sell)
        else:
            st.success(msg_sell)

        st.markdown("<br>", unsafe_allow_html=True)
        homes_count_sell = st.selectbox("**매도 시점 총 주택 수**", ["1주택", "일시적 2주택", "2주택", "3주택 이상"])
        
        with st.expander("❓ 내 주택수 정확히 세는 법 (양도세 기준)"):
            st.markdown(f"""{DETAIL_STYLE}
            <ul style='margin-top: 0; padding-left: 20px;'>
                <li><b>1세대:</b> 실제 생계를 같이 하는 가족 합산</li>
                <li><b>분양권/입주권:</b> 분양권은 '21. 1. 1. 이후 취득분부터 포함 (입주권은 상시 포함)</li>
                <li><b>오피스텔:</b> 실제 주거용 사용 시 취득일 무관 모두 포함</li>
                <li><b>중과 제외:</b> 수도권/광역시 외 지방 공시가 3억 이하 등 제외</li>
            </ul>
            </div>""", unsafe_allow_html=True)
            
        is_joint_sell = st.checkbox("🤝 **부부 공동명의 (지분 50:50)**", key="cgt_joint")
        is_suspension = st.checkbox("💡 **다주택자 양도세 중과 유예 적용** (2026. 5. 9. 양도분까지)")

    st.markdown("---")
    if st.button("양도세 정밀 계산하기 🚀", use_container_width=True, key="btn_cgt", type="primary"):
        gain, tax_gain, deduct_amt, tax_base, rate, total_tax, status_msg, deduct_rate = calculate_capital_gains_tax(
            sell_price, buy_price, expenses, holding_period, residence_period, homes_count_sell, is_reg_buy, is_reg_sell, is_suspension, is_joint_sell
        )
        st.markdown("---")
        st.markdown(f"#### 📊 양도소득세 산출 결과")
        st.info(f"💡 **적용 상태:** {status_msg}")
        
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"<span style='font-size: 14px; color: #555;'>① 총 양도차익</span><br><span style='font-size: 18px; font-weight: bold;'>{int(gain):,} 원</span>", unsafe_allow_html=True)
        with c2: st.markdown(f"<span style='font-size: 14px; color: #555;'>② 과세대상 차익</span><br><span style='font-size: 18px; font-weight: bold;'>{int(tax_gain):,} 원</span>", unsafe_allow_html=True)
        with c3: st.markdown(f"<span style='font-size: 14px; color: #555;'>③ 장특공제({deduct_rate * 100:.0f}%)</span><br><span style='font-size: 18px; font-weight: bold; color: #2563eb;'>- {int(deduct_amt):,} 원</span>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        c4, c5 = st.columns(2)
        tb_label = "④ 과표 (1인 기준)" if is_joint_sell else "④ 과세표준"
        with c4: st.markdown(f"<span style='font-size: 14px; color: #555;'>{tb_label}</span><br><span style='font-size: 18px; font-weight: bold;'>{int(tax_base):,} 원</span>", unsafe_allow_html=True)
        with c5: st.markdown(f"<span style='font-size: 14px; color: #555;'>⑤ 적용 최고세율</span><br><span style='font-size: 18px; font-weight: bold; color: #dc2626;'>{rate * 100:.1f}%</span>", unsafe_allow_html=True)
        
        res_label = "부부 합산 양도세 총액" if is_joint_sell else "납부 예상 양도세 총액"
        st.markdown(f"""
        <div style="background-color: #fee2e2; padding: 20px; border-radius: 15px; border-left: 10px solid #ef4444; margin-top: 15px;">
            <p style="margin: 0; color: #991b1b; font-weight: bold;">💸 {res_label} (지방세 포함)</p>
            <h2 style="margin: 0; color: #dc2626; font-size: 2.5rem;">{int(total_tax):,} 원</h2>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📝 1세대 1주택 비과세 핵심 요건"):
        st.markdown(f"""{DETAIL_STYLE}
        <ul style='margin-top: 0; padding-left: 20px;'>
            <li><b>보유/거주 요건:</b> 2년 이상 보유 필수 (취득 당시 조정대상지역이면 2년 거주 필수)</li>
            <li><b>고가 주택 기준:</b> 양도가액 12억 원 이하 전액 비과세, 초과분은 비율 과세</li>
            <li><b>장기보유특별공제:</b> 거주/보유 각각 연 4%씩, 최대 80% 공제 (10년 이상)</li>
        </ul>
        </div>""", unsafe_allow_html=True)
        
    with st.expander("🔍 일시적 2주택 [1·2·3 법칙] 요약"):
        st.markdown(f"""{DETAIL_STYLE}
        <ul style='margin-top: 0; padding-left: 20px;'>
            <li><b>[1] 1년 텀:</b> 기존 주택 취득 후 1년 이상 지나서 신규 주택 취득</li>
            <li><b>[2] 2년 보유:</b> 기존 주택 2년 보유 (조정 취득 시 2년 거주)</li>
            <li><b>[3] 3년 내 매도:</b> 신규 주택 취득일로부터 3년 이내 기존 주택 매도</li>
        </ul>
        </div>""", unsafe_allow_html=True)

# ==========================================
# 7. 화면 구성 (앱 4: 자금조달 및 대출 V2.1)
# ==========================================
def run_loan_simulator_app():
    st.subheader("🏦 대출 및 자금조달")
    
    st.error("🚨 **[긴급 공지] 2026. 4. 1. 가계대출 관리방안 반영:** 다주택자의 수도권 및 규제지역 내 주택담보대출 만기 연장이 4월 17일부터 원칙적으로 금지됩니다.")
    
    loan_type = st.radio("어떤 대출을 알아보시나요?", ["🏠 주택담보대출 (매매용)", "🔑 전세자금대출 (임차용)"], horizontal=True)
    st.markdown("---")
    
    if loan_type == "🏠 주택담보대출 (매매용)":
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🏢 1. 매수 자금 및 조건")
            prop_price = st.number_input("**매수할 주택 가격 (실제 매매가, 만원)**", min_value=1000, value=80000, step=1000)
            
            with st.expander("💡 대출 한도는 '매매가'가 아닌 'KB시세' 기준입니다."):
                st.markdown(f"{DETAIL_STYLE}대출 한도(LTV) 산정 시 실제 매매가와 <b>KB시세 중 낮은 금액</b>을 기준으로 합니다.</div>", unsafe_allow_html=True)
                
            use_kb_price = st.checkbox("☑️ KB시세 직접 입력 (대출 한도 산정 기준)")
            ltv_base_price = prop_price
            
            if use_kb_price:
                kb_p = st.number_input("**KB시세 (일반평균가, 만원)**", min_value=1000, value=prop_price, step=1000)
                ltv_base_price = min(prop_price, kb_p)
                st.caption(f"🎯 은행 대출 한도 산정 기준 금액: **{ltv_base_price/10000:.1f}억 원**")
                
            cash_on_hand = st.number_input("**현재 보유 중인 매수 현금 (만원)**", min_value=0, value=30000, step=1000)
            required_loan = max(0, prop_price - cash_on_hand)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 👨‍👩‍👧‍👦 2. 정책자금대출 우대 조건 확인")
            
            is_married = st.checkbox("💍 신혼부부 (혼인 7년 이내 또는 3개월 내 결혼 예정)")
            st.caption("💡 [디딤돌] 소득 8.5천만 이하 / 금리 2.45~3.55% / 한도 4억")
            
            has_newborn = st.checkbox("👶 2년 내 출산 (또는 입양 예정) 가구")
            st.caption("💡 [신생아] 소득 2억 이하 / 금리 1.6~3.3% / 한도 5억")
            
            st.markdown("<br>", unsafe_allow_html=True)
            is_capital_area = st.checkbox("🏙️ 해당 주택이 **수도권(서울/경기/인천)**에 위치해 있습니다.", value=True)
            is_regulated_loan = st.checkbox("🚨 해당 주택이 **규제지역(조정대상지역 등)**에 위치해 있습니다.")
            
        with col2:
            st.markdown("#### 👤 3. 주택 수 및 소득")
            current_homes = st.selectbox("**현재 보유 중인 주택 수 (이번 매수 건 제외)**", ["무주택", "1주택", "2주택 이상"])
            
            is_first_time = False
            if current_homes in ["무주택", "1주택"]:
                if current_homes == "1주택":
                    st.warning("⚠️ 1주택자는 기존 주택을 정해진 기한 내에 파는 **'처분 조건부'**로 대출 진행 시 무주택자와 동일한 LTV 한도가 적용됩니다.")
                    st.warning("⚠️ **[4.1 대책 주의]** 처분 없이 추가 매수 시 수도권/규제지역 주담대 만기연장 금지됩니다.")
                is_first_time = st.checkbox("🌱 **생애최초 주택구입자**입니다. (LTV 완화)")
            else:
                st.error("🚨 2주택 이상 다주택자는 규제지역 내 신규 주택 취득 목적의 주담대가 전면 금지됩니다.")
                
            annual_income = st.number_input("**연 소득 (세전, 만원)**", min_value=1000, value=7000, step=500)
            
            with st.expander("📊 **[정밀 DSR] 기존 대출 상세 입력**", expanded=False):
                st.caption("은행 심사 기준이 자동 적용됩니다.")
                debt_credit = st.number_input("일반 신용대출 총 잔액 (만원)", value=0, step=500)
                debt_minus = st.number_input("마이너스 통장 한도 (만원)", value=0, step=500)
                debt_etc_monthly = st.number_input("기타 할부(자동차 등) 월 납입액 (만원)", value=0, step=10)
                is_move_loan = st.checkbox("💡 이주비/중도금 대출입니다. (DSR 제외)")
            
            interest_rate = st.number_input("**예상 실제 대출 금리 (연 %)**", min_value=1.0, max_value=15.0, value=4.2, step=0.1)
            loan_years = st.selectbox("**대출 상환 기간 (년)**", [10, 20, 30, 40, 50], index=2)

        st.markdown("---")
        if st.button("PRO 정밀 분석 결과 보기 🚀", use_container_width=True, type="primary"):
            if required_loan == 0:
                st.success("보유 현금이 충분하여 대출이 필요하지 않습니다! 🎉")
            elif current_homes == "2주택 이상" and is_regulated_loan:
                st.error("🚨 **대출 불가!** 다주택자는 규제지역 내에서 주택 취득 목적의 주담대를 받을 수 없습니다. (LTV 0%)")
            else:
                policy_matches = check_policy_loan_eligibility(ltv_base_price, annual_income, is_married, has_newborn, is_capital_area, is_first_time)
                if policy_matches:
                    st.success("✨ **정책자금대출 대상자로 판별되었습니다! 아래 저금리 상품을 우선 검토하세요.**")
                    p_cols = st.columns(len(policy_matches))
                    for idx, p in enumerate(policy_matches):
                        p_cols[idx].info(f"**{p['name']}**\n\n예상 금리: {p['rate']}\n{p['limit']}\n\n*{p['desc']}*")
                
                max_loan_by_ltv, applied_ratio, applied_cap = get_max_mortgage_ltv(is_regulated_loan, is_capital_area, is_first_time, ltv_base_price, current_homes)
                
                annual_repay_existing = 0
                if not is_move_loan:
                    annual_repay_existing += (debt_credit + debt_minus) / 5 
                    annual_repay_existing += (debt_credit + debt_minus) * 0.05 
                    annual_repay_existing += (debt_etc_monthly * 12)
                
                stress_rate = 3.0 if (is_regulated_loan or is_capital_area) else 1.2
                stress_monthly_pmt_won, _ = calculate_loan_payment(required_loan, interest_rate + stress_rate, loan_years, is_interest_only=False)
                actual_dsr = ((stress_monthly_pmt_won/10000 * 12) + annual_repay_existing) / annual_income
                dsr_limit = 0.40
                
                st.markdown("#### 📊 1. 매매대출 일반 심사 결과")
                cap_text = f"{int(applied_cap):,}만 원" if applied_cap != float('inf') else "제한 없음"
                st.info(f"💡 **적용된 LTV 기준:** 집값의 **{applied_ratio*100:.0f}%** (최대한도 캡: **{cap_text}**)")
                
                c1, c2 = st.columns(2)
                if required_loan > max_loan_by_ltv:
                    c1.error(f"🚨 **LTV 한도 초과!**\n\n최대 가능 대출액: **{int(max_loan_by_ltv):,}만 원**")
                else:
                    c1.success(f"✅ **LTV 통과**\n\n최대 한도 {int(max_loan_by_ltv):,}만 원 이내로 안전권입니다.")
                    
                if actual_dsr > dsr_limit:
                    c2.error(f"🚨 **스트레스 DSR 40% 한도 초과!**\n\n예상 DSR: **{actual_dsr*100:.1f}%** (가산금리 +{stress_rate}%p 적용)")
                else:
                    c2.success(f"✅ **스트레스 DSR 통과 (안정권)**\n\n예상 DSR: **{actual_dsr*100:.1f}%** (가산금리 +{stress_rate}%p 적용)")

                st.markdown("---")
                st.markdown("#### 💸 2. 자금조달 및 실제 월 상환액 브리핑")
                monthly_pmt_won, total_interest_won = calculate_loan_payment(required_loan, interest_rate, loan_years, is_interest_only=False)
                
                r1, r2, r3 = st.columns(3)
                with r1: st.markdown(f"<span style='font-size: 14px; color: #555;'>필요 초기 자금</span><br><span style='font-size: 18px; font-weight: bold;'>{int(cash_on_hand):,} 만원</span>", unsafe_allow_html=True)
                with r2: st.markdown(f"<span style='font-size: 14px; color: #555;'>신규 대출 원금</span><br><span style='font-size: 18px; font-weight: bold;'>{int(required_loan):,} 만원</span>", unsafe_allow_html=True)
                with r3: st.markdown(f"<span style='font-size: 14px; color: #555;'>총 이자액 ({loan_years}년)</span><br><span style='font-size: 18px; font-weight: bold;'>{int(total_interest_won/10000):,} 만원</span>", unsafe_allow_html=True)
                
                total_monthly_out = monthly_pmt_won + (debt_etc_monthly * 10000)
                st.markdown(f"""
                <div style="background-color: #e0f2fe; padding: 20px; border-radius: 15px; border-left: 10px solid #0ea5e9; margin-top: 15px;">
                    <p style="margin: 0; color: #075985; font-size: 14px; font-weight: bold;">🏦 매월 통장에서 빠져나가는 총 금액 (신규 주담대 + 기존 할부 등)</p>
                    <h2 style="margin: 0; color: #0284c7; font-size: 2.2rem;">약 {int(total_monthly_out):,} 원</h2>
                </div>
                """, unsafe_allow_html=True)

    elif loan_type == "🔑 전세자금대출 (임차용)":
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🏢 1. 전세 조건")
            is_capital_jeonse = st.checkbox("🏙️ 구하려는 전셋집이 **수도권(서울/경기/인천)**에 위치해 있습니다.", value=True)
            jeonse_deposit = st.number_input("**들어가려는 집의 전세 보증금 (만원)**", min_value=1000, value=30000, step=1000)
            jeonse_cash = st.number_input("**현재 보유 중인 전세 현금 (만원)**", min_value=0, value=10000, step=1000)
            required_jeonse_loan = max(0, jeonse_deposit - jeonse_cash)
            st.caption(f"💸 실제 필요 전세 대출 금액: **{required_jeonse_loan/10000:.1f}억 원**")

        with col2:
            st.markdown("#### 👤 2. 고객 주택 보유 여부")
            jeonse_homes = st.selectbox("**현재 명의로 보유 중인 주택 수**", ["무주택", "1주택", "2주택 이상"])
            
            is_1home_banned = False
            is_regulated_1home = False
            
            if jeonse_homes == "2주택 이상":
                st.error("🚨 다주택자(2주택 이상)는 공적 보증 전세대출이 전면 금지됩니다.")
            elif jeonse_homes == "1주택":
                is_regulated_1home = st.checkbox("🚨 보유하신 기존 주택이 **규제지역(서울 등)**에 있습니까?")
                if is_regulated_1home:
                    st.warning("⚠️ **[최신 규제]** 1주택자 규제지역 보유 시 전세대출 이자가 DSR 산정에 엄격히 포함되어 한도가 대폭 축소될 수 있습니다.")
                    
                is_speculative = st.checkbox("🚨 보유 주택이 **투기/투기과열지구**에 위치하며 **시세 3억**을 초과합니까?")
                if is_speculative:
                    is_1home_banned = True
                    st.error("🚨 투기과열지구 내 시세 3억 초과 주택 보유자는 전세 대출이 전면 금지됩니다.")
            elif jeonse_homes == "무주택":
                st.success("✅ 무주택자는 보증금 조건만 맞으면 가장 유리하게 대출이 가능합니다.")
                
            jeonse_rate = st.number_input("**예상 전세 대출 금리 (연 %)**", min_value=1.0, value=4.5, step=0.1)

        st.markdown("---")
        if st.button("맞춤형 전세대출 컨설팅 시작 🚀", use_container_width=True, type="primary"):
            if required_jeonse_loan == 0:
                st.success("보유 현금이 충분하여 전세 대출이 필요하지 않습니다! 🎉")
            elif jeonse_homes == "2주택 이상" or (jeonse_homes == "1주택" and is_1home_banned):
                st.error("🚨 **대출 불가!** 최신 규제로 인해 전세자금 보증이 거절됩니다.")
            else:
                st.markdown("#### 📊 맞춤형 전세대출 추천 결과 (1~3순위)")
                recommended_loans = []
                
                # 1. 버팀목 (정부기금)
                btm_deposit_limit = 30000 if is_capital_jeonse else 20000
                btm_max_loan = 12000 if is_capital_jeonse else 8000
                if jeonse_homes == "무주택" and jeonse_deposit <= btm_deposit_limit:
                    actual_limit = min(btm_max_loan, jeonse_deposit * 0.8)
                    if required_jeonse_loan <= actual_limit:
                        recommended_loans.append({
                            "rank": "🥇 1순위 추천",
                            "name": "버팀목 전세자금대출 (정부기금)",
                            "limit": f"최대 {int(actual_limit):,}만 원",
                            "condition": f"무주택자 & 보증금 {'수도권 3억' if is_capital_jeonse else '지방 2억'} 원 이하",
                            "advantage": "시중 은행 대비 압도적으로 낮은 최저 금리를 제공하여 이자 부담이 가장 적습니다!"
                        })
                
                # 2. HUG / HF (일반 보증)
                hug_deposit_limit = 70000 if is_capital_jeonse else 50000
                hug_max_loan = 40000
                hf_max_loan = 22200
                
                if jeonse_deposit <= hug_deposit_limit:
                    actual_hug_limit = min(hug_max_loan, jeonse_deposit * 0.8)
                    actual_hf_limit = min(hf_max_loan, jeonse_deposit * 0.8)
                    if required_jeonse_loan <= actual_hug_limit:
                        recommended_loans.append({
                            "rank": "🥈 2순위 추천",
                            "name": "HUG 안심전세대출 / HF 전세대출",
                            "limit": f"HUG 최대 {int(actual_hug_limit):,}만 원 / HF 최대 {int(actual_hf_limit):,}만 원",
                            "condition": f"보증금 {'수도권 7억' if is_capital_jeonse else '지방 5억'} 원 이하 (1주택자는 한도 제한 가능)",
                            "advantage": "HUG 상품의 경우, 대출과 동시에 전세보증금 반환보증보험이 100% 자동 가입되어 소중한 보증금을 가장 안전하게 지킬 수 있습니다."
                        })
                
                # 3. SGI 서울보증보험 (고가 전세)
                sgi_max_loan = 50000 if jeonse_homes == "무주택" else 30000
                actual_sgi_limit = min(sgi_max_loan, jeonse_deposit * 0.8)
                
                if jeonse_deposit > hug_deposit_limit or required_jeonse_loan > hug_max_loan:
                    if required_jeonse_loan <= actual_sgi_limit:
                         recommended_loans.append({
                            "rank": "🥉 3순위 추천 (고가 전세용)",
                            "name": "SGI 서울보증보험 전세대출",
                            "limit": f"최대 {int(actual_sgi_limit):,}만 원",
                            "condition": "보증금 상한선 제한 없음 (수도권 7억 초과 고가 아파트도 가능)",
                            "advantage": "정부나 HUG 보증이 불가능한 고가 주택이나, 대출 한도가 더 많이 필요한 경우 활용할 수 있는 가장 강력한 민간 보증 상품입니다."
                        })
                elif len(recommended_loans) == 0:
                     recommended_loans.append({
                            "rank": "🥉 3순위 추천 (대체용)",
                            "name": "SGI 서울보증보험 전세대출",
                            "limit": f"최대 {int(actual_sgi_limit):,}만 원",
                            "condition": "보증금 상한선 제한 없음",
                            "advantage": "다른 공적 보증 한도가 부족할 때 안전하게 활용 가능한 상품입니다."
                        })

                if not recommended_loans:
                    st.error(f"🚨 현재 입력하신 금액 (보증금 {jeonse_deposit:,}만 원, 필요 대출 {required_jeonse_loan:,}만 원) 전체를 방어할 수 있는 보증 상품 한도가 부족합니다. 현금을 더 확보해야 합니다.")
                else:
                    for loan in recommended_loans:
                        st.success(f"### {loan['rank']} | {loan['name']}\n"
                                   f"- 💰 **대출 한도:** {loan['limit']}\n"
                                   f"- 📝 **필수 조건:** {loan['condition']}\n"
                                   f"- ⭐ **상품 장점:** {loan['advantage']}")

                monthly_jeonse_interest, _ = calculate_loan_payment(required_jeonse_loan, jeonse_rate, years=2, is_interest_only=True)
                
                st.markdown("---")
                st.markdown("#### 💸 2. 매월 납부 예상 이자 (만기일시상환)")
                st.markdown(f"""
                <div style="background-color: #fef3c7; padding: 20px; border-radius: 15px; border-left: 10px solid #f59e0b; margin-top: 15px;">
                    <p style="margin: 0; color: #92400e; font-size: 14px; font-weight: bold;">🔑 매월 은행에 납부하실 전세대출 이자액 (원금 제외)</p>
                    <h2 style="margin: 0; color: #d97706; font-size: 2.5rem;">약 {int(monthly_jeonse_interest):,} 원</h2>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🔍 정책자금대출(신생아/디딤돌) 핵심 요약", expanded=False):
        st.markdown(f"""{DETAIL_STYLE}
        <b>1. 👶 신생아 특례대출</b>
        <ul style='margin-top: 0; padding-left: 20px;'>
            <li><b>대상/소득:</b> 2년 내 출산/입양 가구, 부부합산 2.0억 원 이하</li>
            <li><b>주택/한도:</b> 9억 이하 주택, <b>최대 5억 원</b></li>
            <li><b>혜택:</b> 수도권 방공제(최우선변제금) 차감 없음</li>
        </ul>
        <hr style='margin: 10px 0;'>
        <b>2. 🏠 디딤돌대출 (일반/신혼)</b>
        <ul style='margin-top: 0; padding-left: 20px;'>
            <li><b>소득:</b> 일반 6천만 / 신혼 8.5천만 이하</li>
            <li><b>주택/한도:</b> 5억 이하(신혼 6억), <b>최대 2.5억</b>(신혼 4억)</li>
            <li><b>주의:</b> 수도권 아파트 매수 시 방공제 약 4,800만 원 차감</li>
        </ul>
        <hr style='margin: 10px 0;'>
        <b>3. 공통 요건:</b> 가구당 순자산 4.69억 원 이하
        </div>""", unsafe_allow_html=True)

    # 🔥 전세대출 3종 요약본 추가
    with st.expander("🔍 주요 전세자금대출(버팀목/HUG/SGI) 핵심 요약", expanded=False):
        st.markdown(f"""{DETAIL_STYLE}
        <b>💡 공통 한도 유의사항:</b> 대부분의 전세대출은 <b>전세보증금의 최대 80%</b>까지만 대출이 가능합니다. (단, 신혼부부나 청년 등 일부 상품은 조건에 따라 90%까지 가능)
        <hr style='margin: 10px 0;'>
        <b>1. 🏛️ 버팀목 전세자금대출 (정부기금)</b>
        <ul style='margin-top: 0; padding-left: 20px;'>
            <li><b>조건/한도:</b> 무주택자 / 보증금 상한(수도권 3억, 지방 2억 이하) / 최대 한도 1.2억(지방 8천만)</li>
            <li><b>장점:</b> 시중 은행 전세대출 대비 금리가 가장 저렴하여 이자 부담이 확연히 적습니다. (1~2%대)</li>
            <li><b>단점:</b> 보증금 상한선과 대출 한도가 낮아 고가 전세 아파트에는 활용이 어렵습니다.</li>
        </ul>
        <hr style='margin: 10px 0;'>
        <b>2. 🛡️ HUG 안심전세대출 / HF 일반전세대출</b>
        <ul style='margin-top: 0; padding-left: 20px;'>
            <li><b>조건/한도:</b> 보증금 상한(수도권 7억, 지방 5억 이하) / [HUG] 최대 4억 원 / [HF] 최대 2.22억 원</li>
            <li><b>장점:</b> [HUG] 대출과 동시에 전세보증금 반환보증보험이 무조건 100% 자동 가입되어 깡통전세 예방에 탁월합니다.</li>
            <li><b>단점:</b> 1주택자의 경우 한도가 2억 원으로 제한되거나, 보유 주택 요건(규제지역 등)에 따라 거절될 수 있습니다.</li>
        </ul>
        <hr style='margin: 10px 0;'>
        <b>3. 🏢 SGI 서울보증보험 전세대출</b>
        <ul style='margin-top: 0; padding-left: 20px;'>
            <li><b>조건/한도:</b> 보증금 상한 <b>제한 없음</b> / 최대 5억 원 (1주택자는 3억 원)</li>
            <li><b>장점:</b> 보증금 제한이 없어 수도권 7억 원 초과 고가 아파트 전세에 폭넓게 활용 가능합니다.</li>
            <li><b>단점:</b> 타 기관 상품 대비 보증료율과 은행 적용 금리가 상대적으로 높은 편입니다.</li>
        </ul>
        </div>""", unsafe_allow_html=True)

# ==========================================
# 8. 메인 네비게이션 및 사이드바 (main 함수)
# ==========================================
def main():
    st.markdown("""
    <style>
        .block-container { padding-top: 3rem !important; }
        div.stButton > button[kind="primary"] {
            background-color: #FF4B4B !important; color: white !important; font-weight: bold !important;
            font-size: 18px !important; border-radius: 10px !important; padding: 0.5rem 1rem !important;
        }
        div[data-baseweb="tab-list"] { gap: 5px; }
        button[data-baseweb="tab"] {
            font-size: 16px !important; font-weight: bold !important; background-color: #f0f2f6 !important; 
            border-radius: 12px 12px 0px 0px !important; padding: 10px 15px !important; color: #555555 !important;
        }
        button[aria-selected="true"] { background-color: #FF4B4B !important; color: white !important; }
        
        .news-box { padding: 12px; border-radius: 8px; margin-bottom: 12px; font-size: 13px; line-height: 1.4; }
        .news-date { font-weight: bold; font-size: 12px; margin-bottom: 4px; }
        .bg-red { background-color: #fee2e2; border-left: 5px solid #ef4444; color: #991b1b; }
        .bg-yellow { background-color: #fef9c3; border-left: 5px solid #eab308; color: #854d0e; }
        .bg-blue { background-color: #e0f2fe; border-left: 5px solid #0ea5e9; color: #075985; }
        .bg-gray { background-color: #f3f4f6; border-left: 5px solid #6b7280; color: #374151; }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.title("⚙️ 프롭테크 메뉴")
        total, daily = update_and_get_visitor_count()
        c1, c2 = st.columns(2)
        c1.metric("오늘 방문", f"{daily} 명")
        c2.metric("총 방문", f"{total} 명")
        
        st.markdown("---")
        st.markdown("### 📢 부동산/대출 트렌드")
        st.markdown("""
        <div class="news-box bg-red">
            <div class="news-date">🚨 [2026.04.01] 대출 규제 속보</div>
            다주택자 수도권 및 규제지역 내 주택담보대출 <b>만기 연장 원칙적 금지</b> 발표 (4/17 시행).
        </div>
        <div class="news-box bg-yellow">
            <div class="news-date">⚠️ [2026.03.15] 스트레스 DSR 3단계</div>
            수도권/규제지역 대출 심사 시 <b>가산금리 +3.0%p</b> 본격 적용. 체감 한도 대폭 축소.
        </div>
        <div class="news-box bg-blue">
            <div class="news-date">📉 [2026.02] 은행권 금리 동향</div>
            주요 시중은행 주담대 평균 금리 <b>4.2%대</b> 진입. (변동형 기준)
        </div>
        <div class="news-box bg-gray">
            <div class="news-date">📌 [2025 최신] 디딤돌대출 규제</div>
            수도권 아파트 매수 시 최우선변제금(방공제) <b>약 4,800만원 대출 한도 차감</b> 의무화.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏢 집스탯 (ZipStat) PRO V2.1</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555555;'>실거래가 분석부터 최신 규제 반영 자금조달까지 원클릭으로!</p>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 실거래가 분석", "💰 세금 계산", "📈 양도세 계산", "🏦 자금조달/대출"])
    
    with tab1: run_real_estate_app() 
    with tab2: run_tax_app()
    with tab3: run_capital_gains_tax_app()
    with tab4: run_loan_simulator_app()
        
    st.markdown("---")
    st.caption("💡 본 대시보드는 실무 참고용이며, 정확한 세금 및 대출 한도는 전문가 및 금융기관과 상담하시기 바랍니다.")

if __name__ == "__main__":
    main()
    
