# GPT 이미지 스튜디오 (GitHub / Streamlit Cloud 배포용)

## 배포
1. 이 폴더의 `app.py`, `requirements.txt`, `README.md`, `.gitignore`를 GitHub 저장소 최상위에 업로드합니다. **ZIP 파일 자체는 업로드하지 않습니다.**
2. Streamlit Community Cloud에서 `Deploy a public app from GitHub` 선택
3. Repository: `ss00sszz/gpt-image-studio` (예시) / Branch: `main` / Main file: `app.py`
4. Deploy 후 사이트에서 **이용자 본인의** OpenAI API 키를 입력해 이미지 생성

## 주의 사항
- 실제 API 키, `.env`, `.streamlit/secrets.toml` 파일을 공개 저장소에 업로드하지 마세요.
- 현재 코드는 방문자별 API 키 입력 방식이며 운영자 키를 서버에서 제공하지 않습니다.
- 사용자의 API 키는 세션 입력 위젯과 요청 과정에서 서버에 전달됩니다. 앱 운영자 및 배포 플랫폼을 신뢰할 수 있는 환경에서만 사용하세요.
- 세션당 8장 제한은 비용/남용에 대한 전역 제어가 아닙니다. 공개 유료 서비스로 운영하려면 계정 인증, 서버 측 요금/호출 제한, 로깅 통제가 추가로 필요합니다.
- 모델 사용 권한과 API 크레딧에 따라 생성이 실패할 수 있습니다.
