#!/usr/bin/env python3
"""노션 변경 감지 → 변경 있을 때만 분석 실행"""
import json
import os
import time
import subprocess
from datetime import datetime
from notion_reader import get_database_entries
from config import DATABASES

STATE_FILE = os.path.join(os.path.dirname(__file__), ".last_state.json")
LOG_FILE = os.path.join(os.path.dirname(__file__), "watch.log")


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def check_changes():
    """노션에서 현재 상태를 읽고, 이전과 비교하여 변경 여부 반환"""
    old_state = load_state()
    new_state = {}
    changed = []

    for db_name, db_id in DATABASES.items():
        try:
            entries = get_database_entries(db_id)
        except Exception as e:
            log(f"  DB 읽기 실패 ({db_name}): {e}")
            continue

        for entry in entries:
            key = entry["id"]
            new_state[key] = {
                "title": entry["title"],
                "last_edited": entry["last_edited"],
            }
            old = old_state.get(key, {})
            if old.get("last_edited") != entry["last_edited"]:
                changed.append(entry["title"])

    # 새로 추가된 항목 체크
    new_keys = set(new_state.keys()) - set(old_state.keys())
    for key in new_keys:
        if new_state[key]["title"] not in changed:
            changed.append(f"[신규] {new_state[key]['title']}")

    save_state(new_state)
    return changed


def run_analysis():
    """main.py 실행 (변경분만 분석) + Firebase 배포"""
    project_dir = os.path.dirname(__file__)
    script = os.path.join(project_dir, "main.py")

    # 1. 분석 실행
    result = subprocess.run(
        ["python3", script],
        capture_output=True, text=True, timeout=600,
        cwd=project_dir,
    )
    if result.returncode == 0:
        log("  분석 완료")
    else:
        log(f"  분석 오류: {result.stderr[-200:]}")
        return

    # 2. Firebase 배포 (설치되어 있는 경우만)
    import shutil
    firebase_path = shutil.which("firebase")
    if not firebase_path:
        # 일반적인 설치 경로도 확인
        for path in [os.path.expanduser("~/.local/bin/firebase"), "/usr/local/bin/firebase"]:
            if os.path.isfile(path):
                firebase_path = path
                break

    if firebase_path:
        deploy = subprocess.run(
            [firebase_path, "deploy", "--only", "hosting"],
            capture_output=True, text=True, timeout=120,
            cwd=project_dir,
        )
        if deploy.returncode == 0:
            log("  Firebase 배포 완료")
        else:
            log(f"  Firebase 배포 오류: {deploy.stderr[-200:]}")
    else:
        log("  Firebase 미설치 — 로컬 대시보드만 업데이트됨")


def main():
    log("변경 감지 체크 시작")
    changed = check_changes()

    if changed:
        log(f"  변경 감지: {len(changed)}개 — {', '.join(changed[:5])}")
        run_analysis()
    else:
        log("  변경 없음 — 스킵")


if __name__ == "__main__":
    main()
