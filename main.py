#!/usr/bin/env python3
"""
인터뷰 인사이트 자동 추출 프로그램
- 노션에서 인터뷰 읽기
- Claude API로 인사이트 추출
- 노션 페이지 상단에 결과 작성
"""
import sys
import json
import os
from datetime import datetime

from notion_reader import get_all_interviews
from insight_extractor import extract_individual_insight, extract_common_insights
from notion_writer import write_insights_to_notion

CACHE_FILE = os.path.join(os.path.dirname(__file__), ".insight_cache.json")


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def run(force=False):
    print("=" * 50)
    print("인터뷰 인사이트 추출기")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # 1. 노션에서 인터뷰 읽기
    print("\n[1/4] 노션에서 인터뷰 로드 중...")
    all_interviews = get_all_interviews()

    total = sum(len(v) for v in all_interviews.values())
    print(f"  총 {total}개 인터뷰 발견")

    # 2. 캐시 확인 (변경된 것만 재분석)
    cache = load_cache()
    needs_update = force

    # 3. 개별 인사이트 추출
    print("\n[2/4] 개별 인사이트 추출 중...")
    all_individual_insights = {}

    for db_name, interviews in all_interviews.items():
        db_insights = []
        for interview in interviews:
            cache_key = interview["id"]
            cached = cache.get(cache_key, {})

            if (
                not force
                and cached.get("last_edited") == interview["last_edited"]
                and cached.get("insight")
            ):
                print(f"  [캐시] {interview['title']}")
                insight = cached["insight"]
            else:
                print(f"  [분석] {interview['title']}...")
                try:
                    insight = extract_individual_insight(
                        interview["title"],
                        interview["content"],
                        db_name,
                    )
                    cache[cache_key] = {
                        "last_edited": interview["last_edited"],
                        "insight": insight,
                        "title": interview["title"],
                    }
                    needs_update = True
                except Exception as e:
                    print(f"    오류: {e}")
                    insight = f"분석 실패: {str(e)[:200]}"

            db_insights.append({
                "title": interview["title"],
                "insight": insight,
            })

        all_individual_insights[db_name] = db_insights

    save_cache(cache)

    # 4. 공통 인사이트 추출
    print("\n[3/4] 공통 인사이트 분석 중...")
    if needs_update or "common" not in cache:
        common_insights = extract_common_insights(all_individual_insights)
        cache["common"] = {
            "insight": common_insights,
            "updated": datetime.now().isoformat(),
        }
        save_cache(cache)
    else:
        print("  [캐시] 변경 없음, 캐시 사용")
        common_insights = cache["common"]["insight"]

    # 5. 노션에 작성
    print("\n[4/5] 노션에 인사이트 작성 중...")
    write_insights_to_notion(all_individual_insights, common_insights)

    # 6. 웹 대시보드 빌드
    print("\n[5/5] 웹 대시보드 생성 중...")
    from build_dashboard import build_dashboard
    dashboard_path = build_dashboard()

    print(f"\n완료! 대시보드: file://{dashboard_path}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    run(force=force)
