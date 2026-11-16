import argparse
import hashlib
import html
import json
from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .sources import SourceError, collect

ROOT = Path(__file__).resolve().parents[1]
def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def history(path):
    return read_json(path) if Path(path).exists() else {"issues": []}


def seen_ids(log):
    return {identity for issue in log["issues"] for identity in issue["source_ids"]}


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid text field: {name}")
    if "http://" in value or "https://" in value or "<" in value or "](" in value:
        raise ValueError(f"Unexpected link/HTML in generated {name}")


def validate(result, evidence, max_items):
    records = {s["id"]: s for s in evidence["sources"]}
    items = result.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= max_items:
        raise ValueError("No publishable items, or too many items")
    sections, used = set(), set()
    for item in items:
        section = item.get("section")
        if section not in {"award", "robotics", "medicine", "ai_mind"} or section in sections:
            raise ValueError("Unknown or duplicate section")
        sections.add(section)
        for field in ("title", "takeaway", "why", "caution"):
            text(item.get(field), field)
        if not isinstance(item.get("story"), list) or not 1 <= len(item["story"]) <= 4:
            raise ValueError("Invalid story")
        for paragraph in item["story"]:
            text(paragraph, "story")
        if "outcomes" in item:
            if not isinstance(item["outcomes"], dict):
                raise ValueError("Invalid outcomes")
            for field in ("demonstrated", "application", "readiness"):
                text(item["outcomes"].get(field), "outcomes." + field)
        ids = item.get("sources")
        if not isinstance(ids, list) or not ids or any(not isinstance(i, str) or i not in records for i in ids):
            raise ValueError("Unknown/missing evidence id")
        selected = [records[i] for i in ids]
        if not any(s["section"] == section for s in selected):
            raise ValueError("Section has no matching evidence")
        if section == "award":
            topic = next(s for s in selected if s["section"] == "award")
            if topic.get("stage") in {"core_paper", "follow_up"} and not any(s["section"] == "award_paper" for s in selected):
                raise ValueError("Award progression requires a paper")
        if not isinstance(item.get("glossary"), list):
            raise ValueError("Missing glossary")
        for note in item["glossary"]:
            text(note.get("term"), "term")
            text(note.get("meaning"), "meaning")
        used.update(ids)
    if not isinstance(result.get("omissions"), list):
        raise ValueError("Missing omissions list")
    for omission in result["omissions"]:
        text(omission, "omissions")
    return used


def md(value):
    return html.escape(str(value)).replace("[", "\\[").replace("]", "\\]").replace("*", "\\*").replace("_", "\\_")


def collection_index(evidence):
    labels = {"award": "수상 연구", "award_paper": "수상 관련 검색 후보", "robotics": "로보틱스", "medicine": "의학·생명", "ai_mind": "AI·인지"}
    lines = [f"# 수집 자료 · {evidence['date']}", "", "AI 요약 없이 저장한 자료입니다. 검색 후보이며 추천 순위가 아닙니다.", "", f"수집 시각: {evidence.get('collected_at', evidence['date'])}", "", f"자료 {len(evidence['sources'])}건 · 출처 오류 {len(evidence.get('errors', []))}건", "", "[구조화된 근거 자료](evidence.json)", ""]
    for error in evidence.get("errors", []):
        lines += [f"- 수집 오류: {md(error['source'])} — {md(error['error'])}"]
    for section, label in labels.items():
        records = [s for s in evidence["sources"] if s["section"] == section]
        if not records:
            continue
        lines += ["", "## " + label, ""]
        for source in records:
            lines += [f"### [{md(source['title'])}]({source['url']})", "", f"{md(', '.join(source.get('authors', [])[:3]))} · {md(source.get('date', ''))} · {md(source.get('venue', ''))}", "", md(source.get("abstract", "초록 없음")), ""]
            lines += ["확인 범위: " + ("공식 수상 정보·해설" if source["access"] == "official_award_metadata" else "초록·서지정보. 논문 본문 미확인."), ""]
            if source.get("citation_count") is not None:
                lines += [f"참고: 인용 {source['citation_count']}회 · {md(source['citation_source'])} · 조회 {source['retrieved']}", ""]
    return "\n".join(lines)


def archive(evidence, destination):
    """Immutable snapshots; collecting is not the same as introducing a paper."""
    date.fromisoformat(evidence["date"])
    if not evidence.get("sources"):
        raise ValueError("No sources to archive; previous collection remains available")
    payload = json.dumps(evidence, ensure_ascii=False, sort_keys=True).encode()
    digest = hashlib.sha256(payload).hexdigest()
    destination = Path(destination)
    relative = Path(evidence["date"]) / digest[:16]
    folder = destination / relative
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / "evidence.json").exists():
        if read_json(folder / "evidence.json") != evidence:
            raise ValueError("Snapshot identity collision; refusing overwrite")
    else:
        write_json(folder / "evidence.json", evidence)
    (folder / "README.md").write_text(collection_index(evidence), encoding="utf-8")
    manifest = {"date": evidence["date"], "collected_at": evidence.get("collected_at", evidence["date"]), "path": str(relative / "evidence.json"), "count": len(evidence["sources"]), "source_errors": evidence.get("errors", []), "sha256": digest}
    previous = read_json(destination / "latest.json") if (destination / "latest.json").exists() else {}
    if manifest["collected_at"] >= previous.get("collected_at", ""):
        write_json(destination / "latest.json", manifest)
        (destination / "README.md").write_text(f"# 수집 자료 보관함\n\n최근 수집: {manifest['collected_at']} · {manifest['count']}건\n\n[최근 자료 읽기]({relative}/README.md) · [근거 JSON]({relative}/evidence.json)\n\n매주 목요일 09:00 한국 시간에 수집·저장합니다. AI API를 호출하지 않습니다.\n브리핑은 사용자가 채팅에서 요청할 때 작성합니다.\n", encoding="utf-8")
    return folder


def render(result, evidence):
    records = {s["id"]: s for s in evidence["sources"]}
    lines = [f"# 논문 리서칭 · {evidence['date']}", "", "가볍게 읽고, 궁금한 주제는 더 깊게. 인용 지표는 순위가 아닌 참고 자료입니다.", ""]
    if evidence.get("errors"):
        lines += ["일부 출처 수집에 실패해 해당 자료는 제외했습니다. 수집 기록을 참고하세요.", ""]
    for number, item in enumerate(result["items"], 1):
        lines += [f"## {number}. {md(item['title'])}", ""]
        for identity in item["sources"]:
            source = records[identity]
            award = source["access"] == "official_award_metadata"
            names = source.get("authors", [])
            authors = ", ".join(names[:3]) + (f" 외 (총 {len(names)}명)" if len(names) > 3 else "")
            affiliations = "; ".join(source.get("affiliations", [])) or "이번 수집 자료에서 미확인"
            lines += [f"- **{'자료' if award else '논문 원제'}:** [{md(source['title'])}]({source['url']})",
                      f"- **{'수상자' if award else '저자(기재 순서)'}:** {md(authors or '미확인')}",
                      f"- **소속:** {md(affiliations)}",
                      f"- **{'발표' if award else '공개일·발표처'}:** {md(source.get('date', '미확인'))} · {md(source.get('venue', '미확인'))}"]
            if source.get("issue_date") and source["issue_date"] != source.get("date"):
                lines += ["  - 별도 저널 호수 날짜: " + md(source["issue_date"])]
            study = "공식 수상 해설 (개별 논문 아님)" if award else item.get("research_type") or ", ".join(source.get("study_types", [])) or "원자료에서 미확인"
            lines += [f"- **연구·자료 유형:** {md(study)}",
                      f"- **심사 상태:** {md(source.get('peer_review', '미확인'))}"]
            if source.get("doi"):
                lines += ["- **DOI:** " + md(source["doi"])]
            lines += [""]
        lines += [f"**{md(item['takeaway'])}**", ""]
        for paragraph in item["story"]:
            lines += [md(paragraph), ""]
        lines += ["**왜 흥미로운가:** " + md(item["why"]), "", "**여기까지는 조심:** " + md(item["caution"]), ""]
        if item.get("outcomes"):
            lines += ["**확인된 결과물·기대 활용**", ""]
            for field, label in (("demonstrated", "확인된 성과"), ("application", "활용·기대 효과"), ("readiness", "적용 단계·남은 검증")):
                lines += [f"- **{label}:** {md(item['outcomes'][field])}"]
            lines += [""]
        for note in item["glossary"]:
            lines += [f"> **{md(note['term'])}** — {md(note['meaning'])}", ""]
        for identity in item["sources"]:
            source = records[identity]
            authors = ", ".join(source.get("authors", [])[:3]) + (" 외" if len(source.get("authors", [])) > 3 else "")
            lines += [f"- [{md(source['title'])}]({source['url']}) — {md(authors)} · {md(source.get('date', ''))} · {md(source.get('venue', ''))}"]
            scope = "공식 수상 정보" if source["access"] == "official_award_metadata" else "초록·서지정보 확인, 본문 미확인"
            lines += [f"  - 확인 범위: {scope}. {md(source.get('peer_review', '심사 여부 미확인'))}."]
            if source.get("doi"):
                lines += ["  - DOI: " + md(source["doi"])]
            if source.get("explanation_url"):
                lines += [f"  - [공식 수상 해설]({source['explanation_url']})"]
            if source.get("citation_count") is not None:
                lines += [f"  - 참고: 인용 {source['citation_count']}회 · {md(source['citation_source'])} · 조회 {source['retrieved']}. 집계 서비스에 따라 다를 수 있습니다."]
        lines += [""]
    if result["omissions"]:
        lines += ["이번에 생략한 항목: " + " / ".join(md(x) for x in result["omissions"]), ""]
    return "\n".join(lines)


def publish(draft_dir, output, log_path, max_items):
    draft_dir, output = Path(draft_dir), Path(output)
    evidence = read_json(draft_dir / "evidence.json")
    result = read_json(draft_dir / "briefing.json")
    used = validate(result, evidence, max_items)
    log = history(log_path)
    expanded = set(used)
    for source in evidence["sources"]:
        if source["id"] in used:
            expanded.update(source.get("aliases", []))
    if seen_ids(log) & expanded:
        raise ValueError("Already published evidence; recollect instead of repeating")
    issue_path = output / evidence["date"]
    if issue_path.exists():
        raise ValueError("Issue for this date already exists; refusing overwrite")
    # All validation before changing history. Drafts never advance history.
    issue_path.mkdir(parents=True)
    article = render(result, evidence)
    (issue_path / "README.md").write_text(article, encoding="utf-8")
    write_json(issue_path / "evidence.json", evidence)
    write_json(issue_path / "briefing.json", result)
    if (draft_dir / "run.json").exists():
        write_json(issue_path / "run.json", read_json(draft_dir / "run.json"))
    log["issues"].append({"date": evidence["date"], "source_ids": sorted(expanded), "sha256": hashlib.sha256(article.encode()).hexdigest()})
    write_json(log_path, log)
    return issue_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="논문 리서칭: collect → archive; 요청 시 채팅에서 작성")
    parser.add_argument("command", choices=["collect", "archive", "publish"])
    parser.add_argument("--settings", type=Path, default=ROOT / "config/settings.json")
    parser.add_argument("--draft-dir", type=Path, default=ROOT / "drafts/current")
    parser.add_argument("--history", type=Path, default=ROOT / "data/history.json")
    parser.add_argument("--output", type=Path, default=ROOT / "briefings")
    parser.add_argument("--collections", type=Path, default=ROOT / "collections")
    args = parser.parse_args(argv)
    try:
        settings = read_json(args.settings)
        if args.command == "collect":
            now = datetime.now(ZoneInfo(settings["timezone"]))
            today = now.date()
            evidence = collect(settings, today, seen_ids(history(args.history)))
            evidence["collected_at"] = now.isoformat(timespec="seconds")
            write_json(args.draft_dir / "evidence.json", evidence)
            # Remove generated files from an earlier collection, not user inputs.
            for name in ("briefing.json", "README.md", "run.json"):
                (args.draft_dir / name).unlink(missing_ok=True)
            print(f"Collected {len(evidence['sources'])} sources; {len(evidence['errors'])} source errors")
            for error in evidence["errors"]:
                print(f"  {error['source']}: {error['error']}")
            if not evidence["sources"]:
                return 1
        elif args.command == "archive":
            evidence = read_json(args.draft_dir / "evidence.json")
            print("Saved collection:", archive(evidence, args.collections))
        else:
            print("Saved issue:", publish(args.draft_dir, args.output, args.history, settings["max_items"]))
    except (ValueError, KeyError, OSError, SourceError) as exc:
        print(f"Stopped: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
