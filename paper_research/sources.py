"""Public metadata retrieval; never infer full-text access from an abstract."""
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, timedelta


class SourceError(RuntimeError):
    pass


def request(url, *, payload=None, key=None, attempts=3):
    headers = {"User-Agent": "PaperResearch/0.1 (research briefing)"}
    if key:
        headers["Authorization"] = "Bearer " + key
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode()
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers), timeout=90) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            # Do not log response bodies or credentials. Do not retry billed POSTs.
            if payload is None and exc.code in (429, 500, 502, 503, 504) and attempt + 1 < attempts:
                time.sleep(2 ** attempt)
                continue
            raise SourceError(f"{urllib.parse.urlsplit(url).hostname}: HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError):
            raise SourceError(f"{urllib.parse.urlsplit(url).hostname}: connection failed") from None


def get_json(url, **params):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return json.loads(request(url))


def clean(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", value or ""))).strip()


def doi_id(doi):
    return "doi:" + doi.lower().strip().removeprefix("https://doi.org/")


def arxiv(query, section, today, days):
    since = (today - timedelta(days=days)).strftime("%Y%m%d")
    until = today.strftime("%Y%m%d")
    params = urllib.parse.urlencode({"search_query": f"({query}) AND submittedDate:[{since}0000 TO {until}2359]", "sortBy": "submittedDate", "sortOrder": "descending", "max_results": 12})
    root = ET.fromstring(request("https://export.arxiv.org/api/query?" + params))
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    result = []
    for entry in root.findall("a:entry", ns):
        aid = re.sub(r"v\d+$", "", entry.findtext("a:id", "", ns).rsplit("/", 1)[-1])
        if not re.fullmatch(r"\d{4}\.\d{4,5}", aid):
            continue
        doi = entry.findtext("x:doi", "", ns)
        result.append({"id": doi_id(doi) if doi else "arxiv:" + aid, "aliases": ["arxiv:" + aid], "section": section, "title": clean(entry.findtext("a:title", "", ns)), "authors": [x.text for x in entry.findall("a:author/a:name", ns)], "date": entry.findtext("a:published", "", ns)[:10], "url": "https://arxiv.org/abs/" + aid, "doi": doi or None, "venue": entry.findtext("x:journal_ref", "arXiv", ns), "abstract": clean(entry.findtext("a:summary", "", ns)), "access": "abstract_only", "peer_review": "심사 여부 미확인; arXiv 등록만으로 판단하지 않음", "citation_count": None, "retrieved": today.isoformat()})
    return result


def pubmed(query, today, days):
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    data = get_json(base + "esearch.fcgi", db="pubmed", term=query, mindate=(today - timedelta(days=days)).isoformat(), maxdate=today.isoformat(), datetype="pdat", sort="pub_date", retmax=12, retmode="json")
    ids = data["esearchresult"]["idlist"]
    if not ids:
        return []
    time.sleep(0.4)  # NCBI requests without an API key: at most 3/sec.
    root = ET.fromstring(request(base + "efetch.fcgi?" + urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids), "retmode": "xml"})))
    result = []
    for item in root.findall(".//PubmedArticle"):
        pmid = item.findtext(".//PMID")
        article = item.find(".//Article")
        doi = item.findtext(".//ArticleId[@IdType='doi']")
        abstract = "\n".join((x.get("Label", "") + ": " if x.get("Label") else "") + "".join(x.itertext()) for x in article.findall("Abstract/AbstractText"))
        if not abstract:
            continue
        types = [x.text for x in article.findall("PublicationTypeList/PublicationType")]
        if any(x in types for x in ["Retracted Publication", "Retraction of Publication", "Published Erratum"]):
            continue
        pd = article.find("Journal/JournalIssue/PubDate")
        # Issue dates may be in the future for articles already online.
        electronic = article.find("ArticleDate[@DateType='Electronic']")
        if electronic is not None:
            published = "-".join(electronic.findtext(k, "01").zfill(2) for k in ("Year", "Month", "Day"))
            if published > today.isoformat():
                continue
        else:
            published = " ".join(pd.itertext()) if pd is not None else "unknown"
            year = pd.findtext("Year", "0") if pd is not None else "0"
            if year.isdigit() and int(year) > today.year:
                continue
        result.append({"id": doi_id(doi) if doi else "pubmed:" + pmid, "aliases": ["pubmed:" + pmid], "section": "medicine", "title": "".join(article.find("ArticleTitle").itertext()), "authors": [" ".join(filter(None, [a.findtext("ForeName"), a.findtext("LastName"), a.findtext("CollectiveName")])) for a in article.findall("AuthorList/Author")], "date": published, "issue_date": " ".join(pd.itertext()) if pd is not None else "unknown", "url": "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/", "doi": doi, "venue": article.findtext("Journal/Title"), "abstract": abstract, "study_types": types, "mesh": [x.text for x in item.findall(".//MeshHeading/DescriptorName")], "access": "abstract_only", "peer_review": "PubMed 수록; 개별 심사 이력 미확인", "citation_count": None, "retrieved": today.isoformat()})
    return result


STAGES = ("background", "core_paper", "follow_up")


def award_topic(today, seen):
    """Exhaust the latest award's three stages before walking back in time."""
    for year in range(today.year, today.year - 10, -1):
        data = get_json("https://api.nobelprize.org/2.1/nobelPrizes", nobelPrizeYear=year, limit=10)
        awards = data.get("nobelPrizes", [])
        for award in awards:
            category = award.get("category", {}).get("en")
            slug = {"Physiology or Medicine": "medicine", "Physics": "physics", "Chemistry": "chemistry"}.get(category)
            laureates = award.get("laureates", [])
            if not slug or not laureates or award.get("dateAwarded", "9999") > today.isoformat():
                continue
            for stage in STAGES:
                identity = f"nobel:{year}:{slug}:{stage}"
                if identity in seen:
                    continue
                names = [x.get("knownName", x.get("fullName", {})).get("en", "") for x in laureates]
                motivations = list(dict.fromkeys(x.get("motivation", {}).get("en", "") for x in laureates))
                return {"id": identity, "aliases": [], "section": "award", "stage": stage, "title": f"{year} Nobel Prize — {category}", "authors": names, "date": award.get("dateAwarded"), "url": f"https://www.nobelprize.org/prizes/{slug}/{year}/summary/", "venue": "NobelPrize.org official API", "abstract": "Laureates: " + ", ".join(names) + ". Official motivation: " + "; ".join(motivations), "access": "official_award_metadata", "peer_review": "논문이 아닌 공식 수상 정보", "citation_count": None, "retrieved": today.isoformat()}
    return None


def related_award_papers(topic, today, seen):
    """Discovery candidates only: author/keyword matches do not prove award linkage."""
    query = " ".join(topic["authors"]) + " " + topic["abstract"].split("Official motivation: ")[-1]
    data = get_json("https://api.crossref.org/works", query=query, rows=15, filter="type:journal-article,until-pub-date:" + today.isoformat())
    result = []
    for work in data.get("message", {}).get("items", []):
        doi = work.get("DOI")
        if not doi or doi_id(doi) in seen or not work.get("abstract"):
            continue
        year = work.get("published", {}).get("date-parts", [[0]])[0][0]
        if not year or year > today.year:
            continue
        result.append({"id": doi_id(doi), "aliases": [], "section": "award_paper", "title": clean(" ".join(work.get("title", []))), "authors": [" ".join(filter(None, [a.get("given"), a.get("family")])) for a in work.get("author", [])], "date": str(year), "url": "https://doi.org/" + doi, "doi": doi, "venue": "; ".join(work.get("container-title", [])), "abstract": clean(work["abstract"]), "access": "abstract_only", "peer_review": "Crossref 서지정보; 개별 심사 이력 미확인", "citation_count": work.get("is-referenced-by-count"), "citation_source": "Crossref", "retrieved": today.isoformat(), "linkage": "검색 후보이며 수상 업적의 핵심 논문인지 별도 판단 필요"})
    return result


def collect(settings, today, seen):
    sources, errors = [], []
    jobs = [("award", lambda: award_topic(today, seen)), ("robotics", lambda: arxiv(settings["queries"]["robotics"], "robotics", today, settings["lookback_days"])), ("medicine", lambda: pubmed(settings["queries"]["medicine"], today, settings["lookback_days"])), ("ai_mind", lambda: arxiv(settings["queries"]["ai_mind"], "ai_mind", today, settings["lookback_days"]))]
    for name, job in jobs:
        try:
            values = job()
            values = [values] if isinstance(values, dict) else (values or [])
            sources.extend(v for v in values if not ({v["id"], *v.get("aliases", [])} & seen))
        except (SourceError, ValueError, KeyError, ET.ParseError) as exc:
            errors.append({"source": name, "error": str(exc)})
    award = next((s for s in sources if s["section"] == "award"), None)
    if award:
        try:
            # Official explanatory page supplies context beyond the award motivation.
            url = award["url"].replace("/summary/", "/press-release/")
            page = request(url).decode("utf-8")
            page = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", page, flags=re.S | re.I)
            page = clean(page)
            motivation_start = page.find("was awarded")
            if motivation_start >= 0:
                page = page[max(0, motivation_start - 500):]
            award["official_explanation"] = page[:18000]
            award["explanation_url"] = url
        except (SourceError, UnicodeError) as exc:
            errors.append({"source": "award_explanation", "error": str(exc)})
        try:
            sources.extend(related_award_papers(award, today, seen))
        except (SourceError, ValueError, KeyError) as exc:
            errors.append({"source": "award_papers", "error": str(exc)})
    unique = {}
    for source in sources:
        unique.setdefault(source["id"], source)
    return {"date": today.isoformat(), "sources": list(unique.values()), "errors": errors}
