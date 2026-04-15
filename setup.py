#!/usr/bin/env python3
"""
인터뷰 인사이트 대시보드 — 초기 설정
다른 사람이 자기 노션/API로 쓸 수 있도록 설정하는 스크립트
"""
import os
import sys
import json
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

print("""
╔══════════════════════════════════════════════╗
║   인터뷰 인사이트 대시보드 — 초기 설정        ║
╚══════════════════════════════════════════════╝
""")

# 1. Notion Token
print("━━━ 1/3: Notion API 토큰 ━━━")
print()
print("  발급 방법:")
print("  1) https://www.notion.so/my-integrations 접속")
print("  2) '새 API 통합' 클릭 → 이름 입력 → 제출")
print("  3) 'Internal Integration Secret' 복사 (ntn_ 으로 시작)")
print("  4) 인터뷰 페이지에서 ··· → 연결 → 방금 만든 integration 추가")
print()
notion_token = input("  Notion 토큰 입력: ").strip()
if not notion_token:
    print("  ❌ 토큰이 필요합니다.")
    sys.exit(1)

# 2. Claude API Key
print()
print("━━━ 2/3: Claude API 키 ━━━")
print()
print("  발급 방법:")
print("  1) https://console.anthropic.com 접속")
print("  2) API Keys → Create Key")
print("  3) 키 복사 (sk-ant- 으로 시작)")
print()
claude_key = input("  Claude API 키 입력: ").strip()
if not claude_key:
    print("  ❌ API 키가 필요합니다.")
    sys.exit(1)

# 3. Notion Page ID
print()
print("━━━ 3/3: 노션 인터뷰 페이지 ━━━")
print()
print("  인터뷰 데이터베이스가 있는 노션 페이지 URL을 붙여넣으세요.")
print("  예: https://www.notion.so/myworkspace/3179992dd40e8068adade20424bb240d")
print()
page_input = input("  노션 페이지 URL 또는 ID: ").strip()

# URL에서 ID 추출
page_id = page_input
if "notion.so" in page_input:
    # URL에서 마지막 32자리 hex 추출
    import re
    m = re.search(r'([a-f0-9]{32})', page_input.replace("-", ""))
    if m:
        page_id = m.group(1)
    else:
        print("  ❌ URL에서 페이지 ID를 찾을 수 없습니다.")
        sys.exit(1)

page_id = page_id.replace("-", "")
if len(page_id) != 32:
    print(f"  ❌ 페이지 ID가 올바르지 않습니다 ({len(page_id)}자, 32자 필요)")
    sys.exit(1)

# 연결 테스트
print()
print("  연결 테스트 중...")
headers = {
    "Authorization": f"Bearer {notion_token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

try:
    req = urllib.request.Request(
        f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100",
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
except Exception as e:
    print(f"  ❌ 노션 연결 실패: {e}")
    print()
    print("  확인할 것:")
    print("  - 토큰이 정확한지")
    print("  - 해당 페이지에 integration이 연결되어 있는지")
    sys.exit(1)

# 데이터베이스 자동 탐지
databases = {}
exclude_ids = []
for block in data.get("results", []):
    if block["type"] == "child_database":
        db_id = block["id"].replace("-", "")
        db_title = block["child_database"]["title"]
        databases[db_title] = db_id
        print(f"  ✅ 데이터베이스 발견: {db_title}")

if not databases:
    print("  ⚠️  데이터베이스를 찾지 못했습니다. 페이지 ID를 확인해주세요.")
    sys.exit(1)

# 4. 제품 정보
print()
print("━━━ 4/5: 제품 정보 ━━━")
print()
print("  분석할 제품/서비스 정보를 입력하세요.")
print("  (인터뷰가 어떤 제품에 대한 것인지)")
print()
product_name = input("  제품 이름 (예: 요리 레시피 앱): ").strip()
if not product_name:
    product_name = "내 제품"
product_desc = input("  제품 설명 (예: AI 기반 맞춤 레시피 추천): ").strip()
if not product_desc:
    product_desc = ""
target_customer = input("  타겟 고객 (예: 요리 초보 직장인): ").strip()
if not target_customer:
    target_customer = ""

print(f"  ✅ {product_name}")

# Claude API 테스트
print()
print("  Claude API 테스트 중...")
try:
    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 20,
        "messages": [{"role": "user", "content": "Hi"}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": claude_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        json.loads(resp.read())
    print("  ✅ Claude API 연결 성공")
except Exception as e:
    print(f"  ❌ Claude API 연결 실패: {e}")
    sys.exit(1)

# 제외할 페이지 확인
print()
print("  인터뷰가 아닌 항목이 있으면 제외합니다.")
print("  (데이터베이스 안에 '인사이트 정리', '감사 페이지' 등)")
print()

for db_name, db_id in databases.items():
    try:
        body = json.dumps({}).encode()
        req = urllib.request.Request(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            data=body, headers=headers, method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            db_data = json.loads(resp.read())
        print(f"  [{db_name}]")
        for page in db_data.get("results", []):
            title_prop = page["properties"].get("이름", {}).get("title", [])
            title = title_prop[0]["plain_text"] if title_prop else "(제목 없음)"
            print(f"    - {title}")
    except:
        pass

print()
exclude_input = input("  제외할 페이지 ID가 있으면 입력 (쉼표로 구분, 없으면 Enter): ").strip()
if exclude_input:
    exclude_ids = [eid.strip().replace("-", "") for eid in exclude_input.split(",")]

# config.py 생성
print()
print("  설정 파일 생성 중...")

db_dict_str = "{\n"
for name, did in databases.items():
    db_dict_str += f'    "{name}": "{did}",\n'
db_dict_str += "}"

exclude_str = "[\n"
for eid in exclude_ids:
    exclude_str += f'    "{eid}",\n'
exclude_str += "]"

config_content = f'''NOTION_TOKEN = "{notion_token}"
CLAUDE_API_KEY = "{claude_key}"

PAGE_ID = "{page_id}"

DATABASES = {db_dict_str}

# 인터뷰가 아닌 항목 제외
EXCLUDE_PAGE_IDS = {exclude_str}

# 제품 정보 (프롬프트에 자동 반영)
PRODUCT_NAME = "{product_name}"
PRODUCT_DESC = "{product_desc}"
TARGET_CUSTOMER = "{target_customer}"
'''

config_path = os.path.join(SCRIPT_DIR, "config.py")
with open(config_path, "w") as f:
    f.write(config_content)

print(f"  ✅ config.py 생성 완료")

# 첫 실행
print()
print("━━━ 설정 완료! ━━━")
print()
print(f"  데이터베이스: {len(databases)}개")
print(f"  제외 항목: {len(exclude_ids)}개")
print()

run_now = input("  지금 바로 첫 분석을 실행할까요? (y/n): ").strip().lower()
if run_now == "y":
    print()
    print("  첫 분석을 시작합니다... (3~5분 소요)")
    print()
    os.system(f"cd {SCRIPT_DIR} && python3 main.py --force")
    print()
    print(f"  ✅ 대시보드 생성 완료!")
    print(f"  열기: open {os.path.join(SCRIPT_DIR, 'index.html')}")
else:
    print()
    print("  나중에 실행하려면:")
    print(f"    cd {SCRIPT_DIR}")
    print("    python3 main.py --force")
    print()
    print("  대시보드 열기:")
    print(f"    open {os.path.join(SCRIPT_DIR, 'index.html')}")

print()
print("  이후 업데이트:")
print("    python3 main.py          # 변경분만 분석")
print("    python3 main.py --force   # 전체 재분석")
print()
