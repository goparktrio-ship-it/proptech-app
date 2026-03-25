import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import datetime # 날짜와 시간을 다루는 파이썬 기본 도구 추가!

st.set_page_config(page_title="프롭테크 실거래가 분석기", page_icon="🏠", layout="wide")

st.title("🏠 전월세 실거래")
st.write("버튼 하나로 원하는 동네와 날짜의 시장 흐름을 한눈에 파악하세요! 😎")

# 🎯 [중요] API 키 입력!
API_KEY = '6185985620d6525b8af9628d96468b183acefb64c58135f6cae9fc04f844fe6a'

# 1. 🗺️ 3단계 지역 데이터 사전 (송파구 추가 완료!)
region_data = {
    "경기도": {
        "용인시 수지구": {
            "code": "41465", 
            "dongs": ["전체보기", "고기동", "동천동", "상현동", "성복동", "신봉동", "죽전동", "풍덕천동"]
        },
        "성남시 분당구": {
            "code": "41135",
            "dongs": ["전체보기", "구미동", "궁내동", "금곡동", "대장동", "백현동", "분당동", "삼평동", "서현동", "수내동", "야탑동", "운중동", "율동", "이매동", "정자동", "판교동", "하산운동"]
        }
    },
    "서울특별시": {
        "송파구": {
            "code": "11710",
            "dongs": ["전체보기", "가락동", "거여동", "마천동", "문정동", "방이동", "삼전동", "석촌동", "송파동", "신천동", "오금동", "잠실동", "장지동", "풍납동"]
        },
        "강남구": {
            "code": "11680",
            "dongs": ["전체보기", "개포동", "논현동", "대치동", "도곡동", "삼성동", "세곡동", "수서동", "신사동", "압구정동", "역삼동", "율현동", "일원동", "자곡동", "청담동"]
        }
    }
}

# 2. 🎛️ 화면 구성: 지역 선택 (3칸)
st.subheader("📍 지역 선택")
col1, col2, col3 = st.columns(3)

with col1:
    selected_sido = st.selectbox("🌍 시/도를 선택하세요", list(region_data.keys()))

with col2:
    selected_sigungu = st.selectbox("🏠 시/군/구를 선택하세요", list(region_data[selected_sido].keys()))

with col3:
    dong_list = region_data[selected_sido][selected_sigungu]["dongs"]
    selected_dong = st.selectbox("🏘️ 상세 '동'을 선택하세요", dong_list)

lawd_cd = region_data[selected_sido][selected_sigungu]["code"]

st.markdown("---") 

# 3. 🗓️ 화면 구성: 날짜 선택 (2칸)
st.subheader("🗓️ 조회 연월 선택")
now = datetime.datetime.now()
current_year = now.year

date_col1, date_col2 = st.columns(2)

with date_col1:
    # 올해부터 2015년까지 역순으로 선택 가능하게!
    selected_year = st.selectbox("연도", range(current_year, 2014, -1))

with date_col2:
    # 1월부터 12월까지
    selected_month = st.selectbox("월", range(1, 13), index=now.month - 1)

# API에 보낼 YYYYMM 형태로 합치기 (예: 2026년 2월 -> "202602")
# :02d는 한 자리 숫자(예: 2)를 두 자리(예: 02)로 맞춰주는 마법이에요!
deal_ymd = f"{selected_year}{selected_month:02d}"

st.markdown("---")

# 4. 🚀 분석 시작 버튼 (버튼 이름에 선택한 연월과 동네가 다 나오게 업데이트!)
button_text = f"{selected_year}년 {selected_month}월 {selected_sigungu} {selected_dong} 분석 시작! 🚀"

if st.button(button_text, use_container_width=True):
    
    st.info("데이터를 열심히 수집하고 분석하는 중입니다... 잠시만요! 📡")
    
    url = 'http://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent'
    params = {
        'serviceKey': API_KEY,
        'LAWD_CD': lawd_cd,
        'DEAL_YMD': deal_ymd # 🔥 이제 고정된 날짜가 아니라 우리가 선택한 날짜가 들어갑니다!
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        root = ET.fromstring(response.text)
        items = root.findall('.//item')
        
        if len(items) > 0:
            data_list = []
            for item in items:
                dong = item.find('umdNm').text if item.find('umdNm') is not None else ''
                apt_name = item.find('aptNm').text if item.find('aptNm') is not None else '이름없음'
                deposit = item.find('deposit').text.strip() if item.find('deposit') is not None else '0'
                monthly = item.find('monthlyRent').text.strip() if item.find('monthlyRent') is not None else '0'
                floor = item.find('floor').text if item.find('floor') is not None else ''
                area_m2 = item.find('excluUseAr').text if item.find('excluUseAr') is not None else '0'
                
                data_list.append({
                    '법정동': dong.strip(),
                    '아파트명': apt_name,
                    '전용면적(㎡)': float(area_m2),
                    '보증금(만원)': deposit,
                    '월세(만원)': monthly,
                    '층수': floor
                })
                
            df = pd.DataFrame(data_list)
            df['평수(평)'] = round(df['전용면적(㎡)'] / 3.3058, 1)
            
            if selected_dong != "전체보기":
                df = df[df['법정동'] == selected_dong]
            
            if len(df) > 0:
                st.success("분석 완료! 결과를 확인해 보세요. 🎉")
                st.subheader(f"📌 {selected_year}년 {selected_month}월 {selected_sigungu} {selected_dong} 실거래가 내역 (총 {len(df)}건)")
                st.dataframe(df, use_container_width=True)
            else:
                st.warning(f"{selected_year}년 {selected_month}월에는 {selected_dong}에 신고된 거래가 없네요! 텅~ 🍃")
                
        else:
            st.warning(f"{selected_year}년 {selected_month}월 데이터가 아직 국토부에 업데이트되지 않았거나 거래가 없습니다.")
    else:
        st.error(f"🚨 연결 실패! (상태 코드: {response.status_code})")