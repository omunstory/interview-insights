"""Claude API를 사용해 인터뷰에서 마케팅 실행용 인사이트를 추출하는 모듈"""
import json
import urllib.request
from config import CLAUDE_API_KEY, PRODUCT_NAME, PRODUCT_DESC, TARGET_CUSTOMER

API_URL = "https://api.anthropic.com/v1/messages"


def _call_claude(prompt, max_tokens=4096):
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(API_URL, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read())
    return result["content"][0]["text"]


def extract_individual_insight(interview_title, interview_content, db_name):
    """개별 인터뷰에서 마케팅 실행용 인사이트 추출"""
    prompt = f"""당신은 실리콘밸리 마케팅 디렉터입니다. 랜딩페이지와 광고 카피를 바로 쓸 수 있는 인사이트를 추출합니다.

제품: {PRODUCT_NAME} ({PRODUCT_DESC})
타겟 고객: {TARGET_CUSTOMER}
데이터베이스: {db_name}
인터뷰 대상: {interview_title}

## 중요
- 이 문서는 인터뷰 진행자가 직접 작성한 것입니다. 질문 설계, 가이드라인, 메모, 실제 답변 등 **모든 내용이 분석 대상**입니다.
- **[답변]** 으로 시작하는 텍스트는 인터뷰이의 실제 답변입니다. 이것이 가장 중요한 데이터입니다.
- 고객이 겪는 구체적 고통 에피소드, 감정적/실질적 비용, 자발적 문제 언급을 집중적으로 찾으세요.

## 추출할 항목 (반드시 JSON 형식)

### 핵심 규칙: quote 필드는 **짧은 한 줄이 아니라 전체 맥락**을 포함하세요.
- 어떤 질문에 대한 답변인지
- 답변의 전후 문맥
- 감정이 담긴 표현 전부
- 원문을 최대한 길게 (3~5문장) 그대로 가져오세요

```json
{{
  "pain": [
    {{
      "point": "고통을 한 줄로 요약",
      "intensity": "상/중/하",
      "question": "이 답변을 이끌어낸 질문 또는 맥락",
      "quote": "원문 전체 맥락 (3~5문장, 질문에 대한 답변 전체를 가져오세요)",
      "emotion": "느껴지는 감정 (좌절/불안/분노/무력감 등)"
    }}
  ],
  "alternative": [
    {{"name": "현재 대안", "limit": "한계점", "quote": "원문 전체 맥락"}}
  ],
  "value": [
    {{"point": "인지된 가치", "quote": "원문 전체 맥락"}}
  ],
  "voice": [
    {{
      "text": "마케팅에 쓸 수 있는 핵심 원문 (1~2문장)",
      "full_context": "그 말이 나온 전체 맥락 (3~5문장)",
      "context": "어떤 상황에서 한 말인지"
    }}
  ],
  "price": [
    {{"data": "가격 관련 정보", "quote": "원문 전체 맥락"}}
  ],
  "trigger": [
    {{"moment": "전환 순간", "quote": "원문 전체 맥락"}}
  ],
  "objection": [
    {{"barrier": "구매 저항/망설임", "quote": "원문 전체 맥락"}}
  ],
  "before_after": {{
    "before": "사용 전 상태",
    "after": "사용 후 변화",
    "quote": "원문 전체 맥락"
  }},
  "profile": {{
    "followers": "팔로워 수",
    "purpose": "운영 목적",
    "urgency": "긴급도 점수",
    "spend_history": "지불 이력"
  }},
  "one_line": "이 인터뷰의 한 줄 핵심"
}}
```

데이터가 없는 항목은 빈 배열/null로. 추측 금지.

---
인터뷰 내용:
{interview_content}
"""
    return _call_claude(prompt, max_tokens=3000)


def extract_common_insights(all_individual_insights):
    """마케팅 실행용 종합 분석 — 바로 랜딩페이지를 쓸 수 있는 수준"""
    insights_text = ""
    for db_name, interviews in all_individual_insights.items():
        insights_text += f"\n\n## {db_name}\n"
        for interview in interviews:
            insights_text += f"\n### {interview['title']}\n{interview['insight']}\n"

    prompt = f"""당신은 실리콘밸리 마케팅 디렉터입니다. 이 분석을 보고 팀이 **바로 랜딩페이지, 광고, 세일즈 스크립트를 만들 수 있어야** 합니다.

제품: {PRODUCT_NAME} ({PRODUCT_DESC})
타겟 고객: {TARGET_CUSTOMER}
데이터베이스 세그먼트: {', '.join(all_individual_insights.keys())}

## 중요 컨텍스트
- 모든 인터뷰 문서는 진행자가 직접 작성. 질문 설계도 유효한 데이터.
- "데이터 부족"이라 판단하지 마세요. 제공된 모든 내용을 분석하세요.

## Part 1: ICP (Ideal Customer Profile)
인터뷰 데이터에서 **가장 돈을 쓸 가능성이 높고, 가장 아파하는** 고객 프로필을 정의하세요.
- 팔로워 규모
- 운영 목적 (수익/취미/브랜딩)
- 지불 이력 유무
- 긴급도 수준
- 대표 인물 (인터뷰이 중)
- ICP를 한 문장으로 정의

## Part 2: Pain → Gap → USP → Message
핵심 흐름을 최대 5개 도출하세요. 각각:

### USP N: [한 줄 메시지]
- **Pain**: 고객이 겪는 고통
- **Gap**: 현재 대안의 구멍
- **USP**: 우리가 메우는 차별점
- **Primary Message**: 고객 언어 기반 한 줄
- **뒷받침 인터뷰**: 누구(몇 명)
- **강도**: 확실/유망/가설

## Part 3: 메시징 매트릭스
아래 표를 채워주세요:

| 퍼널 단계 | 잠재고객 메시지 | 기존고객 메시지 | 핵심 고객 원문 |
|-----------|---------------|---------------|-------------|
| 인지(Awareness) | | | |
| 고려(Consideration) | | | |
| 전환(Decision) | | | |

## Part 4: 카피 키트 (바로 쓸 수 있는 문장)
### 인지 단계 (Awareness)
헤드라인 후보 3개 + 후킹 서브카피 3개. 고객 원문 기반.

### 고려 단계 (Consideration)
기능 가치 설명 3개 + 대안 비교 포인트 3개.

### 전환 단계 (Decision)
소셜프루프 3개 + CTA 문구 3개.

## Part 5: 구매 저항 & 반박
| 저항(Objection) | 근거 | 반박(Counter) | 반박 근거 |
|----------------|------|-------------|----------|

## Part 6: Before/After
사용 전후 변화 스토리. 실제 데이터 기반만.
| 구분 | Before (사용 전) | After (사용 후) | 고객 원문 |
|------|----------------|----------------|----------|

## Part 7: 가격 전략
- 확인된 지불 이력 (금액 + 누구)
- 세그먼트별 지불 의향 범위
- 가격 앵커 포인트
- 권장 가격 포지셔닝

## Part 8: 공통 발언 분석
### 8-1. 2명 이상이 같은 말을 한 것
같은 **의미**의 말을 한 사람들을 묶어주세요. 원문 그대로 나열.
| 공통 주제 | 언급자 (이름) | 각자의 원문 |
|----------|-------------|-----------|

### 8-2. 스트레스/긴급도 점수가 높은 사람들의 공통점
긴급도 7점 이상이거나, 감정 강도가 "상"인 사람들만 모아서:
- 공통 프로필 (팔로워 규모, 운영 기간, 목적)
- 공통 고통 패턴
- 공통 행동 패턴

## Part 9: 광고 카피 원문 (고객이 직접 한 말만)
**중요: 인터뷰어가 만든 질문이나 가이드라인은 절대 포함하지 마세요.**
**[답변] 태그가 붙은 실제 고객 발언만 사용하세요.**

### 9-1. 페인 포인트 카피 (고통/자기의심/좌절)
고객이 자기 능력을 의심하거나, 좌절하거나, 포기하고 싶었던 순간의 원문.
"나는 재능이 없나?", "게으른 쓰레기", "한심해질뿐" 같은 자기 의심과 감정적 고통이 담긴 문장을 찾으세요.
이런 문장은 광고에서 공감대를 형성하는 가장 강력한 소재입니다.

### 9-2. 와우 포인트 카피 (놀라움/만족/변화)
제품을 사용하고 나서, 또는 인사이트를 얻은 후의 긍정적 반응.
"이거 진짜 좋다", "몰랐던 걸 알게 됐다", "이제 편해졌다" 같은 변화의 순간.

### 9-3. 전체 카피 리스트
| 고객 원문 (그대로) | 누가 한 말 | 카피 유형 (페인/와우) | 추천 용도 (헤드라인/서브카피/CTA/소셜프루프/배너) | 왜 강력한지 |
|------------------|----------|-------------------|----------------------------------------------|----------|

최소 15개, 페인 카피 최소 8개 + 와우 카피 최소 5개 이상 골라주세요.
감정이 날것 그대로 드러나는 문장이 가장 좋습니다.

## Part 10: 미검증 가설 & 다음 인터뷰 질문
### 10-1. 아직 검증 안 된 가설
인터뷰에서 힌트는 있지만 아직 확실하지 않은 것들. 각각:
| 가설 | 근거 (힌트) | 왜 아직 미검증인지 | 검증 방법 |
|-----|----------|----------------|---------|

### 10-2. 다음 인터뷰에서 확인해야 할 질문 3개
각 질문에: 질문 원문, 왜 이걸 물어봐야 하는지, 어떤 답이 나오면 가설이 검증되는지

## 규칙
- 한국어
- 추측 아닌 데이터 기반만
- 인터뷰이 이름 표기
- 마크다운 테이블 사용

---
{insights_text}
"""
    return _call_claude(prompt, max_tokens=12000)
