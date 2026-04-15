"""Notion API를 통해 인터뷰 페이지 내용을 읽는 모듈 (고도화 버전)"""
import json
import time
import urllib.request
from config import NOTION_TOKEN, DATABASES, EXCLUDE_PAGE_IDS

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# Notion API rate limit: 3 requests/second
_last_request_time = 0


def _api_get(url):
    """GET 요청 + rate limit + 재시도"""
    global _last_request_time
    # Rate limit: 최소 0.35초 간격
    elapsed = time.time() - _last_request_time
    if elapsed < 0.35:
        time.sleep(0.35 - elapsed)

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            _last_request_time = time.time()
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt < 2:
                wait = (attempt + 1) * 2
                print(f"    [재시도 {attempt+1}/3] {str(e)[:60]}... {wait}초 대기")
                time.sleep(wait)
            else:
                print(f"    [실패] {url[-40:]}: {str(e)[:80]}")
                return {"results": []}


def _api_post(url, data=None):
    """POST 요청 + rate limit + 재시도"""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < 0.35:
        time.sleep(0.35 - elapsed)

    body = json.dumps(data or {}).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=body, headers=HEADERS, method="POST")
            _last_request_time = time.time()
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt < 2:
                wait = (attempt + 1) * 2
                print(f"    [재시도 {attempt+1}/3] {str(e)[:60]}... {wait}초 대기")
                time.sleep(wait)
            else:
                print(f"    [실패] POST {url[-40:]}: {str(e)[:80]}")
                return {"results": []}


def _extract_rich_text(rich_text_list):
    return "".join(t.get("plain_text", "") for t in rich_text_list)


def get_database_entries(db_id):
    """데이터베이스의 모든 항목(페이지) 목록 반환 (페이지네이션 지원)"""
    entries = []
    has_more = True
    start_cursor = None

    while has_more:
        payload = {}
        if start_cursor:
            payload["start_cursor"] = start_cursor

        url = f"https://api.notion.com/v1/databases/{db_id}/query"
        result = _api_post(url, payload)

        for page in result.get("results", []):
            page_id = page["id"].replace("-", "")
            if page_id in [eid.replace("-", "") for eid in EXCLUDE_PAGE_IDS]:
                continue

            # 제목 추출: title 속성 → 없으면 첫 번째 heading에서 추출 시도
            title_prop = page["properties"].get("이름", {}).get("title", [])
            title = title_prop[0]["plain_text"] if title_prop else ""

            # 제목이 이모지만이거나 비어있으면 페이지 내용에서 제목 추출
            clean_title = title.replace("🟢", "").replace("🔴", "").replace("🟡", "").strip()
            if len(clean_title) < 2:
                title = _extract_title_from_page(page["id"]) or title or "(제목 없음)"

            entries.append({
                "id": page["id"],
                "title": title,
                "last_edited": page["last_edited_time"],
            })

        has_more = result.get("has_more", False)
        start_cursor = result.get("next_cursor")

    return entries


def _extract_title_from_page(page_id):
    """페이지 테이블에서 참여자 이름 추출 (우선), 없으면 heading에서 추출"""
    result = _api_get(f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=20")
    blocks = result.get("results", [])

    # 1순위: 테이블에서 참여자/이름 찾기
    for block in blocks:
        if block["type"] == "table" and block.get("has_children"):
            table_text = _read_table_rows(block["id"])
            for line in table_text.split("\n"):
                if "참여자" in line or ("이름" in line and "파일" not in line):
                    parts = line.split("|")
                    if len(parts) >= 2:
                        name = parts[1].strip()
                        if name and name not in ("내용", ""):
                            return f"잠재고객 인터뷰 - {name}"

    # 2순위: heading에서 제목 추출
    for block in blocks:
        bt = block["type"]
        if bt in ("heading_1", "heading_2"):
            text = _extract_rich_text(block[bt].get("rich_text", []))
            if text.strip():
                return text.strip()

    return None


def _read_table_rows(block_id):
    """테이블 블록의 행들을 텍스트로 변환"""
    children = _api_get(f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100")
    rows = []
    for row_block in children.get("results", []):
        if row_block["type"] == "table_row":
            cells = row_block["table_row"]["cells"]
            cell_texts = [_extract_rich_text(cell) for cell in cells]
            rows.append(" | ".join(cell_texts))
    return "\n".join(rows)


# 지원하는 텍스트 블록 타입과 접두사
TEXT_BLOCKS = {
    "paragraph": "",
    "heading_1": "# ",
    "heading_2": "## ",
    "heading_3": "### ",
    "bulleted_list_item": "- ",
    "numbered_list_item": "1. ",
    "quote": "> ",
    "callout": "💡 ",
    "to_do": "☐ ",
    "toggle": "",
    "code": "[답변] ",
}

# 하위 블록을 가질 수 있는 컨테이너 블록
CONTAINER_BLOCKS = {"column_list", "column", "synced_block", "template"}


def _read_blocks_recursive(block_id, depth=0):
    """블록의 모든 하위 블록을 재귀적으로 텍스트로 변환 (최대 5단계)"""
    if depth > 5:
        return []

    # 페이지네이션: 100개 이상 블록도 모두 읽기
    all_blocks = []
    has_more = True
    start_cursor = None

    while has_more:
        url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100"
        if start_cursor:
            url += f"&start_cursor={start_cursor}"

        result = _api_get(url)
        all_blocks.extend(result.get("results", []))
        has_more = result.get("has_more", False)
        start_cursor = result.get("next_cursor")

    lines = []
    for block in all_blocks:
        block_type = block["type"]

        # 테이블
        if block_type == "table":
            table_text = _read_table_rows(block["id"])
            if table_text.strip():
                lines.append(f"[표]\n{table_text}")

        # 텍스트 블록 (paragraph, heading, code, toggle 등)
        elif block_type in TEXT_BLOCKS:
            rich_text = block[block_type].get("rich_text", [])
            text = _extract_rich_text(rich_text)
            if text.strip():
                prefix = TEXT_BLOCKS[block_type]
                lines.append(f"{prefix}{text}")

            # 하위 블록 재귀 읽기
            if block.get("has_children"):
                child_lines = _read_blocks_recursive(block["id"], depth + 1)
                lines.extend(child_lines)

        # 구분선
        elif block_type == "divider":
            lines.append("---")

        # 컨테이너 블록 (column_list, synced_block 등)
        elif block_type in CONTAINER_BLOCKS and block.get("has_children"):
            child_lines = _read_blocks_recursive(block["id"], depth + 1)
            lines.extend(child_lines)

        # child_page: 하위 페이지도 읽기 (depth 제한 적용)
        elif block_type == "child_page" and depth < 2:
            page_title = block["child_page"].get("title", "")
            lines.append(f"\n## [하위 페이지] {page_title}")
            child_lines = _read_blocks_recursive(block["id"], depth + 1)
            lines.extend(child_lines)

        # embed/bookmark/link_preview: URL 추출
        elif block_type in ("embed", "bookmark", "link_preview"):
            url_val = ""
            if block_type == "embed":
                url_val = block["embed"].get("url", "")
            elif block_type == "bookmark":
                url_val = block["bookmark"].get("url", "")
                caption = _extract_rich_text(block["bookmark"].get("caption", []))
                if caption:
                    lines.append(f"[링크] {caption}: {url_val}")
                    continue
            elif block_type == "link_preview":
                url_val = block["link_preview"].get("url", "")
            if url_val:
                lines.append(f"[링크] {url_val}")

        # file/image/video/audio/pdf: 파일 URL 추출
        elif block_type in ("file", "image", "video", "audio", "pdf"):
            file_data = block[block_type]
            file_url = ""
            if file_data.get("type") == "file":
                file_url = file_data.get("file", {}).get("url", "")
            elif file_data.get("type") == "external":
                file_url = file_data.get("external", {}).get("url", "")
            caption = _extract_rich_text(file_data.get("caption", []))
            if file_url or caption:
                label = caption if caption else block_type
                lines.append(f"[{block_type}] {label}")

        # 알 수 없는 블록: 경고만 (조용히 무시하지 않음)
        elif block_type not in ("divider", "table_of_contents", "breadcrumb", "child_database"):
            if block.get("has_children"):
                child_lines = _read_blocks_recursive(block["id"], depth + 1)
                lines.extend(child_lines)

    return lines


def read_page_content(page_id):
    """페이지의 모든 블록을 텍스트로 변환 (하위 블록, 페이지네이션 포함)"""
    lines = _read_blocks_recursive(page_id)
    return "\n".join(lines)


def get_all_interviews():
    """모든 데이터베이스에서 인터뷰 목록과 내용을 읽어옴"""
    all_interviews = {}

    for db_name, db_id in DATABASES.items():
        entries = get_database_entries(db_id)
        interviews = []
        for entry in entries:
            content = read_page_content(entry["id"])
            interviews.append({
                "id": entry["id"],
                "title": entry["title"],
                "last_edited": entry["last_edited"],
                "content": content,
            })
        all_interviews[db_name] = interviews
        print(f"  [{db_name}] {len(interviews)}개 인터뷰 로드 완료")

    return all_interviews
