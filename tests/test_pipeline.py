import copy
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from paper_research import briefing as b
from paper_research import sources as s


def fixture():
    evidence = {"date": "2026-11-16", "errors": [], "sources": [{"id": "doi:10.example/a", "aliases": ["arxiv:2601.12345"], "section": "robotics", "title": "A robot paper", "authors": ["A Researcher"], "date": "2026", "url": "https://doi.org/10.example/a", "venue": "Test venue", "abstract": "A robot learning experiment.", "access": "abstract_only", "peer_review": "미확인", "citation_count": 0, "citation_source": "Crossref", "retrieved": "2026-11-16"}]}
    result = {"items": [{"section": "robotics", "title": "로봇은 어떻게 배울까?", "takeaway": "로봇 학습 실험을 살펴봅니다.", "story": ["실험 결과를 살펴봅니다."], "why": "로봇 학습에 관한 연구입니다.", "caution": "초록만 확인했습니다.", "glossary": [{"term": "VLA", "meaning": "시각·언어·행동 모델"}], "sources": ["doi:10.example/a"]}], "omissions": []}
    return evidence, result


class PipelineTests(unittest.TestCase):
    def test_archive_is_repeatable_and_does_not_mark_sources_read(self):
        evidence, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = b.archive(evidence, root / "collections")
            second = b.archive(evidence, root / "collections")
            self.assertEqual(first, second)
            self.assertEqual(b.read_json(first / "evidence.json"), evidence)
            latest = b.read_json(root / "collections/latest.json")
            self.assertEqual(root / "collections" / latest["path"], first / "evidence.json")
            self.assertIn("A robot paper", (first / "README.md").read_text())
            self.assertEqual(b.seen_ids(b.history(root / "history.json")), set())

    def test_changed_collection_retains_previous_snapshot(self):
        evidence, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            first = b.archive(evidence, directory)
            updated = copy.deepcopy(evidence)
            updated["sources"][0]["abstract"] = "Updated evidence"
            second = b.archive(updated, directory)
            self.assertNotEqual(first, second)
            self.assertEqual(b.read_json(first / "evidence.json"), evidence)

    def test_empty_collection_cannot_replace_latest(self):
        evidence, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            b.archive(evidence, directory)
            before = (Path(directory) / "latest.json").read_bytes()
            evidence["sources"] = []
            with self.assertRaisesRegex(ValueError, "No sources"):
                b.archive(evidence, directory)
            self.assertEqual(before, (Path(directory) / "latest.json").read_bytes())

    def test_older_snapshot_does_not_replace_latest(self):
        evidence, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            b.archive(evidence, directory)
            evidence["date"] = "2026-11-15"
            b.archive(evidence, directory)
            self.assertEqual(b.read_json(Path(directory) / "latest.json")["date"], "2026-11-16")

    def test_collection_errors_visible_in_reading_index(self):
        evidence, _ = fixture()
        evidence["errors"] = [{"source": "arxiv", "error": "HTTP 503"}]
        self.assertIn("HTTP 503", b.collection_index(evidence))
        self.assertIn("순위가 아닙니다", b.collection_index(evidence))

    def test_unknown_citation_rejected(self):
        evidence, result = fixture()
        result["items"][0]["sources"] = ["invented:reference"]
        with self.assertRaisesRegex(ValueError, "evidence"):
            b.validate(result, evidence, 4)

    def test_duplicate_section_rejected(self):
        evidence, result = fixture()
        result["items"].append(copy.deepcopy(result["items"][0]))
        with self.assertRaisesRegex(ValueError, "section"):
            b.validate(result, evidence, 4)

    def test_award_progression_requires_paper(self):
        evidence, result = fixture()
        evidence["sources"][0].update(section="award", stage="core_paper")
        result["items"][0]["section"] = "award"
        with self.assertRaisesRegex(ValueError, "requires a paper"):
            b.validate(result, evidence, 4)

    def test_render_scope_and_optional_metrics(self):
        evidence, result = fixture()
        output = b.render(result, evidence)
        self.assertIn("본문 미확인", output)
        self.assertIn("인용 0회", output)
        self.assertIn("VLA", output)
        evidence["sources"][0]["citation_count"] = None
        self.assertNotIn("인용 0회", b.render(result, evidence))

    def test_publish_records_alias_and_refuses_repeat(self):
        evidence, result = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            b.write_json(root / "draft/evidence.json", evidence)
            b.write_json(root / "draft/briefing.json", result)
            self.assertFalse((root / "history.json").exists())
            issue = b.publish(root / "draft", root / "issues", root / "history.json", 4)
            self.assertTrue((issue / "README.md").exists())
            self.assertIn("arxiv:2601.12345", b.seen_ids(b.history(root / "history.json")))
            before = (root / "history.json").read_bytes()
            with self.assertRaises(ValueError):
                b.publish(root / "draft", root / "issues", root / "history.json", 4)
            self.assertEqual(before, (root / "history.json").read_bytes())

    def test_invalid_output_does_not_change_history(self):
        evidence, result = fixture()
        result["items"][0]["sources"] = ["fabricated"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            b.write_json(root / "draft/evidence.json", evidence)
            b.write_json(root / "draft/briefing.json", result)
            with self.assertRaises(ValueError):
                b.publish(root / "draft", root / "issues", root / "history.json", 4)
            self.assertFalse((root / "history.json").exists())
            self.assertFalse((root / "issues").exists())

    @patch.object(s, "get_json")
    def test_unannounced_award_falls_back_and_advances(self, get_json):
        award = {"category": {"en": "Physics"}, "dateAwarded": "2025-10-07", "laureates": [{"knownName": {"en": "Example"}, "motivation": {"en": "example discovery"}}]}
        get_json.side_effect = [{"nobelPrizes": []}, {"nobelPrizes": [award]}]
        topic = s.award_topic(date(2026, 5, 1), {"nobel:2025:physics:background"})
        self.assertEqual(topic["id"], "nobel:2025:physics:core_paper")

    @patch.object(s, "request")
    def test_arxiv_versions_have_stable_identity(self, request):
        request.return_value = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2601.12345v3</id><title>Test</title><summary>Evidence</summary><published>2026-01-01</published><author><name>A</name></author></entry></feed>'''
        record = s.arxiv("cat:cs.RO", "robotics", date(2026, 1, 2), 45)[0]
        self.assertEqual(record["id"], "arxiv:2601.12345")
        self.assertEqual(record["access"], "abstract_only")

    @patch.object(s.time, "sleep")
    @patch.object(s, "request")
    @patch.object(s, "get_json")
    def test_pubmed_uses_online_date_for_future_issue(self, get_json, request, sleep):
        get_json.return_value = {"esearchresult": {"idlist": ["1"]}}
        request.return_value = b'''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>1</PMID><Article><Journal><Title>Journal</Title><JournalIssue><PubDate><Year>2027</Year><Month>Dec</Month></PubDate></JournalIssue></Journal><ArticleTitle>A study</ArticleTitle><Abstract><AbstractText>Evidence</AbstractText></Abstract><ArticleDate DateType="Electronic"><Year>2026</Year><Month>11</Month><Day>1</Day></ArticleDate></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>'''
        record = s.pubmed("test", date(2026, 11, 16), 45)[0]
        self.assertEqual(record["date"], "2026-11-01")
        self.assertIn("2027", record["issue_date"])

    @patch.object(s, "award_topic", side_effect=s.SourceError("nobel: HTTP 503"))
    @patch.object(s, "arxiv", return_value=[])
    @patch.object(s, "pubmed", return_value=[])
    def test_source_failure_is_reported(self, pubmed, arxiv, award_topic):
        settings = {"queries": {"robotics": "r", "medicine": "m", "ai_mind": "a", "quantum": "q"}, "lookback_days": 45}
        evidence = s.collect(settings, date(2026, 11, 16), set())
        self.assertEqual(evidence["sources"], [])
        self.assertEqual(evidence["errors"][0]["source"], "award")


if __name__ == "__main__":
    unittest.main()
