import streamlit as st
import gspread
import json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# 1. 🔑 [보안 핵심] 하이브리드 연결
try:
    try:
        # [PC 테스트용]
        service_info = json.load(open('hallowed-winter-493604-k9-234626bef11e.json'))
    except FileNotFoundError:
        # [클라우드용]
        secret_data = st.secrets["gcp_service_account"]
        service_info = json.loads(secret_data) if isinstance(secret_data, str) else dict(secret_data)
        
    # --- 시트 접속기 ---
    gc = gspread.service_account_from_dict(service_info)
    sh = gc.open("HEAT PUMP AS내역") 
    worksheet = sh.sheet1
    
    # --- 드라이브 접속기 (사진 업로드용 추가) ---
    credentials = service_account.Credentials.from_service_account_info(
	service_info, 
	scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
    )
    drive_service = build('drive', 'v3', credentials=credentials)
    
    # 여기에 아까 복사한 구글 드라이브 폴더 ID를 붙여넣으세요! 
    DRIVE_FOLDER_ID = '1dtMtedii_bpSQobL-CGupfc5IkW-opgU'

except Exception as e:
    st.error(f"⚠️ 시스템 연결 실패: {e}")
    st.stop()

# 2. 📱 모바일 최적화 화면 설정
st.set_page_config(page_title="H-TECH AS", layout="centered")
st.markdown("<style>div.stButton > button { width: 100%; height: 60px; font-size: 20px; font-weight: bold; background-color: #0066cc; color: white; border-radius: 10px; }</style>", unsafe_allow_html=True)

st.title("🛠️ AS 현장 데이터 입력")

# 3. 📝 데이터 입력창
with st.form("as_form", clear_on_submit=True):
    company = st.selectbox("🏢 업체명", ["박철수 어가", "김정선 어가", "김수지 어가", "기타"])
    status = st.radio("⚙️ 장비 상태", ["COMP 불량", "COIL 교체", "PCB 에러", "누수", "기타"])
    detail = st.text_area("📝 상세 내용")
    manager = st.text_input("👤 담당자 이름")
    uploaded_file = st.file_uploader("📸 현장 사진 (선택)", type=['jpg', 'png', 'jpeg'])
    
    st.write("---")
    submit_button = st.form_submit_button("구글 서버로 전송")

# 4. 🚀 데이터 전송 로직
if submit_button:
    if not manager:
        st.warning("담당자 이름을 입력해 주세요!")
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        file_link = "사진 없음" # 기본값
        
        # 사진이 첨부되었다면 구글 드라이브에 업로드!
        if uploaded_file:
            file_name = uploaded_file.name.replace("_", " ")
            
            with st.spinner("📸 사진을 안전하게 금고(드라이브)에 저장 중입니다..."):
                file_metadata = {'name': file_name, 'parents': [DRIVE_FOLDER_ID]}
                media = MediaIoBaseUpload(io.BytesIO(uploaded_file.getvalue()), mimetype=uploaded_file.type, resumable=False) 
                
                # 드라이브에 올리고 링크(webViewLink)를 받아옴
                uploaded_photo = drive_service.files().create(
		    body=file_metadata, 
		    media_body=media, 
		    fields='id, webViewLink',
		    supportsAllDrives=True  
		).execute()
                
                # 사진 링크 추출
                file_link = uploaded_photo.get('webViewLink')
        
        # 구글 시트에는 사진 이름 대신 '사진 웹 링크'를 적어줍니다!
        row = [now, company, f"{status} ({detail})" if detail else status, manager, file_link]
        worksheet.append_row(row)
        
        st.success(f"✅ {company} 접수 완료! (사진 링크 생성 성공)")
        st.balloons()