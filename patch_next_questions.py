"""
다음 인터뷰 질문 파싱 버그 수정 패치
사용법: python3 patch_next_questions.py
"""
import os
import re
import sys

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_dashboard.py")

# 최종 새 코드 (정확히 이 블록이 들어 있으면 패치 완료로 간주)
NEW = """        # 10-2: 다음 질문
        # 섹션 본문만 떼어내서 헤더("질문 3개")가 매칭되지 않도록 함
        sec10_body = re.split(r'###?\\s*10-2[^\\n]*\\n', sec10, maxsplit=1)
        sec10_body = sec10_body[1] if len(sec10_body) > 1 else sec10
        # "1. **"질문"**", "Q1. ...", "질문 1: ..." 등 다양한 형식 지원
        q_pattern = re.findall(
            r'(?:^|\\n)\\s*(?:#{0,4}\\s*)?(?:Q\\s*)?\\d+\\s*[.):]\\s*\\*{0,2}["“]?\\s*(.+?)\\s*["”]?\\*{0,2}\\s*\\n(.*?)(?=(?:\\n\\s*(?:#{0,4}\\s*)?(?:Q\\s*)?\\d+\\s*[.):]|\\n##\\s*Part|\\Z))',
            sec10_body, re.DOTALL
        )
        for q_title, q_body in q_pattern:
            why_m = re.search(r'(?:왜|이유|필요)[^:：\\n]*[:：]\\s*(.*?)(?:\\n|$)', q_body)
            val_m = re.search(r'(?:검증|기준|답)[^:：\\n]*[:：]\\s*(.*?)(?:\\n|$)', q_body)
            result["next_questions"].append({
                "question": q_title.strip().strip('"').strip('"').strip('"'),
                "why": why_m.group(1).strip() if why_m else "",
                "validation": val_m.group(1).strip() if val_m else "",
            })"""

# # 10-2 부터 result["next_questions"].append({...}) 닫는 곳까지 통째로 교체
TARGET_RE = re.compile(
    r'        # 10-2: 다음 질문.*?result\["next_questions"\]\.append\(\{[^}]*\}\)',
    re.DOTALL,
)

def main():
    if not os.path.exists(PATH):
        print("❌ build_dashboard.py를 찾을 수 없습니다.")
        print("   이 스크립트를 interview-insights 폴더 안에 두고 실행하세요.")
        sys.exit(1)

    with open(PATH, "r", encoding="utf-8") as f:
        src = f.read()

    if NEW in src:
        print("✅ 이미 패치가 적용되어 있습니다. 추가 작업 필요 없음.")
        return

    if not TARGET_RE.search(src):
        print("⚠️  교체할 코드 영역을 찾지 못했습니다.")
        print("   build_dashboard.py 파일을 직접 새 버전으로 교체해 주세요.")
        sys.exit(1)

    backup = PATH + ".bak"
    with open(backup, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"📦 원본 백업: {backup}")

    new_src = TARGET_RE.sub(NEW, src, count=1)
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(new_src)

    print("✅ 패치 적용 완료.")
    print()
    print("다음 명령으로 대시보드를 다시 만들고 배포하세요:")
    print("   python3 build_dashboard.py")
    print("   firebase deploy --only hosting")

if __name__ == "__main__":
    main()
