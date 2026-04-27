"""
다음 인터뷰 질문 파싱 버그 수정 패치
사용법: python3 patch_next_questions.py
"""
import os
import sys

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_dashboard.py")

OLD = """        # 10-2: 다음 질문
        q_pattern = re.findall(
            r'(?:###?\\s*)?(?:Q\\d+|질문\\s*\\d+)[.:]?\\s*(.*?)\\n(.*?)(?=(?:###?\\s*(?:Q\\d+|질문)|## Part|$))',
            sec10, re.DOTALL
        )"""

NEW = """        # 10-2: 다음 질문
        # 섹션 본문만 떼어내서 헤더("질문 3개")가 매칭되지 않도록 함
        sec10_body = re.split(r'###?\\s*10-2[^\\n]*\\n', sec10, maxsplit=1)
        sec10_body = sec10_body[1] if len(sec10_body) > 1 else sec10
        q_pattern = re.findall(
            r'(?:^|\\n)#{0,4}\\s*(?:Q\\s*\\d+|질문\\s*\\d+)\\s*[.:)]\\s*(.*?)\\n(.*?)(?=(?:\\n#{0,4}\\s*(?:Q\\s*\\d+|질문\\s*\\d+)\\s*[.:)]|\\n##\\s*Part|\\Z))',
            sec10_body, re.DOTALL
        )"""

def main():
    if not os.path.exists(PATH):
        print("❌ build_dashboard.py를 찾을 수 없습니다.")
        print(f"   이 스크립트를 interview-insights 폴더 안에 두고 실행하세요.")
        sys.exit(1)

    with open(PATH, "r", encoding="utf-8") as f:
        src = f.read()

    if NEW in src:
        print("✅ 이미 패치가 적용되어 있습니다. 추가 작업 필요 없음.")
        return

    if OLD not in src:
        print("⚠️  원본 코드와 일치하는 부분을 찾지 못했습니다.")
        print("   build_dashboard.py 파일을 직접 새 버전으로 교체해 주세요.")
        sys.exit(1)

    backup = PATH + ".bak"
    with open(backup, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"📦 원본 백업: {backup}")

    src = src.replace(OLD, NEW)
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)

    print("✅ 패치 적용 완료.")
    print()
    print("다음 명령으로 대시보드를 다시 만들고 배포하세요:")
    print("   python3 build_dashboard.py")
    print("   firebase deploy --only hosting")

if __name__ == "__main__":
    main()
