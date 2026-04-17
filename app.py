import streamlit as st
import gspread
import json
from datetime import datetime

# 1. 🔑 [보안 핵심] 하이브리드 연결 (방탄 코드 적용)
try:
    try:
        # [1순위: PC 테스트용] 
        gc = gspread.service_account(filename='hallowed-winter-493604-k9-234626bef11e.json')
    except FileNotFoundError:
        # [2순위: 클라우드용] 
        secret_data = st.secrets["gcp_service_account"]
        
        # 스트림릿이 금고 내용을 어떻게 해석했든 무조건 구글 열쇠로 변환해 주는 마법의 코드
        if isinstance(secret_data, str):
            service_info = json.loads(secret_data)
        else:
            service_info = dict(secret_data)
            
        gc = gspread.service_account_from_dict(service_info)
    
    # 구글 스프레드시트 연결
    sh = gc.open("HEAT PUMP AS내역") 
    worksheet = sh.sheet1

except Exception as e:
    st.error(f"⚠️ 구글 시트 연결 실패: {e}")
    st.stop()

# 2. 📱 모바일 최적화 화면 설정
st.set_page_config(page_title="H-TECH AS", layout="centered")

# 버튼을 큼직하게 만드는 디자인 코드
st.markdown("""
    <style>
    div.stButton > button { width: 100%; height: 60px; font-size: 20px; font-weight: bold; background-color: #0066cc; color: white; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("🛠️ AS 현장 데이터 입력")

# 3. 📝 데이터 입력창 구성
with st.form("as_form", clear_on_submit=True):
    company = st.selectbox("🏢 업체명", ["박철수 어가", "김정선 어가", "김수지 어가", "기타"])
    status = st.radio("⚙️ 장비 상태", ["COMP 불량", "COIL 교체", "PCB 에러", "누수", "기타"])
    detail = st.text_area("📝 상세 내용")
    manager = st.text_input("👤 담당자 이름")
    
    # 사진 업로드 (파일명 정제 로직 포함)
    uploaded_file = st.file_uploader("📸 현장 사진 (선택)", type=['jpg', 'png', 'jpeg'])

    st.write("---")
    submit_button = st.form_submit_button("구글 서버로 전송")

# 4. 🚀 데이터 전송 로직
if submit_button:
    if not manager:
        st.warning("담당자 이름을 입력해 주세요!")
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 파일명 규칙: 언더바(_)를 공백( )으로 자동 변경
        file_info = "사진 없음"
        if uploaded_file:
            file_info = uploaded_file.name.replace("_", " ")
        
        # 구글 시트에 한 줄 추가
        row = [now, company, f"{status} ({detail})" if detail else status, manager, file_info]
        worksheet.append_row(row)
        
        st.success(f"✅ {company} 접수 완료! 사내 엑셀로 자동 취합됩니다.")
        st.balloons()