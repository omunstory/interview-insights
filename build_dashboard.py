#!/usr/bin/env python3
"""마케팅 실행용 대시보드 빌더"""
import json
import re
import os
from datetime import datetime
from config import DATABASES
from notion_reader import get_database_entries

CACHE = os.path.join(os.path.dirname(__file__), ".insight_cache.json")
TMPL = os.path.join(os.path.dirname(__file__), "dashboard.html")
OUT = os.path.join(os.path.dirname(__file__), "index.html")
SHORT = {"1차 제품 개선":"기존","(잠재 고객)지옥 캠프":"잠재","(얼리버드 고객)지옥 캠프":"얼리버드"}


def load_cache():
    with open(CACHE) as f: return json.load(f)


def parse_json_from_text(text):
    m = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    m = re.search(r'\{[^{}]*"pain".*\}', text, re.DOTALL)
    if m:
        try: return json.loads(m.group())
        except: pass
    return None


def _tbl(section):
    """Parse markdown table from section text"""
    lines = [l.strip() for l in section.split('\n') if l.strip().startswith('|')]
    if len(lines) < 3: return []
    headers = [h.strip().strip('*') for h in lines[0].split('|')[1:-1]]
    rows = []
    for line in lines[2:]:
        cells = [c.strip().strip('*') for c in line.split('|')[1:-1]]
        if len(cells) >= len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def _sec(text, part_num):
    """Extract Part N section"""
    pattern = rf'Part {part_num}.*?(?=##\s*Part \d|$)'
    m = re.search(pattern, text, re.DOTALL)
    return m.group() if m else ""


def _md2html(text):
    out = []
    for line in text.split('\n'):
        s = line.strip()
        if not s: continue
        if s.startswith('### '): out.append(f'<h4 style="margin:12px 0 5px;font-size:13px;font-weight:700">{s[4:]}</h4>')
        elif s.startswith('- ') or s.startswith('• '):
            p = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', s[2:])
            out.append(f'<div style="font-size:12.5px;margin:2px 0;padding-left:10px">• {p}</div>')
        elif re.match(r'\d+\.', s):
            p = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', re.sub(r'^\d+\.\s*', '', s))
            out.append(f'<div style="font-size:12.5px;margin:2px 0;padding-left:10px">• {p}</div>')
        else:
            p = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', s)
            out.append(f'<p style="font-size:12.5px;margin:3px 0">{p}</p>')
    return '\n'.join(out)


def parse_common(text):
    result = {
        "icp": {"title":"","definition":"","followers":"","purpose":"","spend":"","urgency":"","representative":""},
        "usps": [], "matrix": [], "copy_awareness": [], "copy_consideration": [], "copy_decision": [],
        "objections": [], "before_after": [], "segments": [], "price_html": "",
        "common_voices": [], "high_stress_html": "", "ad_copies": [],
        "hypotheses": [], "next_questions": [],
    }

    # Part 1: ICP
    sec1 = _sec(text, 1)
    if sec1:
        # ** 제거 helper
        def clean(s): return re.sub(r'\*\*', '', s).strip().strip('"').strip('"')

        def_m = re.search(r'(?:한 문장|ICP)[^:]*정의[^:]*:\s*\n?"?(.*?)(?:"|$|\n\n)', sec1, re.DOTALL)
        if not def_m: def_m = re.search(r'한 문장[^:]*:\s*\n?"?(.*?)(?:"|$|\n)', sec1)
        result["icp"]["definition"] = clean(def_m.group(1)) if def_m else ""
        for key, patterns in [
            ("followers", [r'\*?\*?팔로워[^:]*\*?\*?:\s*(.*?)(?:\n|$)']),
            ("purpose", [r'\*?\*?운영\s*목적[^:]*\*?\*?:\s*(.*?)(?:\n|$)']),
            ("spend", [r'\*?\*?지불\s*이력[^:]*\*?\*?:\s*(.*?)(?:\n|$)']),
            ("urgency", [r'\*?\*?긴급도[^:]*\*?\*?:\s*(.*?)(?:\n|$)']),
            ("representative", [r'\*?\*?대표\s*인물[^:]*\*?\*?:\s*(.*?)(?:\n|$)']),
        ]:
            for pat in patterns:
                m = re.search(pat, sec1)
                if m:
                    result["icp"][key] = clean(m.group(1))
                    break
        d = result["icp"]["definition"]
        result["icp"]["title"] = d[:40] + "..." if len(d) > 40 else d if d else "인스타 크리에이터"

    # Part 2: USPs (Pain→Gap→USP→Message)
    sec2 = _sec(text, 2)
    if sec2:
        usps = re.findall(
            r'###\s*USP\s*\d+:\s*(.*?)\n(.*?)(?=###\s*USP|## Part|$)',
            sec2, re.DOTALL
        )
        if not usps:
            usps = re.findall(
                r'###\s*\d+\.\s*(.*?)\n(.*?)(?=###\s*\d+|## Part|$)',
                sec2, re.DOTALL
            )
        for title, body in usps:
            title = title.strip().strip('"').strip('"').strip('*').strip('"')
            pain_m = re.search(r'\*\*Pain\*\*:\s*(.*?)(?:\n|$)', body)
            gap_m = re.search(r'\*\*Gap\*\*:\s*(.*?)(?:\n|$)', body)
            usp_m = re.search(r'\*\*USP\*\*:\s*(.*?)(?:\n|$)', body)
            msg_m = re.search(r'\*\*Primary Message\*\*:\s*(.*?)(?:\n|$)', body)
            people_m = re.search(r'\*\*뒷받침[^*]*\*\*:\s*(.*?)(?:\n|$)', body)
            str_m = re.search(r'\*\*강도\*\*:\s*(확실|유망|가설)', body)
            result["usps"].append({
                "message": msg_m.group(1).strip().strip('"') if msg_m else title,
                "pain": pain_m.group(1).strip() if pain_m else "",
                "gap": gap_m.group(1).strip() if gap_m else "",
                "usp": usp_m.group(1).strip() if usp_m else title,
                "people": people_m.group(1).strip() if people_m else "",
                "strength": str_m.group(1) if str_m else "유망",
            })

    # Part 3: Matrix
    sec3 = _sec(text, 3)
    if sec3:
        rows = _tbl(sec3)
        for r in rows:
            stage = r.get("퍼널 단계", r.get("퍼널", ""))
            result["matrix"].append({
                "stage": stage,
                "prospect": r.get("잠재고객 메시지", r.get("잠재고객", "")),
                "customer": r.get("기존고객 메시지", r.get("기존고객", "")),
                "quote": r.get("핵심 고객 원문", ""),
            })

    # Part 4: Copy Kit
    sec4 = _sec(text, 4)
    if sec4:
        # Awareness
        aw = re.search(r'인지.*?(?=###\s*고려|## Part|$)', sec4, re.DOTALL)
        if aw:
            for line in aw.group().split('\n'):
                s = line.strip()
                m = re.match(r'[-•\d]+[.)]\s*(.*)', s)
                if m and len(m.group(1)) > 5:
                    txt = re.sub(r'\*\*(.*?)\*\*', r'\1', m.group(1)).strip().strip('"')
                    typ = "헤드라인" if "헤드" in line.lower() else "서브카피" if "서브" in line.lower() else "후킹"
                    result["copy_awareness"].append({"text": txt, "type": typ, "source": ""})

        co = re.search(r'고려.*?(?=###\s*전환|## Part|$)', sec4, re.DOTALL)
        if co:
            for line in co.group().split('\n'):
                s = line.strip()
                m = re.match(r'[-•\d]+[.)]\s*(.*)', s)
                if m and len(m.group(1)) > 5:
                    txt = re.sub(r'\*\*(.*?)\*\*', r'\1', m.group(1)).strip().strip('"')
                    typ = "기능 가치" if "기능" in line or "가치" in line else "비교"
                    result["copy_consideration"].append({"text": txt, "type": typ, "source": ""})

        de = re.search(r'전환.*?(?=## Part|$)', sec4, re.DOTALL)
        if de:
            for line in de.group().split('\n'):
                s = line.strip()
                m = re.match(r'[-•\d]+[.)]\s*(.*)', s)
                if m and len(m.group(1)) > 5:
                    txt = re.sub(r'\*\*(.*?)\*\*', r'\1', m.group(1)).strip().strip('"')
                    typ = "소셜프루프" if "소셜" in line or "후기" in line else "CTA"
                    result["copy_decision"].append({"text": txt, "type": typ, "source": ""})

    # Part 5: Objections
    sec5 = _sec(text, 5)
    if sec5:
        rows = _tbl(sec5)
        for r in rows:
            result["objections"].append({
                "barrier": r.get("저항(Objection)", r.get("저항", "")),
                "quote": r.get("근거", ""),
                "counter": r.get("반박(Counter)", r.get("반박", "")),
                "counter_evidence": r.get("반박 근거", ""),
            })

    # Part 6: Before/After
    sec6 = _sec(text, 6)
    if sec6:
        rows = _tbl(sec6)
        for r in rows:
            before = r.get("Before (사용 전)", r.get("Before", ""))
            after = r.get("After (사용 후)", r.get("After", ""))
            quote = r.get("고객 원문", "")
            if before or after:
                result["before_after"].append({"before": before, "after": after, "quote": quote})

    # Part 7: Price
    sec7 = _sec(text, 7)
    if sec7:
        raw = re.sub(r'##\s*Part 7.*?\n', '', sec7)
        result["price_html"] = _md2html(raw.strip())

    # Part 8: 공통 발언
    sec8 = _sec(text, 8)
    if sec8:
        # 8-1: 공통 발언 테이블
        rows = _tbl(sec8)
        common_voices = {}
        for r in rows:
            theme = r.get("공통 주제", "")
            people = r.get("언급자 (이름)", r.get("언급자", ""))
            quotes_raw = r.get("각자의 원문", "")
            if theme:
                if theme not in common_voices:
                    common_voices[theme] = []
                # 원문을 사람별로 분리
                parts = [q.strip().strip('"').strip('"') for q in re.split(r'[/|·•]', quotes_raw) if q.strip()]
                names = [n.strip() for n in re.split(r'[,，、]', people) if n.strip()]
                for i, part in enumerate(parts):
                    who = names[i] if i < len(names) else people
                    common_voices[theme].append({"text": part, "who": who})
        result["common_voices"] = [
            {"theme": theme, "quotes": quotes}
            for theme, quotes in common_voices.items()
        ]

        # 8-2: 고스트레스 공통점
        stress_match = re.search(r'8-2.*?(?=## Part|$)', sec8, re.DOTALL)
        if stress_match:
            raw = re.sub(r'###?\s*8-2.*?\n', '', stress_match.group())
            result["high_stress_html"] = _md2html(raw.strip())

    # Part 9: 광고 카피 원문
    sec9 = _sec(text, 9)
    if sec9:
        rows = _tbl(sec9)
        for r in rows:
            text_val = r.get("고객 원문 (그대로)", r.get("고객 원문", "")).strip('"').strip('"')
            who = r.get("누가 한 말", "")
            copy_type = r.get("카피 유형 (페인/와우)", r.get("카피 유형", ""))
            usage = r.get("추천 용도 (헤드라인/서브카피/CTA/소셜프루프/배너)", r.get("추천 용도", ""))
            why = r.get("왜 강력한지", "")
            if text_val:
                result["ad_copies"].append({
                    "text": text_val, "who": who, "usage": usage, "why": why,
                    "copy_type": copy_type,
                })

    # Part 10: 미검증 가설
    sec10 = _sec(text, 10)
    if sec10:
        # 10-1: 가설 테이블
        rows = _tbl(sec10)
        for r in rows:
            hyp = r.get("가설", "")
            evidence = r.get("근거 (힌트)", r.get("근거", ""))
            why_un = r.get("왜 아직 미검증인지", "")
            how = r.get("검증 방법", "")
            if hyp:
                result["hypotheses"].append({
                    "hypothesis": hyp, "evidence": evidence,
                    "why_unverified": why_un, "how_to_verify": how,
                })

        # 10-2: 다음 질문
        q_pattern = re.findall(
            r'(?:###?\s*)?(?:Q\d+|질문\s*\d+)[.:]?\s*(.*?)\n(.*?)(?=(?:###?\s*(?:Q\d+|질문)|## Part|$))',
            sec10, re.DOTALL
        )
        for q_title, q_body in q_pattern:
            why_m = re.search(r'(?:왜|이유)[^:：]*[:：]\s*(.*?)(?:\n|$)', q_body)
            val_m = re.search(r'(?:검증|답)[^:：]*[:：]\s*(.*?)(?:\n|$)', q_body)
            result["next_questions"].append({
                "question": q_title.strip().strip('"'),
                "why": why_m.group(1).strip() if why_m else "",
                "validation": val_m.group(1).strip() if val_m else "",
            })

        # 테이블 형식으로도 시도
        if not result["next_questions"]:
            nq_match = re.search(r'10-2.*?(?=## Part|$)', sec10, re.DOTALL)
            if nq_match:
                nq_rows = _tbl(nq_match.group())
                for r in nq_rows:
                    q = r.get("질문", r.get("질문 원문", ""))
                    why = r.get("왜 이걸 물어봐야 하는지", r.get("이유", ""))
                    val = r.get("어떤 답이 나오면 가설이 검증되는지", r.get("검증", ""))
                    if q:
                        result["next_questions"].append({"question": q, "why": why, "validation": val})

    return result


def build_dashboard():
    print("마케팅 대시보드 빌드 중...")
    cache = load_cache()
    common_text = cache.get("common", {}).get("insight", "")
    common = parse_common(common_text)

    databases = []
    total = 0
    for db_name, db_id in DATABASES.items():
        entries = get_database_entries(db_id)
        interviews = []
        for entry in entries:
            key = entry["id"]
            if key not in cache or "insight" not in cache[key]: continue
            page_id_clean = entry["id"].replace("-", "")
            notion_url = f"https://notion.so/{page_id_clean}"
            parsed = parse_json_from_text(cache[key]["insight"])
            clean_title = entry["title"].replace('🟢','').replace('🔴','').replace('🟡','').strip()
            if parsed:
                iv = {
                    "title": clean_title,
                    "notion_url": notion_url,
                    "one_line": parsed.get("one_line", ""),
                    "pains": parsed.get("pain", []),
                    "values": parsed.get("value", []),
                    "voices": parsed.get("voice", []),
                    "objections": parsed.get("objection", []),
                }
                # 각 pain/voice에 출처 정보 주입
                for p in iv["pains"]:
                    p["source"] = clean_title
                    p["notion_url"] = notion_url
                for v in iv["voices"]:
                    v["source"] = clean_title
                    v["notion_url"] = notion_url
                for o in iv.get("objections", []):
                    o["source"] = clean_title
                    o["notion_url"] = notion_url
            else:
                iv = {"title": clean_title, "notion_url": notion_url, "one_line": "", "pains": [], "values": [], "voices": [], "objections": []}
            interviews.append(iv)
        total += len(interviews)
        databases.append({"name": db_name, "short": SHORT.get(db_name, ""), "interviews": interviews})

    # Segments from individual data
    segments = []
    for db in databases:
        points = []
        pain_count = sum(len(iv["pains"]) for iv in db["interviews"])
        val_count = sum(len(iv["values"]) for iv in db["interviews"])
        points.append(f"인터뷰 {len(db['interviews'])}명")
        points.append(f"Pain 포인트 {pain_count}개 발견")
        points.append(f"Value 포인트 {val_count}개 발견")
        segments.append({"name": db["name"], "points": points})
    common["segments"] = segments

    # 고객 고통 원문 수집 (모든 인터뷰에서 pain + voice + objection 원문)
    raw_pains = []
    for db in databases:
        for iv in db["interviews"]:
            url = iv.get("notion_url", "")
            name = iv["title"]
            seg = db["short"]
            for p in iv.get("pains", []):
                if p.get("quote"):
                    raw_pains.append({
                        "text": p["quote"], "category": "고통",
                        "point": p.get("point", ""), "intensity": p.get("intensity", ""),
                        "question": p.get("question", ""),
                        "emotion": p.get("emotion", ""),
                        "full_context": "",
                        "who": name, "segment": seg, "notion_url": url,
                    })
            for v in iv.get("voices", []):
                if v.get("text"):
                    raw_pains.append({
                        "text": v["text"], "category": "원문",
                        "point": v.get("context", ""), "intensity": "",
                        "question": "",
                        "emotion": "",
                        "full_context": v.get("full_context", ""),
                        "who": name, "segment": seg, "notion_url": url,
                    })
            for o in iv.get("objections", []):
                if o.get("quote"):
                    raw_pains.append({
                        "text": o["quote"], "category": "저항",
                        "point": o.get("barrier", ""), "intensity": "",
                        "question": "",
                        "emotion": "",
                        "full_context": "",
                        "who": name, "segment": seg, "notion_url": url,
                    })

    data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total": total, "db_count": len(DATABASES),
        "icp": common["icp"],
        "usps": common["usps"],
        "matrix": common["matrix"],
        "copy_awareness": common["copy_awareness"],
        "copy_consideration": common["copy_consideration"],
        "copy_decision": common["copy_decision"],
        "objections": common["objections"],
        "before_after": common["before_after"],
        "segments": common["segments"],
        "price_html": common["price_html"] or "<p>가격 데이터 로딩 중</p>",
        "common_voices": common["common_voices"],
        "high_stress_html": common["high_stress_html"] or "<p>데이터 분석 중</p>",
        "ad_copies": common["ad_copies"],
        "hypotheses": common["hypotheses"],
        "next_questions": common["next_questions"],
        "databases": databases,
        "raw_pains": raw_pains,
    }

    with open(TMPL) as f: html = f.read()
    html = html.replace("__DASHBOARD_DATA_PLACEHOLDER__", json.dumps(data, ensure_ascii=False))
    with open(OUT, "w") as f: f.write(html)
    print(f"  완료: {OUT}")
    return OUT


if __name__ == "__main__":
    build_dashboard()
