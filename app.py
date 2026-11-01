import base64
import io
import zipfile
from datetime import datetime

import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="GPT 이미지 스튜디오", page_icon="🎨", layout="wide")
st.title("🎨 GPT 이미지 스튜디오")
st.caption("기존 단일 이미지 생성 + 서로 다른 내용의 카드뉴스 최대 5장 일괄 생성")

MODELS = {
    "GPT Image 2 (기본)": "gpt-image-2",
    "GPT Image 2.5 Sunburst": "gpt-image-2.5-sunburst",
    "GPT Image 2.5 Flare": "gpt-image-2.5-flare",
    "GPT Image 1.5": "gpt-image-1.5",
    "GPT Image 1 Mini (저비용)": "gpt-image-1-mini",
}
STYLES = {
    "원문 그대로": "",
    "블로그용 깔끔한 인포그래픽": "깔끔한 블로그용 기술 인포그래픽, 선명한 구성, 가독성 높은 한국어 제목, 화면 비율에 맞게 배치.",
    "실사 컴퓨터 화면": "현실적인 컴퓨터 모니터 사진 스타일, 정돈된 데스크 환경, 자연스러운 조명.",
    "심플한 IT 일러스트": "미니멀한 IT 벡터 일러스트, 간결한 도형, 조화로운 블루 톤.",
    "카드뉴스 디자인": "한국어 SNS 카드뉴스 디자인. 제목과 핵심 문구를 읽기 좋게 배치하고 시각적 위계를 명확하게 구성.",
}
EXAMPLE_PROMPTS = [
    "표지: 저신용자 주택담보대출 LTV 80% 알아보기. 제목과 주택 캐릭터.",
    "2장: 대출 가능 여부에 영향을 주는 조건을 아이콘과 짧은 문구로 소개.",
    "3장: LTV 계산 방식과 예시를 그림으로 알기 쉽게 설명.",
    "4장: 신청할 때 확인할 서류와 심사 항목을 체크리스트로 표현.",
    "5장: 대출 전 금리·상환 부담·심사 조건을 확인하자는 마무리 카드.",
]

if "generated" not in st.session_state:
    st.session_state.generated = []
if "card_results" not in st.session_state:
    st.session_state.card_results = {}
if "remaining_images" not in st.session_state:
    st.session_state.remaining_images = 8
if "card_count" not in st.session_state:
    st.session_state.card_count = 5

with st.sidebar:
    st.header("API 연결")
    api_key = st.text_input(
        "본인의 OpenAI API 키", type="password",
        help="API 키는 GitHub에 올리지 마세요. 사용자별 API 키로 과금됩니다.",
    ).strip()
    st.caption("API 키는 코드나 다운로드 파일에 저장하지 않습니다.")
    st.divider()
    st.header("공통 생성 설정")
    model_label = st.selectbox("이미지 생성 GPT 모델", list(MODELS))
    model = MODELS[model_label]
    size = st.selectbox("이미지 크기", ["1536x1024", "1024x1024", "1024x1536", "auto"], index=1)
    quality = st.selectbox("품질", ["medium", "low", "high", "auto"])
    style = st.selectbox("스타일", list(STYLES))
    st.info("모델·계정에 따라 일부 크기/품질이 지원되지 않을 수 있습니다.")
    st.caption(f"현재 세션의 남은 생성 수량: {st.session_state.remaining_images} / 8장")


def make_prompt(description, card_number=None, common_instruction=""):
    parts = [description.strip()]
    if card_number is not None:
        parts.append(f"이 이미지는 연속 카드뉴스의 {card_number}번 카드입니다. 다른 카드의 내용을 섞지 말고 이 카드의 내용만 표현하세요.")
        parts.append("카드뉴스 한 장을 독립된 이미지 파일로 완성하세요. 여러 카드를 한 이미지에 나열하지 마세요.")
    if common_instruction.strip():
        parts.append("시리즈 공통 디자인 지침: " + common_instruction.strip())
    if STYLES[style]:
        parts.append(STYLES[style])
    return "\n\n".join(parts)


def generate_one(client, instruction):
    result = client.images.generate(
        model=model, prompt=instruction, size=size, quality=quality, n=1
    )
    if not result.data or not result.data[0].b64_json:
        raise ValueError("이미지 데이터가 반환되지 않았습니다. 모델을 변경하거나 다시 시도해 주세요.")
    return base64.b64decode(result.data[0].b64_json)


def create_client():
    return OpenAI(api_key=api_key, timeout=180.0, max_retries=1)


def zip_images(named_images):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in named_images:
            zf.writestr(name, content)
    return buffer.getvalue()


def show_gallery(named_images, prefix):
    for start in range(0, len(named_images), 2):
        columns = st.columns(2)
        for col, (filename, content) in zip(columns, named_images[start:start + 2]):
            with col:
                st.image(content, caption=filename, use_container_width=True)
                st.download_button(
                    "⬇ PNG 다운로드", content, file_name=filename,
                    mime="image/png", key=f"{prefix}_{filename}", use_container_width=True,
                )
    if len(named_images) > 1:
        st.download_button(
            "📦 전체 ZIP 다운로드", zip_images(named_images),
            file_name=f"{prefix}_{datetime.now():%Y%m%d}.zip",
            mime="application/zip", key=f"{prefix}_zip", use_container_width=True,
        )


def allowed(requested):
    if not api_key:
        st.error("사이드바에서 OpenAI API 키를 입력하세요.")
        return False
    if requested > st.session_state.remaining_images:
        st.error(f"남은 생성 한도가 {st.session_state.remaining_images}장입니다. 이 세션에서는 최대 8장까지 생성할 수 있어요.")
        return False
    return True


tab_single, tab_cards = st.tabs(["🖼️ 기존 이미지 생성", "🗂️ 카드뉴스 5장 일괄 생성"])

with tab_single:
    prompt = st.text_area(
        "이미지 생성 명령어",
        value="윈도우11에서 보안 검사 화면과 정상적인 라이선스 인증 상태를 나란히 보여주는 깔끔한 한국어 컴퓨터 화면 이미지",
        height=135, key="single_prompt",
    )
    count = st.number_input("같은 명령어로 생성할 장수", min_value=1, max_value=4, value=1, step=1)
    if st.button("✨ 이미지 생성하기", type="primary", use_container_width=True, key="single_generate"):
        if not prompt.strip():
            st.warning("이미지 설명을 입력하세요.")
        elif allowed(int(count)):
            client = create_client()
            images = []
            bar = st.progress(0)
            for i in range(int(count)):
                try:
                    content = generate_one(client, make_prompt(prompt))
                    name = f"gpt_image_{datetime.now():%Y%m%d_%H%M%S}_{i + 1:02d}.png"
                    images.append((name, content))
                    st.session_state.remaining_images -= 1
                except Exception as exc:
                    st.error(f"{i + 1}번 이미지 생성 실패: {exc}")
                    break
                finally:
                    bar.progress((i + 1) / int(count))
            if images:
                st.session_state.generated = images
                st.success(f"{len(images)}장 생성 완료")
    if st.session_state.generated:
        st.subheader("생성 결과")
        show_gallery(st.session_state.generated, "single")

with tab_cards:
    st.markdown("각 카드에 서로 다른 명령어를 입력하세요. 크기·모델·스타일은 사이드바에서 공통 설정합니다.")
    cards_count = st.slider("카드뉴스 장수", min_value=1, max_value=5, key="card_count")
    common = st.text_area(
        "공통 디자인 지침 (선택)",
        placeholder="예: 모든 카드에 동일한 파란색/흰색 배경, 귀여운 집 캐릭터, 선명한 한국어 글씨, 통일된 폰트 분위기",
        height=95, key="common_design",
    )
    prompts = []
    for i in range(cards_count):
        prompts.append(st.text_area(
            f"{i + 1}번 이미지 명령어", value=EXAMPLE_PROMPTS[i],
            height=100, key=f"card_prompt_{i + 1}",
        ))
    st.caption("예시 명령어는 자유롭게 지우고 수정할 수 있습니다. 각 카드는 별도 이미지 생성 요청으로 만들어집니다.")

    if st.button(f"✨ 서로 다른 카드뉴스 {cards_count}장 일괄 생성", type="primary", use_container_width=True):
        if any(not p.strip() for p in prompts):
            st.warning("생성할 카드의 명령어를 모두 입력하세요.")
        elif allowed(cards_count):
            client = create_client()
            # 이전 결과를 보존하여 실패한 이미지도 이후에 재시도 가능
            bar = st.progress(0)
            success = 0
            for i, p in enumerate(prompts, start=1):
                with st.spinner(f"{i}/{cards_count}번 카드 생성 중..."):
                    try:
                        image = generate_one(client, make_prompt(p, i, common))
                        st.session_state.card_results[i] = image
                        st.session_state.remaining_images -= 1
                        success += 1
                    except Exception as exc:
                        st.error(f"{i}번 카드 생성 실패: {exc}")
                    finally:
                        bar.progress(i / cards_count)
            if success:
                st.success(f"{success}장 생성 완료. 각 카드 이미지를 아래에서 확인할 수 있습니다.")

    if st.session_state.card_results:
        st.subheader("📸 카드뉴스 결과 및 개별 재생성")
        current = [(i, st.session_state.card_results[i]) for i in range(1, cards_count + 1) if i in st.session_state.card_results]
        for start in range(0, len(current), 2):
            columns = st.columns(2)
            for col, (i, content) in zip(columns, current[start:start + 2]):
                filename = f"cardnews_{i:02d}.png"
                with col:
                    st.markdown(f"**{i}번 카드**")
                    st.image(content, use_container_width=True)
                    st.download_button("⬇ PNG 저장", content, file_name=filename,
                                       mime="image/png", key=f"card_download_{i}", use_container_width=True)
                    if st.button(f"🔄 {i}번 카드만 다시 생성", key=f"regen_{i}", use_container_width=True):
                        if not prompts[i - 1].strip():
                            st.warning("해당 카드의 명령어를 입력하세요.")
                        elif allowed(1):
                            try:
                                with st.spinner(f"{i}번 카드 재생성 중..."):
                                    image = generate_one(create_client(), make_prompt(prompts[i - 1], i, common))
                                    st.session_state.card_results[i] = image
                                    st.session_state.remaining_images -= 1
                                st.rerun()
                            except Exception as exc:
                                st.error(f"{i}번 카드 재생성 실패: {exc}")
        named = [(f"cardnews_{i:02d}.png", img) for i, img in current]
        st.download_button(
            "📦 생성된 카드뉴스 ZIP 전체 다운로드", zip_images(named),
            file_name="cardnews_5series.zip", mime="application/zip",
            use_container_width=True, key="cards_zip",
        )
        st.caption("ZIP에는 현재 선택한 장수 범위에서 생성된 이미지만 포함됩니다.")
