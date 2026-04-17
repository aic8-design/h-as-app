import streamlit as st
import gspread
import json
from datetime import datetime
import cloudinary
import cloudinary.uploader

# ==========================================
# 1. 🔑 보안 설정 및 외부 서비스 연결
# ==========================================
try:
    # --- [A] 구글 스프레드시트 연결 (기존 하이브리드 방식) ---
    try:
        # PC 테스트용: 로컬에 파일이 있는 경우
        service_info = json.load(open('hallowed-winter-493604-k9-234626bef11e.json'))
    except FileNotFoundError:
        # 스트림릿 클라우드용: Secrets 금고에서 읽기
        secret_data = st.secrets["gcp_service_account"]
        if isinstance(secret_data, str):
            service_info = json.loads(secret_data)
        else:
            service_info = dict(secret_data)
            
    # 시트 접속기 실행
    gc = gspread.service_account_from_dict(service_info)
    sh = gc.open("HEAT PUMP AS내역")  # 관리자님 시트 이름
    worksheet = sh.sheet1

    # --- [B] ☁️ Cloudinary 설정 (본인 계정 정보로 수정 필수!) ---
    # Cloudinary 대시보드(Dashboard) 화면에 있는 정보를 복사해서 넣으세요.
    cloudinary.config(
        cloud_name = "dyxuhtloo", 
        api_key = "711879852278235", 
        api_secret = "katQ2CanHxv9--WJyiYtcW2keNs",
        secure = True
    )

except Exception as e:
    st.error(f"⚠️ 초기 연결 실패: {e}")
    st.stop()

# ==========================================
# 2. 📱 모바일 최적화 화면 구성
# ==========================================
st.set_page_config(page_title="H-TECH AS", layout="centered")

# 버튼 디자인 커스텀
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        height: 60px;
        font-size: 20px;
        font-weight: bold;
        background-color: #0066cc;
        color: white;
        border-radius: 10px;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #004d99;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛠️ AS 현장 데이터 입력")
st.write("현장에서 수리 내용을 입력하면 사내 마스터 엑셀로 자동 전송됩니다.")

# 데이터 입력 양식
with st.form("as_form", clear_on_submit=False):
    company = st.selectbox("🏢 업체명", ["박철수 어가", "김정선 어가", "김수지 어가", "기타"])
    status = st.radio("⚙️ 장비 상태", ["COMP 불량", "COIL 교체", "PCB 에러", "누수", "기타"], horizontal=True)
    detail = st.text_area("📝 상세 내용 (증상 및 조치사항)")
    manager = st.text_input("👤 담당자 이름")
    
    # 사진 업로드 칸
    uploaded_file = st.file_uploader("📸 현장 사진 (선택)", type=['jpg', 'png', 'jpeg'])
    
    st.write("---")
    submit_button = st.form_submit_button("구글 서버로 전송")

# ==========================================
# 3. 🚀 데이터 저장 로직
# ==========================================
if submit_button:
    if not manager:
        st.warning("담당자 이름을 입력해 주세요!")
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_link = "사진 없음"
        
        # [사진이 있는 경우] Cloudinary로 업로드
        if uploaded_file is not None:
            try:
                with st.spinner("📸 사진을 클라우드에 안전하게 저장 중..."):
                    # 파일명에서 언더바(_) 제거하여 업로드
                    clean_name = uploaded_file.name.split('.')[0].replace("_", " ")
                    
                    upload_result = cloudinary.uploader.upload(
                        uploaded_file,
                        folder = "AS_PHOTOS",
                        public_id = f"{now.replace(':', '-')}_{clean_name}"
                    )
                    # 성공 시 클릭 가능한 이미지 URL 획득
                    file_link = upload_result.get("secure_url")
            except Exception as e:
                file_link = f"사진 업로드 실패: {e}"
                st.error(f"사진 저장 중 오류 발생: {e}")

        # [구글 시트에 최종 기록]
        try:
            # 1행: 시간, 2행: 업체명, 3행: 상태+내용, 4행: 담당자, 5행: 사진링크
            status_full = f"{status} ({detail})" if detail else status
            row = [now, company, status_full, manager, file_link]
            
            worksheet.append_row(row)
            
            st.success(f"✅ {company} 접수 완료!")
            if "http" in file_link:
                st.info("💡 사진이 포함된 데이터가 정상적으로 전송되었습니다.")
            st.balloons()
            
        except Exception as e:
            st.error(f"구글 시트 기록 실패: {e}")