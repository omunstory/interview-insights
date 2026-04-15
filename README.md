# 인터뷰 인사이트 대시보드

노션에 있는 고객 인터뷰를 자동으로 분석해서 USP 마케팅 대시보드를 만들어줍니다.

## 설치 (1분)

### 1. 다운로드
```bash
git clone https://github.com/omunstory/interview-insights.git
cd interview-insights
```

### 2. 설정
```bash
python3 setup.py
```

필요한 것:
- **Notion API 토큰** → [여기서 발급](https://www.notion.so/my-integrations)
- **Claude API 키** → [여기서 발급](https://console.anthropic.com)
- **노션 페이지 URL** → 인터뷰 데이터베이스가 있는 페이지

### 3. 실행
```bash
python3 main.py --force   # 첫 실행 (전체 분석, 3~5분)
open index.html            # 대시보드 열기
```

## 사용법

```bash
python3 main.py            # 변경된 인터뷰만 업데이트
python3 main.py --force    # 전체 재분석
python3 build_dashboard.py # 대시보드만 재빌드
```

## 노션 페이지 구조

인터뷰 페이지 안에 데이터베이스가 있어야 합니다:

```
📄 인터뷰 페이지
 ├── 📊 DB: 기존 고객 인터뷰
 │    ├── 인터뷰 1
 │    └── 인터뷰 2
 ├── 📊 DB: 잠재고객 인터뷰
 │    ├── 인터뷰 3
 │    └── ...
 └── 📊 DB: 얼리버드 인터뷰
```

## 대시보드 구성

| 탭 | 설명 |
|---|---|
| 핵심 요약 | ICP + Primary USP + 메시징 매트릭스 |
| 고객 고통 원문 | 날것 그대로의 고객 텍스트 (필터 가능) |
| Pain→USP→Message | Pain-Gap-USP-Message 흐름도 |
| 카피 키트 | 인지/고려/전환 단계별 바로 쓸 수 있는 카피 |
| 저항 & Before/After | 구매 저항과 반박, 사용 전후 변화 |
| 가격 전략 | 지불 이력, 의향, 포지셔닝 |
| 개별 인터뷰 | 인터뷰별 상세 (노션 링크 포함) |
