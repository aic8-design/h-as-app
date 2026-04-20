import streamlit as st
import gspread
import pandas as pd
import json
from datetime import datetime
import cloudinary
import cloudinary.uploader

# ==========================================
# 1. 초기 설정 및 클라우드 연결
# ==========================================
st.set_page_config(page_title="히트펌프 장비 관리 시스템", layout="wide")

try:
    # GCP 서비스 계정 연결
    try:
        service_info = json.load(open('hallowed-winter-493604-k9-234626bef11e.json'))
    except FileNotFoundError:
        secret_data = st.secrets["gcp_service_account"]
        service_info = json.loads(secret_data) if isinstance(secret_data, str) else dict(secret_data)
        
    gc = gspread.service_account_from_dict(service_info)
    sh = gc.open("HEAT PUMP") 
    
    # ☁️ Cloudinary 설정 (본인 정보로 수정 필수)
    cloudinary.config(
        cloud_name = "dyxuhtloo", 
        api_key = "711879852278235", 
        api_secret = "katQ2CanHxv9--WJyiYtcW2keNs",
        secure = True
    )
except Exception as e:
    st.error(f"⚠️ 시스템 연결 실패: {e}")
    st.stop()

# ==========================================
# 2. 세션 상태 (로그인 유지) 관리
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

# 데이터 불러오기 캐싱 (속도 향상 및 API 제한 방지)
@st.cache_data(ttl=60)
def load_sheet_data(sheet_name):
    try:
        worksheet = sh.worksheet(sheet_name)
        # ★ 수정됨: 헤더가 2행에 있으므로 head=2 옵션 적용 (데이터는 3행부터 읽음)
        records = worksheet.get_all_records(head=2)
        return pd.DataFrame(records)
    except Exception as e:
        return pd.DataFrame()

# ==========================================
# 3. 로그인 화면
# ==========================================
if not st.session_state['logged_in']:
    st.markdown("### 🔲 히트펌프 장비 관리")
    with st.form("login_form"):
        user_id = st.text_input("아이디")
        user_pw = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            df_accounts = load_sheet_data("계정관리")
            
            if df_accounts.empty:
                st.error("계정 정보를 불러올 수 없거나 시트 형식이 맞지 않습니다.")
            else:
                # ID와 PW가 일치하는 행 찾기
                user_row = df_accounts[(df_accounts['ID'] == user_id) & (df_accounts['PW'].astype(str) == user_pw)]
                
                if not user_row.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user_row.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 틀렸습니다.")
    st.stop() # 로그인 안 되면 아래 코드 실행 안 함

# ==========================================
# 4. 메인 화면 (로그인 성공 후)
# ==========================================
user_info = st.session_state['user_info']
auth_level = user_info.get('권한', '') # 하이에어공조 or 대리점
user_company = user_info.get('업체명', '')

# 상단 헤더 및 로그아웃
col1, col2 = st.columns([8, 2])
col1.markdown(f"### 🔲 히트펌프 장비 관리 (접속: {user_company})")
if col2.button("로그아웃"):
    st.session_state['logged_in'] = False
    st.session_state['user_info'] = None
    st.rerun()

st.write("---")

# 장비 구분 선택 (라디오 버튼)
equipment_type = st.radio(
    "장비 구분", 
    ["해수열", "폐수열", "공기열", "건조기(김공장)", "어선용"], 
    horizontal=True
)

# 선택한 장비 탭의 데이터 불러오기
df_equip = load_sheet_data(equipment_type)

if df_equip.empty:
    st.warning(f"구글 시트에 '{equipment_type}' 탭이 없거나 데이터가 비어 있습니다. (헤더가 2행에 있는지 확인하세요)")
    st.stop()

# --- 검색 필터링 (권한에 따라 다름) ---
st.write("#### 🔍 업체 검색")
search_col1, search_col2, search_col3 = st.columns([3, 3, 4])

selected_agency = None
selected_customer = None

if auth_level == "하이에어공조":
    # 본사: 모든 대리점 목록 보기 가능
    agency_list = ["전체"] + list(df_equip['대리점'].dropna().unique())
    selected_agency = search_col1.selectbox("대리점", agency_list)
    
    # 대리점 선택에 따라 고객사 목록 필터링
    if selected_agency != "전체":
        filtered_df = df_equip[df_equip['대리점'] == selected_agency]
    else:
        filtered_df = df_equip
        
    customer_list = ["선택하세요"] + list(filtered_df['업체명'].dropna().unique())
    selected_customer = search_col2.selectbox("업체명", customer_list)

else:
    # 대리점: 자기 자신의 업체명으로 고정
    search_col1.text_input("대리점", value=user_company, disabled=True)
    
    # 자기 대리점 소속의 고객사만 표시
    filtered_df = df_equip[df_equip['대리점'] == user_company]
    customer_list = ["선택하세요"] + list(filtered_df['업체명'].dropna().unique())
    selected_customer = search_col2.selectbox("업체명", customer_list)

# ==========================================
# 5. 상세 정보 출력 (업체가 선택되었을 때)
# ==========================================
if selected_customer != "선택하세요" and selected_customer is not None:
    # 선택된 업체의 데이터 추출
    cust_data = filtered_df[filtered_df['업체명'] == selected_customer].iloc[0]
    
    # 1) 업체 정보
    st.markdown("▶ **업체 정보**")
    st.info(f"""
    - **대표자:** {cust_data.get('대표자', '')}
    - **연락처:** {cust_data.get('연락처', '')}
    - **주소:** {cust_data.get('주소', '')}
    """)
    
    # 2) 장비 납품 내역
    st.markdown("▶ **장비 납품 내역**")
    history_df = filtered_df[filtered_df['업체명'] == selected_customer]
    
    # ★ 수정됨: AS기준 -> AS기간
    if auth_level == "하이에어공조":
        display_cols = ['설치 날짜', 'AS기간', '규격', '수량', '사업명', '계약금액', '대리점']
    else:
        display_cols = ['규격', '수량', '사업명', '설치 날짜', 'AS기간']
    
    # 존재하는 열만 추려서 표로 보여주기
    existing_cols = [col for col in display_cols if col in history_df.columns]
    st.dataframe(history_df[existing_cols], hide_index=True, use_container_width=True)
    
    # 3) 장비 AS 이력 (AS내역 시트에서 필터링)
    st.markdown("▶ **장비 AS 이력**")
    df_as = load_sheet_data("AS내역")
    
    if not df_as.empty and '업체명' in df_as.columns:
        cust_as_history = df_as[df_as['업체명'] == selected_customer]
        if not cust_as_history.empty:
            if auth_level == "하이에어공조":
                as_disp_cols = ['접수시간', '업체명', 'AS 항목', '담당자', '입력자', '상세 내용']
            else:
                as_disp_cols = ['접수시간', '업체명', 'AS 항목', '담당자', '상세 내용']
                
            as_exist_cols = [col for col in as_disp_cols if col in cust_as_history.columns]
            st.dataframe(cust_as_history[as_exist_cols], hide_index=True, use_container_width=True)
        else:
            st.write("해당 업체의 AS 이력이 없습니다.")
    else:
        st.write("AS 이력 데이터를 불러올 수 없거나 이력이 없습니다.")

    # ==========================================
    # 6. AS 내역 추가 (Form)
    # ==========================================
    with st.expander("➕ AS 내역 추가하기", expanded=False):
        with st.form("add_as_form", clear_on_submit=False):
            st.write(f"**[{selected_customer}]** AS 내역 접수")
            
            # AS 항목 (중복 선택)
            as_items = st.multiselect("▶ AS 항목", ["COMP", "COIL", "응축기", "배관", "PANEL", "기타"])
            as_detail = st.text_area("▶ AS 상세 내용(증상 및 조치사항)")
            manager_name = st.text_input("▶ 담당자 이름")
            
            # 파일 업로드 (사진, PDF)
            photo_file = st.file_uploader("▶ 현장 사진 (JPG, PNG)", type=['jpg', 'png', 'jpeg'])
            pdf_file = st.file_uploader("▶ 증빙 서류 (SERVICE REPORT - PDF)", type=['pdf'])
            
            submit_btn = st.form_submit_button("구글 서버로 전송")
            
            if submit_btn:
                if not as_items or not manager_name:
                    st.warning("AS 항목과 담당자 이름은 필수 입력입니다!")
                else:
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    photo_link = "첨부없음"
                    pdf_link = "첨부없음"
                    
                    with st.spinner("서버로 전송 중입니다..."):
                        # 사진 업로드 (Cloudinary)
                        if photo_file:
                            try:
                                res = cloudinary.uploader.upload(photo_file, folder="AS_PHOTOS", resource_type="image")
                                photo_link = res.get("secure_url")
                            except Exception as e: photo_link = f"오류: {e}"
                        
                        # PDF 업로드
                        if pdf_file:
                            try:
                                res = cloudinary.uploader.upload(pdf_file, folder="AS_REPORTS", resource_type="auto")
                                pdf_link = res.get("secure_url")
                            except Exception as e: pdf_link = f"오류: {e}"
                        
                        # AS내역 시트에 행 추가 (append_row는 자동으로 맨 밑 빈 줄을 찾아서 넣습니다)
                        try:
                            ws_as = sh.worksheet("AS내역")
                            items_str = ", ".join(as_items)
                            new_row = [now_str, selected_customer, items_str, as_detail, manager_name, user_info['업체명'], photo_link, pdf_link]
                            ws_as.append_row(new_row)
                            
                            st.success("✅ AS 내역이 성공적으로 접수되었습니다!")
                            st.balloons()
                            # 캐시 지우기 (최신 데이터 반영 위해)
                            st.cache_data.clear()
                        except Exception as e:
                            st.error(f"시트 기록 실패: {e}")