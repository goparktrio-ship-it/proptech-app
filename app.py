import os
import json
import base64
import pandas as pd
import streamlit as st
from PIL import Image
import concurrent.futures
import plotly.express as px  
import streamlit.components.v1 as components 

# 🚀 [모듈화] 백엔드 엔진에서 변수 및 계산 함수 모두 불러오기
from engine import *

# ==========================================
# 0. 초기 설정 및 자산 로드
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(current_dir, "logo.png")
title_icon_path = os.path.join(current_dir, "uni6_loan.png") 

try:
    img_icon = Image.open(logo_path)
except FileNotFoundError:
    img_icon = "🏢"

# 🚀 핵심 해결 1: initial_sidebar_state를 "collapsed"로 변경하여 처음 접속 시 홈 화면이 바로 보이도록 수정
st.set_page_config(
    page_title="집스탯 PRO V2.1",
    page_icon=img_icon,
    layout="wide",
    initial_sidebar_state="collapsed" 
)

# 🚀 핵심 해결 2: LocalStorage 초기화 및 세션 상태 중앙 통제
try:
    from streamlit_local_storage import LocalStorage
    localS = LocalStorage()
    HAS_LS = True
except ImportError:
    HAS_LS = False

if 'fav_apts' not in st.session_state:
    st.session_state['fav_apts'] = []
if 'ls_loaded' not in st.session_state:
    st.session_state['ls_loaded'] = False

# [추가됨] 로컬 스토리지 저장을 지연 실행하기 위한 예약 플래그
if 'needs_ls_save' not in st.session_state:
    st.session_state['needs_ls_save'] = False

# 앱 실행 시 단 한 번만 브라우저 저장소를 읽어옴 (속도 지연으로 인한 덮어쓰기 충돌 완벽 방지)
if HAS_LS and not st.session_state['ls_loaded']:
    stored_data = localS.getItem("fav_apts")
    if stored_data is not None: 
        if stored_data and stored_data != "null" and stored_data != "":
            try:
                st.session_state['fav_apts'] = json.loads(stored_data) if isinstance(stored_data, str) else stored_data
            except:
                pass
        st.session_state['ls_loaded'] = True

# 🚀 [추가됨] st.rerun() 직후 최상단에서 예약된 로컬 스토리지 저장을 안전하게 수행
if st.session_state['needs_ls_save']:
    if HAS_LS:
        localS.setItem("fav_apts", json.dumps(st.session_state['fav_apts']))
    st.session_state['needs_ls_save'] = False

if "DATA_API_KEY" in st.secrets:
    SERVICE_KEY = st.secrets["DATA_API_KEY"]
else:
    SERVICE_KEY = ""

DETAIL_STYLE = "<div style='font-size: 14px; line-height: 1.6; color: #444;'>"

if '양천구' not in GU_CODES: GU_CODES['양천구'] = '11470'
if '기흥구' not in GU_CODES: GU_CODES['기흥구'] = '41463'
SORTED_GU_LIST = sorted(list(GU_CODES.keys()))

title_icon_html = "🏢"
if os.path.exists(title_icon_path):
    with open(title_icon_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    title_icon_html = f'<img src="data:image/png;base64,{encoded_string}" style="height: 45px; width: auto; vertical-align: middle; margin-right: 8px; margin-bottom: 8px;">'

# ==========================================
# 1. 화면 구성 (앱 0: 홈 화면 - 모바일 순서 개선)
# ==========================================
@st.fragment
def run_home_app():
    st.markdown("<br>", unsafe_allow_html=True)
    
    lottie_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
        <style>
            html, body {
                margin: 0;
                padding: 0;
                background-color: transparent !important;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                overflow: hidden;
            }
        </style>
    </head>
    <body>
        <lottie-player src="https://assets9.lottiefiles.com/packages/lf20_w6dptksf.json" background="transparent" speed="1" style="width: 250px; height: 250px;" loop autoplay></lottie-player>
    </body>
    </html>
    """
    components.html(lottie_html, height=260)

    st.markdown("""
    <div style="text-align: center; padding: 0 0 40px 0;">
        <h2 style="color: #1E3A8A; font-weight: 800; margin-top: 0px; font-size: 28px;">집스탯 PRO에 오신 것을 환영합니다!</h2>
        <p style="color: #4B5563; font-size: 16px; margin-top: 10px; line-height: 1.6;">
            복잡한 부동산 실거래가 분석부터 최신 규제가 반영된 세금, 대출 계산까지.<br>
            상단의 탭을 클릭하여 원클릭 스마트 부동산 솔루션을 지금 바로 경험해 보세요.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<h3 style='text-align: center; margin-bottom: 30px;'>🚀 핵심 기능 가이드</h3>", unsafe_allow_html=True)

    r1_col1, r1_col2 = st.columns(2)
    with r1_col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🔍</div>
            <div class="feature-title">1. 실거래가 및 전세가율 분석</div>
            <div class="feature-desc">과거 1년 치 시세 트렌드와 최고가/최저가, 그리고 소액 투자를 위한 전세가율(실투자금) 상위 아파트를 클릭 한 번으로 뽑아냅니다.</div>
        </div>
        """, unsafe_allow_html=True)
    with r1_col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">💰</div>
            <div class="feature-title">2. 취득세 및 연간 보유세 계산</div>
            <div class="feature-desc">2026년 최신 세법 적용! 다주택자 중과세율, 부부 공동명의 혜택까지 반영하여 취득세와 재산세/종부세를 산출합니다.</div>
        </div>
        """, unsafe_allow_html=True)

    r2_col1, r2_col2 = st.columns(2)
    with r2_col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📈</div>
            <div class="feature-title">3. 양도소득세 정밀 계산</div>
            <div class="feature-desc">매수/매도 시점의 규제지역(핀셋 규제 포함) 여부를 자동 판독하여 비과세 및 다주택자 중과 여부를 정확히 계산합니다.</div>
        </div>
        """, unsafe_allow_html=True)
    with r2_col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🏦</div>
            <div class="feature-title">4. 맞춤형 자금조달 및 대출 컨설팅</div>
            <div class="feature-desc">신생아/디딤돌 정책자금 대상 여부 확인은 물론, 최신 4월 대출 규제를 반영한 스트레스 DSR 최대한도를 알아봅니다.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

# ==========================================
# 2. 화면 구성 (앱 1: 실거래가)
# ==========================================
@st.fragment 
def run_real_estate_app():
    st.subheader("🏠 실거래가/전세가율")
    
    fav_list = st.session_state['fav_apts']
        
    st.markdown("#### 🔍 검색 조건 설정")
    col1, col2 = st.columns(2)
    with col1:
        selected_gu = st.selectbox("**지역구 선택**", SORTED_GU_LIST)
        lawd_cd = GU_CODES[selected_gu]
    with col2:
        deal_ym = st.text_input("**조회 년월 (YYYYMM)**", value="202602")
        
    category = st.radio("**분석 모드 선택**", ["매매 실거래", "전월세 실거래", "전세가율(실투자금) 분석", "🚀 1년 내 최고가 분석"], horizontal=True)
    submit_btn = st.button("데이터 분석 시작 🚀", width="stretch", type="primary")

    if submit_btn:
        if category in ["매매 실거래", "전월세 실거래"]:
            api_cat = "매매" if category == "매매 실거래" else "전월세"
            with st.spinner(f'{selected_gu} {api_cat} 데이터를 가져오는 중...'):
                df, error_msg = fetch_real_estate_data(api_cat, lawd_cd, deal_ym, SERVICE_KEY)
                
                if error_msg:
                    st.toast(f"🚨 {error_msg}", icon="🚨") 
                    st.session_state['info'] = None 
                elif not df.empty:
                    st.session_state['data'] = df
                    st.session_state['info'] = {'gu': selected_gu, 'ym': deal_ym, 'cat': api_cat, 'mode': '단순조회'}
                    st.toast("✅ 데이터 조회를 완료했습니다!", icon="✨") 

        elif category == "전세가율(실투자금) 분석":
            with st.spinner(f'{selected_gu} 데이터 융합 분석 중...'):
                df_trade, err_trade = fetch_real_estate_data("매매", lawd_cd, deal_ym, SERVICE_KEY)
                df_rent, err_rent = fetch_real_estate_data("전월세", lawd_cd, deal_ym, SERVICE_KEY)
                
                if err_trade or err_rent:
                    st.toast("🚨 데이터를 불러오지 못했습니다.", icon="🚨") 
                    st.session_state['info'] = None
                else:
                    st.session_state['data_trade'] = df_trade
                    st.session_state['data_rent'] = df_rent
                    st.session_state['info'] = {'gu': selected_gu, 'ym': deal_ym, 'mode': '전세가율'}
                    st.toast("✅ 전세가율 계산 완료!", icon="📊") 
                    
        elif category == "🚀 1년 내 최고가 분석":
            months_to_fetch = get_last_12_months(deal_ym)
            all_data = []
            my_bar = st.progress(0, text="과거 1년 치 실거래가 데이터를 수집 중입니다. (🚀 병렬 가속 중)")
            
            def fetch_month_data(ym):
                df, _ = fetch_real_estate_data("매매", lawd_cd, ym, SERVICE_KEY)
                if not df.empty:
                    df['조회년월'] = ym
                return df
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
                futures = {executor.submit(fetch_month_data, ym): ym for ym in months_to_fetch}
                completed_count = 0
                for future in concurrent.futures.as_completed(futures):
                    df = future.result()
                    if not df.empty:
                        all_data.append(df)
                    completed_count += 1
                    my_bar.progress(completed_count / 12, text=f"{selected_gu} 데이터 병렬 수집 완료... ({completed_count}/12)")
            
            if all_data:
                df_all = pd.concat(all_data, ignore_index=True)
                st.session_state['data_high'] = df_all
                st.session_state['info'] = {'gu': selected_gu, 'ym': deal_ym, 'mode': '최고가'}
                st.toast("✅ 1년 치 최고가 병렬 판독 완료!", icon="🚀") 
            else:
                st.toast("🚨 데이터를 불러오지 못했습니다.", icon="🚨") 
                st.session_state['info'] = None

    if 'info' in st.session_state and st.session_state['info'] is not None:
        info = st.session_state['info']
        
        if info['mode'] == '단순조회' and 'data' in st.session_state:
            df = st.session_state['data'].copy()
            
            if info['cat'] == "매매":
                target_cols = ['umdNm', 'aptNm', 'dealAmount', 'excluUseAr', 'floor', 'dealDay'] 
                exist_cols = [c for c in target_cols if c in df.columns]
                df = df[exist_cols].rename(columns={'umdNm': '법정동', 'aptNm': '아파트명', 'dealAmount': '매매가(만원)', 'excluUseAr': '면적(㎡)', 'floor': '층', 'dealDay': '일'})
                price_col = '매매가(만원)' 
            else:
                target_cols = ['umdNm', 'aptNm', 'deposit', 'monthlyRent', 'excluUseAr', 'floor', 'dealDay'] 
                exist_cols = [c for c in target_cols if c in df.columns]
                df = df[exist_cols].rename(columns={'umdNm': '법정동', 'aptNm': '아파트명', 'deposit': '보증금(만원)', 'monthlyRent': '월세(만원)', 'excluUseAr': '면적(㎡)', 'floor': '층', 'dealDay': '일'})
                price_col = '보증금(만원)' 

            if '면적(㎡)' in df.columns:
                df['면적(㎡)'] = pd.to_numeric(df['면적(㎡)'], errors='coerce')
            if '층' in df.columns:
                df['층'] = pd.to_numeric(df['층'], errors='coerce')
            for col in ['매매가(만원)', '보증금(만원)', '월세(만원)']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce')

            st.markdown("---")
            st.subheader(f"🏘️ {info['gu']} 상세 단지 필터링")
            
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                dong_list = sorted(df['법정동'].dropna().unique().tolist())
                selected_dong = st.selectbox("**1. '동' 선택**", ["전체보기"] + dong_list)
                if selected_dong != "전체보기":
                    df = df[df['법정동'] == selected_dong]

            with f_col2:
                apt_list = sorted(df['아파트명'].dropna().unique().tolist())
                selected_apt = st.selectbox("**2. '아파트(단지)' 선택**", ["전체보기"] + apt_list)
                if selected_apt != "전체보기":
                    df = df[df['아파트명'] == selected_apt]
            
            if selected_apt != "전체보기" and selected_dong != "전체보기":
                is_fav = any(f['apt'] == selected_apt and f['dong'] == selected_dong for f in fav_list)
                _, btn_col = st.columns([4, 1])
                with btn_col:
                    if is_fav:
                        if st.button("❌ 관심 해제", width="stretch"):
                            new_list = [f for f in fav_list if not (f['apt'] == selected_apt and f['dong'] == selected_dong)]
                            st.session_state['fav_apts'] = new_list
                            st.session_state['needs_ls_save'] = True
                            st.rerun()
                    else:
                        if st.button("⭐ 관심 등록", width="stretch"):
                            if len(fav_list) >= 10:
                                st.error("🚨 단지는 최대 10개까지만 등록 가능합니다!")
                            else:
                                new_list = fav_list + [{'gu': info['gu'], 'dong': selected_dong, 'apt': selected_apt}]
                                st.session_state['fav_apts'] = new_list
                                st.session_state['needs_ls_save'] = True
                                st.toast(f"{selected_apt} 관심 등록 완료!", icon="⭐")
                                st.rerun()

            if price_col in df.columns:
                valid_df = df.dropna(subset=[price_col])
                col1, col2, col3 = st.columns(3)
                col1.metric("해당 단지 거래건수", f"{len(df)} 건")
                if not valid_df.empty:
                    max_row = valid_df.loc[valid_df[price_col].idxmax()]
                    min_row = valid_df.loc[valid_df[price_col].idxmin()]
                    col2.metric(f"최고가 🏆", f"{int(max_row[price_col]):,} 만원")
                    col3.metric(f"최저가 📉", f"{int(min_row[price_col]):,} 만원")

            st.markdown("<br>", unsafe_allow_html=True) 
            display_df = df.drop(columns=['일']) if '일' in df.columns else df
            st.dataframe(display_df, width="stretch", hide_index=True)

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
                    sel_dong_gap = st.selectbox("**'동' 선택**", ["구 전체보기"] + dong_list_gap)
                    if sel_dong_gap != "구 전체보기":
                        merged = merged[merged['법정동'] == sel_dong_gap].reset_index(drop=True)

                    if not merged.empty:
                        top_10_df = merged.head(10)
                        
                        fig2 = px.bar(
                            top_10_df, x='아파트명', y='전세가율(%)',
                            title=f"🔥 전세가율(실투자금) TOP 10 단지", 
                            text='전세가율(%)', 
                            color='전세가율(%)', 
                            color_continuous_scale="Reds", 
                            template="plotly_white"
                        )
                        fig2.update_traces(texttemplate='%{text}%', textposition='outside')
                        fig2.update_layout(
                            height=350, 
                            margin=dict(l=0, r=0, t=40, b=0), 
                            xaxis=dict(title="", tickangle=-45, tickfont=dict(size=10), fixedrange=True), 
                            yaxis=dict(title="", showticklabels=False, fixedrange=True), 
                            yaxis_range=[max(0, top_10_df['전세가율(%)'].min()-10), 100],
                            dragmode=False 
                        ) 
                        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

                        for i in range(min(5, len(merged))):
                            row = merged.iloc[i]
                            st.info(f"### {i+1}위: {row['아파트명']}\n**📍 {row['법정동']} | 📐 {row['전용면적(㎡)']}㎡**\n\n📊 **전세가율: {row['전세가율(%)']}%**\n💰 **예상 실투자금: {row['실투자금(만원)']:,}만 원**")
                        with st.expander("📊 전체 데이터 보기"):
                            st.dataframe(merged, width="stretch", hide_index=True)

        elif info['mode'] == '최고가' and 'data_high' in st.session_state:
            df = st.session_state['data_high'].copy()
            df['num_price'] = pd.to_numeric(df['dealAmount'].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce')
            df['num_area'] = pd.to_numeric(df['excluUseAr'], errors='coerce').round(1)
            df = df.dropna(subset=['num_price', 'num_area'])
            
            st.markdown("---")
            st.markdown(f"#### 🚀 {info['gu']} 1년 시세 트렌드 및 최고가 분석")
            
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                dong_list = sorted(df['umdNm'].unique())
                sel_dong = st.selectbox("**1. 동 선택**", dong_list)
                df = df[df['umdNm'] == sel_dong]
            with f_col2:
                apt_list = sorted(df['aptNm'].unique())
                sel_apt = st.selectbox("**2. 아파트 선택**", apt_list)
                df = df[df['aptNm'] == sel_apt]
            with f_col3:
                area_list = sorted(df['num_area'].unique())
                sel_area = st.selectbox("**3. 면적(㎡) 선택**", area_list)
                df_filtered = df[df['num_area'] == sel_area].sort_values('조회년월')

            if not df_filtered.empty:
                trend_df = df_filtered.groupby('조회년월')['num_price'].mean().reset_index()
                
                fig = px.line(
                    trend_df, x='조회년월', y='num_price', markers=True,
                    title=f"📅 {sel_apt}<br><span style='font-size:14px;'>({sel_area}㎡) 최근 1년 시세 흐름</span>",
                    template="plotly_white",
                    labels={'조회년월': '거래월', 'num_price': '평균 매매가(만원)'} 
                )
                fig.update_traces(
                    line_color="#1E3A8A", line_width=3, marker_size=8,
                    hovertemplate="<b>%{x}</b><br>매매가: %{y:,}만 원<extra></extra>"
                )
                fig.update_layout(
                    height=300, 
                    margin=dict(l=0, r=0, t=50, b=0), 
                    xaxis=dict(title="", tickangle=-45, tickfont=dict(size=10), fixedrange=True), 
                    yaxis=dict(title="", tickfont=dict(size=10), fixedrange=True), 
                    title_font_size=16,
                    dragmode=False 
                )
                # 🚀 핵심 해결 3: 최고가 분석 그래프에도 staticPlot(완전 고정) 속성 부여
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True})
                
                max_val = int(df_filtered['num_price'].max())
                avg_val = int(df_filtered['num_price'].mean())
                c1, c2 = st.columns(2)
                c1.metric("1년 내 최고가 🏆", f"{max_val:,} 만원")
                c2.metric("1년 평균가 📊", f"{avg_val:,} 만원")
            
            with st.expander("📊 상세 거래 내역 보기"):
                display_df = df_filtered[['조회년월', 'num_price', 'floor']].rename(columns={
                    '조회년월': '거래월', 'num_price': '거래가(만원)', 'floor': '층'
                })
                st.dataframe(display_df, width="stretch", hide_index=True)

# ==========================================
# 3. 화면 구성 (앱 2: 취득세/보유세)
# ==========================================
@st.fragment 
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
    if st.button("세금 정밀 계산하기 🚀", width="stretch", key="btn_tax", type="primary"):
        st.toast("✅ 세금 정밀 계산 완료!", icon="💰") 
        
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
# 4. 화면 구성 (앱 3: 양도소득세)
# ==========================================
@st.fragment 
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
    if st.button("양도세 정밀 계산하기 🚀", width="stretch", key="btn_cgt", type="primary"):
        st.toast("✅ 양도소득세 산출 완료!", icon="📈") 
        
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
# 5. 화면 구성 (앱 4: 자금조달 및 대출 V2.1)
# ==========================================
@st.fragment 
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
        if st.button("PRO 정밀 분석 결과 보기 🚀", width="stretch", type="primary"):
            st.toast("✅ 대출 및 자금조달 분석 완료!", icon="🏦") 

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
                st.markdown("#### 💸 2. 자금조달 및 실제 월 상환액 브리팅")
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
        if st.button("맞춤형 전세대출 컨설팅 시작 🚀", width="stretch", type="primary"):
            st.toast("✅ 맞춤형 전세대출 컨설팅 완료!", icon="🔑") 

            if required_jeonse_loan == 0:
                st.success("보유 현금이 충분하여 전세 대출이 필요하지 않습니다! 🎉")
            elif jeonse_homes == "2주택 이상" or (jeonse_homes == "1주택" and is_1home_banned):
                st.error("🚨 **대출 불가!** 최신 규제로 인해 전세자금 보증이 거절됩니다.")
            else:
                st.markdown("#### 📊 맞춤형 전세대출 추천 결과 (1~3순위)")
                recommended_loans = []
                
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
                            "advantage": "HUG 상품의 경우, 대출과 동시에 전세보증금 반환보증보험이 100% 자동 가입되어 깡통전세 예방에 탁월합니다."
                        })
                
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
# 6. 관심 단지 1년 추이 전용 오버레이 화면
# ==========================================
def run_favorite_analysis_app():
    fav = st.session_state['auto_run_fav']
    
    st.markdown(f"""
    <div style="background-color:#EFF6FF; padding:20px; border-radius:15px; border-left: 10px solid #1E3A8A; margin-bottom:20px;">
        <h2 style="color:#1E3A8A; margin:0;">⭐ {fav['apt']} 정밀 분석</h2>
        <p style="color:#4B5563; margin: 5px 0 0 0; font-size:15px;">📍 {fav['gu']} {fav['dong']} | <b>최근 1년 치 시세 흐름</b>을 판독합니다.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("✖️ 분석 창 닫기 (홈 화면으로 돌아가기)", type="secondary", width="stretch"):
        del st.session_state['auto_run_fav']
        st.rerun()
        
    lawd_cd = GU_CODES[fav['gu']]
    deal_ym = "202602" 
    
    months_to_fetch = get_last_12_months(deal_ym)
    all_data = []
    my_bar = st.progress(0, text="1년 치 데이터를 불러오는 중입니다... (🚀 병렬 가속)")
    
    def fetch_month_data(ym):
        df, _ = fetch_real_estate_data("매매", lawd_cd, ym, SERVICE_KEY)
        if not df.empty:
            df['조회년월'] = ym
        return df

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch_month_data, ym): ym for ym in months_to_fetch}
        completed_count = 0
        for future in concurrent.futures.as_completed(futures):
            df = future.result()
            if not df.empty:
                all_data.append(df)
            completed_count += 1
            my_bar.progress(completed_count / 12, text=f"데이터 수집 완료... ({completed_count}/12)")
    
    my_bar.empty()
    
    if all_data:
        df_all = pd.concat(all_data, ignore_index=True)
        df_all['num_price'] = pd.to_numeric(df_all['dealAmount'].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce')
        df_all['num_area'] = pd.to_numeric(df_all['excluUseAr'], errors='coerce').round(1)
        
        df_fav = df_all[(df_all['umdNm'] == fav['dong']) & (df_all['aptNm'] == fav['apt'])]
        
        if not df_fav.empty:
            area_list = sorted(df_fav['num_area'].unique())
            sel_area = st.selectbox("**📐 면적(㎡) 선택**", area_list)
            df_filtered = df_fav[df_fav['num_area'] == sel_area].sort_values('조회년월')
            
            if not df_filtered.empty:
                trend_df = df_filtered.groupby('조회년월')['num_price'].mean().reset_index()
                
                fig = px.line(
                    trend_df, x='조회년월', y='num_price', markers=True,
                    title=f"📅 {fav['apt']} ({sel_area}㎡) 최근 1년 시세 흐름",
                    template="plotly_white",
                    labels={'조회년월': '거래월', 'num_price': '평균 매매가(만원)'} 
                )
                fig.update_traces(
                    line_color="#1E3A8A", line_width=3, marker_size=8,
                    hovertemplate="<b>%{x}</b><br>매매가: %{y:,}만 원<extra></extra>"
                )
                fig.update_layout(
                    height=350, 
                    margin=dict(l=0, r=0, t=40, b=0), 
                    xaxis=dict(title="", tickangle=-45, fixedrange=True), 
                    yaxis=dict(title="", fixedrange=True),
                    dragmode=False
                )
                # 🚀 핵심 해결 3: 관심 단지 그래프에도 staticPlot 속성을 부여하여 스와이프/확대 원천 차단
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True})
                
                max_val = int(df_filtered['num_price'].max())
                min_val = int(df_filtered['num_price'].min())
                avg_val = int(df_filtered['num_price'].mean())
                
                c1, c2, c3 = st.columns(3)
                c1.metric("1년 최고가 🏆", f"{max_val:,} 만원")
                c2.metric("1년 최저가 📉", f"{min_val:,} 만원")
                c3.metric("1년 평균가 📊", f"{avg_val:,} 만원")
                
                with st.expander("📊 상세 거래 내역 보기"):
                    st.dataframe(df_filtered[['조회년월', 'num_price', 'floor', 'dealDay']].rename(columns={
                        '조회년월': '거래월', 'num_price': '거래가(만원)', 'floor': '층', 'dealDay': '일'
                    }), width="stretch", hide_index=True)
            else:
                st.warning("선택한 면적의 최근 1년 매매 내역이 없습니다.")
        else:
            st.warning("해당 단지의 최근 1년 매매 실거래 내역이 없습니다. (거래 가뭄 또는 입력 오류)")
    else:
        st.error("데이터를 불러오지 못했습니다.")

# ==========================================
# 7. 메인 네비게이션 및 사이드바 (main 함수)
# ==========================================
def main():
    st.markdown("""
    <style>
        /* 1. 웹 폰트(Pretendard) 적용 */
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif !important;
        }

        /* 2. 전체 여백 최소화 및 깔끔한 배경 */
        .block-container { 
            padding-top: 2rem !important; 
            padding-bottom: 2rem !important;
            max-width: 1000px; 
        }

        /* 3. 메인 파란 버튼(primary) 디자인 고급화 */
        div.stButton > button[kind="primary"] {
            background-color: #1E3A8A !important; 
            color: white !important; 
            font-weight: 600 !important;
            border-radius: 8px !important; 
            transition: all 0.2s ease-in-out;
        }
        div.stButton > button[kind="primary"]:hover {
            transform: translateY(-2px);
        }
        
        /* 4. 사이드바 관심 단지 버튼 커스텀 스타일링 */
        div[data-testid="stSidebar"] div.stButton > button[kind="secondary"] {
            border-radius: 6px;
            border: 1px solid #E2E8F0;
            background-color: #F8FAFC;
            color: #0F172A;
            padding: 0.6rem;
            transition: all 0.2s ease;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        div[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover {
            border-color: #1E3A8A;
            color: #1E3A8A;
            background-color: #EFF6FF;
        }

        /* 5. 탭(Tab) 디자인 강조 */
        div[data-baseweb="tab-list"] { 
            gap: 10px; 
            border-bottom: 2px solid #D1D5DB;
        }
        button[data-baseweb="tab"] {
            font-size: 18px !important;
            font-weight: 800 !important;
            background-color: transparent !important; 
            border: none !important;
            padding: 14px 20px !important; 
            color: #6B7280 !important;
        }
        button[data-baseweb="tab"]:hover {
            color: #111827 !important;
        }
        button[aria-selected="true"] { 
            color: #1E3A8A !important;
            background-color: #EFF6FF !important;
            border-radius: 8px 8px 0 0 !important;
            border-bottom: 4px solid #1E3A8A !important;
        }
        button[aria-selected="true"] p {
            color: #1E3A8A !important;
        }

        /* 6. 사이드바 뉴스 박스 디자인 */
        .news-box { 
            padding: 12px; border-radius: 8px; margin-bottom: 12px; font-size: 13px; line-height: 1.4; 
            border: 1px solid #E5E7EB; 
        }
        .news-date { font-weight: 600 !important; font-size: 12px; margin-bottom: 4px; }
        .bg-red { background-color: #fef2f2; border-left: 4px solid #ef4444; color: #991b1b !important; }
        .bg-yellow { background-color: #fefce8; border-left: 4px solid #eab308; color: #854d0e !important; }
        .bg-blue { background-color: #eff6ff; border-left: 4px solid #3b82f6; color: #1e40af !important; }
        .bg-gray { background-color: #f9fafb; border-left: 4px solid #6b7280; color: #374151 !important; }

        /* 7. 홈 화면 기능 카드 스타일 */
        .feature-card {
            background-color: #ffffff;
            border-radius: 16px;
            padding: 24px;
            border: 1px solid #E5E7EB;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            text-align: center;
            margin-bottom: 20px;
            height: 220px;
        }
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
            border-color: #1E3A8A;
        }
        .feature-icon { font-size: 40px; margin-bottom: 15px; }
        .feature-title { font-size: 17px; font-weight: 700; color: #111827; margin-bottom: 10px; }
        .feature-desc { font-size: 13px; color: #6B7280; line-height: 1.5; }
        
        h1, h2, h3, h4 { font-weight: 700 !important; letter-spacing: -0.5px; }
        
        /* 🚀 8. 불필요한 Deploy 버튼 숨김 (사이드바 버튼에는 영향 안 줌) */
        [data-testid="stAppDeployButton"],
        .stAppDeployButton {
            display: none !important;
            visibility: hidden !important;
        }
        
        /* 🚀 9. iframe 하얀 배경을 완전히 투명하게 만드는 CSS (애니메이션 해결 코드 유지) */
        iframe {
            background-color: transparent !important;
            border: none !important;
        }

        /* 🚀 10. 사이드바 관심단지 목록 모바일 세로 겹침 방지 및 삭제 버튼 크기 최적화 */
        div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: stretch !important;
            gap: 8px !important;
        }
        div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1) {
            width: 80% !important;
            flex: 1 1 80% !important;
            min-width: 0 !important;
        }
        div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
            width: 20% !important;
            flex: 1 1 20% !important;
            min-width: 0 !important;
        }
        /* 삭제 버튼(✖) 전용 디자인 (직관성 강화) */
        div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) button {
            background-color: #fef2f2 !important;
            border: 1px solid #fecdd3 !important;
            color: #e11d48 !important;
            padding: 0 !important;
            min-height: 2.8rem;
        }
        div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) button:hover {
            background-color: #ffe4e6 !important;
            border-color: #e11d48 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # 셀렉트박스 터치 시 모바일 키보드 팝업 강제 차단 스크립트
    disable_keyboard_js = """
    <script>
        const doc = window.parent.document;
        // 화면에 변화가 생길 때마다 셀렉트박스 input을 찾아 키보드 비활성화 속성 주입
        const observer = new MutationObserver((mutations) => {
            const selectInputs = doc.querySelectorAll('div[data-baseweb="select"] input');
            selectInputs.forEach((input) => {
                if (input.getAttribute('inputmode') !== 'none') {
                    input.setAttribute('inputmode', 'none');
                }
            });
        });
        observer.observe(doc.body, { childList: true, subtree: true });
    </script>
    """
    components.html(disable_keyboard_js, height=0, width=0)

    # 🚀 핵심 해결 3: 강력해진 사이드바 자동 닫기 스크립트 (모바일 배경 터치 + ESC 연타)
    if st.session_state.get('collapse_sidebar', False):
        collapse_js = """
        <script>
            const doc = window.parent.document;
            let attempts = 0;
            const interval = setInterval(() => {
                // 1. ESC 키보드 이벤트 강제 발생
                doc.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', code: 'Escape', bubbles: true}));
                
                // 2. 모바일 환경: 사이드바 바깥쪽 반투명 어두운 배경(Backdrop) 강제 터치
                const overlay = doc.querySelector('[data-testid="stSidebar"] + div');
                if (overlay) overlay.click();
                
                // 3. PC 환경: 명시적 닫기 버튼 클릭
                const closeBtn = doc.querySelector('[data-testid="stSidebarCollapseButton"]');
                if (closeBtn) closeBtn.click();
                
                attempts++;
                if(attempts > 5) clearInterval(interval);
            }, 100);
        </script>
        """
        components.html(collapse_js, height=0, width=0)
        st.session_state['collapse_sidebar'] = False

    with st.sidebar:
        if os.path.exists(logo_path):
            st.image(logo_path, width="stretch")
        else:
            st.markdown("<h2 style='text-align: center; color: #333;'>🏢 집스탯 (ZipStat)</h2>", unsafe_allow_html=True)
            
        st.markdown("---")
        st.markdown("### ⭐ 내 관심 단지")
        
        f_list = st.session_state['fav_apts']
            
        if not f_list:
            st.info("실거래가 탭에서 자주 보는 아파트를 등록해 보세요!")
        else:
            for idx, fav in enumerate(f_list):
                c1, c2 = st.columns([4, 1]) 
                with c1:
                    if st.button(f"📊 {fav['apt']} ({fav['dong']})", key=f"fbtn_view_{idx}", use_container_width=True):
                        st.session_state['auto_run_fav'] = fav
                        st.session_state['collapse_sidebar'] = True 
                        st.rerun()
                with c2:
                    if st.button("✖", key=f"fbtn_del_{idx}", use_container_width=True):
                        new_list = [f for f in f_list if not (f['apt'] == fav['apt'] and f['dong'] == fav['dong'])]
                        st.session_state['fav_apts'] = new_list
                        st.session_state['needs_ls_save'] = True
                        st.rerun()
        
        st.markdown("---")
        st.markdown("### 📢 부동산/금융 최신 트렌드")
        st.markdown("""
        <div class="news-box bg-red">
            <div class="news-date">🚨 [2026.04.10 속보] 한국은행 기준금리</div>
            이창용 총재 마지막 금통위, 기준금리 <b>연 2.50%로 7차례 연속 동결</b> (물가 및 환율 변동성 우려 반영)
        </div>
        <div class="news-box bg-yellow">
            <div class="news-date">⚠️ [2026.04.17 시행 임박] 대출 규제</div>
            가계부채 관리방안에 따라 다주택자의 주담대 <b>만기 연장이 원칙적으로 금지</b>됩니다. (유동성 확보 비상)
        </div>
        <div class="news-box bg-blue">
            <div class="news-date">📈 [2026.04 1주차] 주간 아파트 동향</div>
            전국 매매가(+0.04%), 전세가(+0.09%) 동반 상승. 서울·수도권 역세권 단지 중심으로 매수심리 유지 중.
        </div>
        <div class="news-box bg-gray">
            <div class="news-date">📌 [2026 최신] 디딤돌대출 규제</div>
            수도권 아파트 매수 시 최우선변제금(방공제) <b>약 4,800만 원 대출 한도 차감</b> 의무화.
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        total, daily = update_and_get_visitor_count()
        st.markdown(f"<div style='text-align: center; color: #888; font-size: 13px;'>👁️ <b>오늘 방문:</b> {daily} 명 &nbsp;|&nbsp; <b>총 방문:</b> {total} 명</div>", unsafe_allow_html=True)
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; color: #aaaaaa; font-size: 11px;">
            © 2026 ZipStat PRO.<br>All rights reserved.<br><br>
            👨‍💻 Developed by <b>[sweetourzip@naver.com]</b>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"<h1 style='text-align: center; color: #1E3A8A;'>{title_icon_html}집스탯 (ZipStat) PRO V2.1</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555555;'>실거래가 분석부터 최신 규제 반영 자금조달까지 원클릭으로!</p>", unsafe_allow_html=True)

    if 'auto_run_fav' in st.session_state:
        run_favorite_analysis_app()
    else:
        tab0, tab1, tab2, tab3, tab4 = st.tabs(["🏠 홈", "🔍 실거래가 분석", "💰 세금 계산", "📈 양도세 계산", "🏦 자금조달/대출"])
        
        with tab0: run_home_app()
        with tab1: run_real_estate_app() 
        with tab2: run_tax_app()
        with tab3: run_capital_gains_tax_app()
        with tab4: run_loan_simulator_app()
            
    st.markdown("---")
    st.caption("💡 본 대시보드는 실무 참고용이며, 정확한 세금 및 대출 한도는 전문가 및 금융기관과 상담하시기 바랍니다.")

if __name__ == "__main__":
    main()
