import base64
import io
import os
import re
import zipfile
from datetime import datetime

import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="GPT 이미지 스튜디오", page_icon="🎨", layout="wide")
st.title("🎨 GPT 이미지 스튜디오")
st.caption("이미지 모델을 선택하고 명령어를 입력하면 결과를 PNG로 저장할 수 있습니다.")

MODELS = {
    "GPT Image 2 (기본)": "gpt-image-2",
    "GPT Image 2.5 Sunburst": "gpt-image-2.5-sunburst",
    "GPT Image 2.5 Flare": "gpt-image-2.5-flare",
    "GPT Image 1.5": "gpt-image-1.5",
    "GPT Image 1 Mini (저비용)": "gpt-image-1-mini",
}

with st.sidebar:
    st.header("API 연결")
    api_key = st.text_input("본인의 OpenAI API 키", type="password", help="사용자가 자신의 API 키로 생성 비용을 부담합니다. 이 키를 GitHub에 업로드하지 마세요.").strip()
    st.caption("공개 웹사이트에서는 사용자별 API 키를 입력해야 합니다. 키는 코드나 파일에 저장하지 않습니다.")
    st.divider()
    st.header("생성 설정")
    model_label = st.selectbox("이미지 생성 GPT 모델", list(MODELS))
    model = MODELS[model_label]
    size = st.selectbox("이미지 크기", ["1536x1024", "1024x1024", "1024x1536", "auto"])
    quality = st.selectbox("품질", ["medium", "low", "high", "auto"])
    count = st.number_input("생성 개수", min_value=1, max_value=4, value=1, step=1)
    st.info("모델 및 계정에 따라 일부 옵션이 지원되지 않을 수 있습니다. API 오류가 발생하면 모델·크기·품질을 변경하세요.")
    st.caption(f"현재 세션에서 남은 생성 한도: {st.session_state.get('remaining_images', 8)}장 (서버 전체 사용량 제한은 아님)")

prompt = st.text_area(
    "이미지 생성 명령어",
    value="윈도우11에서 보안 검사 화면과 정상적인 라이선스 인증 상태를 나란히 보여주는 깔끔한 한국어 컴퓨터 화면 이미지",
    height=135,
)
style = st.selectbox("스타일 (선택)", ["원문 그대로", "블로그용 깔끔한 인포그래픽", "실사 컴퓨터 화면", "심플한 IT 일러스트"])
style_guides = {
    "원문 그대로": "",
    "블로그용 깔끔한 인포그래픽": "깔끔한 블로그용 기술 인포그래픽, 선명한 구성, 가독성 높은 한국어 제목, 화면 비율에 맞게 배치.",
    "실사 컴퓨터 화면": "현실적인 컴퓨터 모니터 사진 스타일, 정돈된 데스크 환경, 자연스러운 조명.",
    "심플한 IT 일러스트": "미니멀한 IT 벡터 일러스트, 간결한 도형, 조화로운 블루 톤.",
}

if "generated" not in st.session_state:
    st.session_state.generated = []

if st.button("✨ 이미지 생성하기", type="primary", use_container_width=True):
    if st.session_state.get("remaining_images", 8) < int(count):
        st.error("이 세션에서 생성 가능한 수량(최대 8장)을 초과했습니다.")
    elif not api_key:
        st.error("OpenAI API 키를 입력하거나 OPENAI_API_KEY 환경변수를 설정하세요.")
    elif not prompt.strip():
        st.warning("이미지 설명을 입력하세요.")
    else:
        client = OpenAI(api_key=api_key, timeout=90.0, max_retries=1)
        full_prompt = prompt.strip() + ("\n\n" + style_guides[style] if style_guides[style] else "")
        images = []
        progress = st.progress(0)
        with st.spinner("이미지 생성 API에 요청 중입니다..."):
            for i in range(int(count)):
                try:
                    result = client.images.generate(
                        model=model,
                        prompt=full_prompt,
                        size=size,
                        quality=quality,
                        n=1,
                    )
                    item = result.data[0]
                    if not item.b64_json:
                        raise ValueError("이미지 데이터가 반환되지 않았습니다.")
                    img = base64.b64decode(item.b64_json)
                    filename = f"gpt_image_{datetime.now():%Y%m%d_%H%M%S}_{i+1:02d}.png"
                    images.append((filename, img))
                    st.session_state.remaining_images = st.session_state.get("remaining_images", 8) - 1
                except Exception as exc:
                    st.error(f"{i+1}번째 이미지 생성 실패: {exc}")
                    break
                finally:
                    progress.progress((i + 1) / int(count))
        if images:
            st.session_state.generated = images
            st.success(f"{len(images)}개 이미지 생성 완료")

if st.session_state.generated:
    st.subheader("생성 결과")
    images = st.session_state.generated
    for i in range(0, len(images), 2):
        cols = st.columns(2)
        for col, (filename, image_bytes) in zip(cols, images[i:i+2]):
            with col:
                st.image(image_bytes, caption=filename, use_container_width=True)
                st.download_button(
                    "⬇ PNG 다운로드", image_bytes, file_name=filename,
                    mime="image/png", key=f"download_{filename}", use_container_width=True
                )
    if len(images) > 1:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename, image_bytes in images:
                zf.writestr(filename, image_bytes)
        st.download_button("📦 전체 ZIP 다운로드", buffer.getvalue(),
                           file_name="gpt_images.zip", mime="application/zip", use_container_width=True)
