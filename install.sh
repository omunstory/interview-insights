#!/bin/bash
# 인터뷰 인사이트 대시보드 — 원클릭 설치
# 사용법: 터미널에 아래 한 줄 붙여넣기
# curl -sL https://raw.githubusercontent.com/omunstory/interview-insights/main/install.sh | bash

set -e

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   인터뷰 인사이트 대시보드 설치               ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# 설치 경로
INSTALL_DIR="$HOME/interview-insights"

if [ -d "$INSTALL_DIR" ]; then
    echo "  이미 설치되어 있어요. 업데이트할게요..."
    cd "$INSTALL_DIR"
    git pull origin main 2>/dev/null || true
else
    echo "  다운로드 중..."
    git clone https://github.com/omunstory/interview-insights.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo ""
echo "  설치 완료! 이제 설정을 시작할게요."
echo ""

python3 setup.py
