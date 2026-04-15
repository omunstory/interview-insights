"""인사이트 결과를 노션 페이지에 작성하는 모듈"""
import json
import urllib.request
import time
from datetime import datetime
from config import NOTION_TOKEN, PAGE_ID

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def _api_request(url, method="GET", data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _api_patch(url, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=HEADERS, method="PATCH")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _make_rich_text(text):
    """텍스트를 Notion rich_text 배열로 변환 (2000자 제한 처리)"""
    chunks = []
    while text:
        chunks.append({"type": "text", "text": {"content": text[:2000]}})
        text = text[2000:]
    return chunks


def _make_heading(text, level=1):
    key = f"heading_{level}"
    return {"object": "block", "type": key, key: {"rich_text": _make_rich_text(text)}}


def _make_paragraph(text):
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _make_rich_text(text)}}


def _make_divider():
    return {"object": "block", "type": "divider", "divider": {}}


def _make_toggle(title, children_texts):
    """토글 블록 생성"""
    children = [_make_paragraph(t) for t in children_texts if t.strip()]
    return {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": _make_rich_text(title),
            "children": children[:100],
        },
    }


def _markdown_to_blocks(markdown_text):
    """마크다운 텍스트를 Notion 블록들로 변환"""
    blocks = []
    lines = markdown_text.split("\n")
    current_paragraph = []

    def flush_paragraph():
        if current_paragraph:
            text = "\n".join(current_paragraph).strip()
            if text:
                blocks.append(_make_paragraph(text))
            current_paragraph.clear()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            flush_paragraph()
            blocks.append(_make_heading(stripped[4:], 3))
        elif stripped.startswith("## "):
            flush_paragraph()
            blocks.append(_make_heading(stripped[3:], 2))
        elif stripped.startswith("# "):
            flush_paragraph()
            blocks.append(_make_heading(stripped[2:], 1))
        elif stripped == "---":
            flush_paragraph()
            blocks.append(_make_divider())
        elif stripped == "":
            flush_paragraph()
        else:
            current_paragraph.append(line)

    flush_paragraph()
    return blocks


def _delete_old_insight_blocks(page_id):
    """기존 인사이트 블록들만 삭제 (데이터베이스, child_page, 빈 paragraph 보존)"""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
    result = _api_request(url)

    preserved_types = {"child_database", "child_page"}
    deleted = 0

    for block in result.get("results", []):
        if block["type"] in preserved_types:
            continue

        # 빈 paragraph는 데이터베이스 사이 스페이서일 수 있으므로 보존
        if block["type"] == "paragraph":
            texts = block["paragraph"].get("rich_text", [])
            text = "".join(t["plain_text"] for t in texts)
            if not text.strip():
                continue

        try:
            _api_request(f"https://api.notion.com/v1/blocks/{block['id']}", method="DELETE")
            deleted += 1
        except Exception:
            pass

    print(f"  {deleted}개 기존 블록 삭제 완료")


def _append_blocks(page_id, blocks):
    """블록들을 페이지에 추가 (Notion API 제한 고려, 개별 추가)"""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    success = 0
    fail = 0

    # 50개씩 묶어서 추가
    for i in range(0, len(blocks), 50):
        chunk = blocks[i:i + 50]
        try:
            _api_patch(url, {"children": chunk})
            success += len(chunk)
        except Exception as e:
            # 묶음 실패 시 개별 추가
            for block in chunk:
                try:
                    _api_patch(url, {"children": [block]})
                    success += 1
                except Exception:
                    fail += 1
        time.sleep(0.3)  # Rate limit 대응

    print(f"  블록 추가: {success}개 성공, {fail}개 실패")


def write_insights_to_notion(individual_insights, common_insights):
    """인사이트를 노션 페이지에 작성"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 1. 기존 인사이트 블록 삭제
    print("  기존 인사이트 블록 삭제 중...")
    _delete_old_insight_blocks(PAGE_ID)

    # 2. 블록 구성
    blocks = []

    # 헤더
    blocks.append(_make_heading("고객 인터뷰 핵심 인사이트 대시보드", 1))
    blocks.append(_make_paragraph(f"마지막 업데이트: {now}"))
    blocks.append(_make_divider())

    # 공통 인사이트
    blocks.append(_make_heading("전체 공통 인사이트", 2))
    blocks.extend(_markdown_to_blocks(common_insights))
    blocks.append(_make_divider())

    # 개별 인사이트 (토글로 접기)
    blocks.append(_make_heading("개별 인터뷰 인사이트", 2))

    for db_name, interviews in individual_insights.items():
        blocks.append(_make_heading(db_name, 3))
        for interview in interviews:
            insight_lines = interview["insight"].split("\n")
            content_chunks = []
            current_chunk = []
            for line in insight_lines:
                current_chunk.append(line)
                if len("\n".join(current_chunk)) > 1800:
                    content_chunks.append("\n".join(current_chunk))
                    current_chunk = []
            if current_chunk:
                content_chunks.append("\n".join(current_chunk))

            if content_chunks:
                blocks.append(_make_toggle(interview["title"], content_chunks))

    blocks.append(_make_divider())

    # 3. 블록 추가
    print(f"  총 {len(blocks)}개 블록 작성 중...")
    _append_blocks(PAGE_ID, blocks)

    print(f"  노션 작성 완료! ({now})")
