# GitHub로 만드는 주간 논문 수집 자동화

**유료 AI API 없이 자료를 모으고, 필요할 때 ChatGPT에서 브리핑으로 읽기**

이 문서는 GitHub를 처음 쓰는 사람도 자신의 논문 수집 저장소를 만들 수 있도록 설명합니다.
프로그램 설치 없이 GitHub 웹에서 시작할 수 있습니다. 완성되는 것은 **자료 수집·저장 자동화**이며,
한국어 브리핑은 사용자가 ChatGPT에 요청할 때 작성합니다.

문서 기준일: 2026-11-16. GitHub 화면 명칭과 요금 정책은 변경될 수 있습니다.

## 1. 무엇이 자동이고, 무엇이 수동인가?

매주 목요일 09:00 한국 시간에 GitHub Actions가 공개 출처를 검색합니다.
논문 제목·저자·초록·링크·수상 해설을 날짜별로 저장하고 최근 자료 링크를 갱신합니다.
사용자는 저장된 자료를 ChatGPT에 전달해 3~4건의 한국어 브리핑과 문서를 요청합니다.

```text
목요일 예약 → GitHub Actions → 공개 출처 검색 → GitHub에 자료 저장
                                                  ↓
                         사용자가 ChatGPT에 자료 전달·요청
                                                  ↓
                              선별·해설·문서 작성 → 검토
```

- 수집: 노벨상 공식 API·해설, arXiv, PubMed, Crossref.
- AI API: 호출하지 않으며 OpenAI API 키가 필요 없습니다.
- 이메일: 사용하지 않습니다.
- 개인 PC: 예약 시각에 켜둘 필요가 없습니다.
- ChatGPT: GitHub 예약이 이 채팅을 자동으로 실행하지는 않습니다.
- Google Scholar, 퓰리처, OpenAlex: 현재 자동 수집 코드에 포함되지 않습니다.

GitHub 저장소는 파일 보관함이고, Actions는 정해진 시간에 프로그램을 실행하는 기능입니다.
별도의 웹사이트나 GitHub Pages를 만들지 않아도 Markdown 문서를 GitHub에서 읽을 수 있습니다.

## 2. 비용과 준비물

준비물은 GitHub 계정, 배포자가 제공한 시작용 ZIP, 브리핑을 요청할 ChatGPT 계정입니다.
GitHub 웹으로 설정하면 Python 설치는 필요 없습니다. 로컬 실행은 Python 3.12 이상을 사용합니다.

- 이 프로그램 자체에는 유료 모델 API 사용료가 없습니다.
- ChatGPT에서 하는 요청은 사용 중인 계정·플랜의 이용 한도를 따릅니다.
- 공개 저장소의 표준 GitHub-hosted runner 사용은 일반적으로 무료입니다.
- 비공개 저장소에는 GitHub 플랜별 실행 시간·artifact 저장 공간 한도가 적용됩니다.
  GitHub 계정의 Billing 설정에서 사용량을 확인하세요.
- 출처별 공개 API에는 요청 제한이 있습니다. 주간 소규모 수집을 기준으로 사용하며,
  대량 수집이나 배포 자료의 재사용은 각 출처의 이용 조건을 따릅니다.

## 3. 내 GitHub 저장소 만들기

아래 방법은 원본 저장소가 공개 템플릿이 아니어도, 시작용 ZIP을 전달받았다면 사용할 수 있습니다.

1. GitHub에 로그인하고 오른쪽 위 `+` → `New repository`를 선택합니다.
2. 이름을 `weekly-research`처럼 정합니다. 이름은 자유롭게 바꿔도 됩니다.
3. Public 또는 Private을 고릅니다. Private은 본인과 권한을 받은 사람만 볼 수 있습니다.
4. `Add a README file`을 선택하고 저장소를 생성합니다. 아래 설명은 기본 브랜치가 `main`인 경우입니다.
5. 제공받은 ZIP을 **먼저 압축 해제**합니다. ZIP 파일 자체를 GitHub에 올리는 것이 아닙니다.
6. `Code` → `Add file` → `Upload files`에서 압축 해제한 프로젝트 내부의 파일·폴더를 올립니다.
   `weekly-research-starter`라는 바깥 폴더째 넣지 말고 그 **안의 내용**을 올리세요.
7. 업로드를 검토하고 `Commit changes`로 저장합니다. README가 기존 파일을 대체하는 것은 정상입니다.

첫 화면에서 다음 경로가 보여야 합니다.

```text
README.md
AGENTS.md
paper_research/
config/settings.json
tests/
docs/
examples/style-guide.md
```

`.github`와 `.gitignore`는 숨김 항목이라 운영체제에 따라 업로드에서 빠질 수 있습니다.
다음 단계에서 워크플로를 직접 만들거나 파일 내용을 대조합니다.
`collections/`, `briefings/`, `data/history.json`은 시작용 ZIP에 없습니다. 다른 사람의
수집·소개 이력을 물려받지 않도록 제외했으며, 필요한 시점에 생성됩니다.

## 4. 자동 실행 워크플로 등록하기

GitHub 파일 목록에 `.github/workflows/briefing.yml`이 이미 있으면 아래 내용과 같은지 확인합니다.
없으면 `Add file` → `Create new file`을 선택하고 파일 이름을 다음처럼 입력합니다.

```text
.github/workflows/briefing.yml
```

GitHub는 `/`로 구분한 폴더도 함께 만듭니다. 아래 내용을 붙여 넣고 기본 브랜치에 저장합니다.
**이 파일을 저장하면 목요일 예약이 구성됩니다.** 처음에는 실행을 지켜볼 수 있는 시간에
다음 절의 수동 시험을 해보세요.

<!-- WORKFLOW_START -->
```yaml
name: Weekly research collection

on:
  workflow_dispatch:
  schedule:
    - cron: '0 0 * * 4' # Thursday 09:00 Asia/Seoul; GitHub may delay starts.

permissions:
  contents: read

concurrency:
  group: weekly-research-briefing
  cancel-in-progress: false

jobs:
  collect:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.repository.default_branch }}
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Test
        run: python -m unittest discover -s tests -v
      - name: Collect public sources (no AI API)
        run: python -m paper_research.briefing collect
      - name: Archive evidence and reading index
        run: python -m paper_research.briefing archive
      - name: Commit collection
        run: |
          git config user.name 'github-actions[bot]'
          git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
          git add collections/
          if ! git diff --cached --quiet; then
            git commit -m 'Archive weekly research sources'
            git push
          fi
      - name: Keep collection evidence for diagnosis
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: research-collection-${{ github.run_id }}-${{ github.run_attempt }}
          path: drafts/current/evidence.json
          if-no-files-found: ignore
          retention-days: 30
```
<!-- WORKFLOW_END -->

이 워크플로는 테스트도 먼저 실행하므로 `tests/` 폴더가 꼭 필요합니다.
ZIP의 `.github/workflows/test.yml`은 코드 변경 시 테스트만 실행하는 추가 워크플로입니다.
없어도 주간 수집 워크플로 안에서 테스트가 수행됩니다. 설치하려면 같은 방법으로 해당 경로에
파일을 만들고 ZIP에 있는 내용을 복사하면 됩니다.

`.gitignore`도 빠졌다면 `Add file` → `Create new file`로 만들고 다음 내용을 넣습니다.

```gitignore
__pycache__/
*.py[cod]
.env
.venv/
build/
drafts/
```

실행마다 GitHub가 제공하는 임시 인증으로 자기 저장소에 결과를 저장합니다.
사용자가 별도 개인 접근 토큰(PAT), OpenAI 키, 메일 비밀번호를 만들 필요가 없습니다.
워크플로의 `contents: write`는 수집 결과를 커밋하기 위해 사용합니다.
조직 정책이나 브랜치 보호 규칙이 쓰기를 제한한다면 자동으로 우회하지 않습니다.

## 5. 첫 수집을 직접 실행하고 확인하기

1. 저장소의 `Actions` 탭으로 갑니다.
2. Actions 사용을 승인하는 안내가 나오면 내용을 확인하고 활성화합니다.
3. **Weekly research collection** → `Run workflow` → 기본 브랜치를 선택해 실행합니다.
4. 실행 목록에서 새 실행을 열어 끝날 때까지 확인합니다.
5. `Test`, `Collect public sources`, `Archive evidence`, `Commit collection` 단계가 성공했는지 봅니다.
6. `Code` 탭에서 `collections/README.md`를 엽니다.

다음 항목을 확인하면 실제 준비가 끝난 것입니다.

- 수집 시각이 방금 실행한 시각인지 확인합니다.
- 수집 건수와 오류 수를 봅니다. 초록이 저장되어 있는지도 하나 열어 봅니다.
- `Archive weekly research sources` 커밋이 생겼는지 확인합니다.
- `collections/latest.json`이 가리키는 파일이 실제 존재하는지 확인합니다.

자료 수가 항상 43건인 것은 아닙니다. 출처와 검색 시점에 따라 달라집니다.
초록·메타데이터를 수집한 것이므로 논문 PDF 전체를 읽거나 보관했다는 뜻도 아닙니다.

실행 페이지의 Artifacts에는 진단용 원자료가 30일 동안 남습니다.
저장소에 커밋된 `collections/` 파일은 artifact와 별개로 Git에 보관됩니다.

## 6. 목요일 예약을 관리하기

기본 cron은 `0 0 * * 4`입니다. UTC 목요일 00:00, 한국 시간 목요일 09:00에 해당합니다.
GitHub는 실행을 지연시킬 수 있으므로 정각 도착을 보장하는 알람으로 사용하지는 마세요.

다른 시각을 원하면 `.github/workflows/briefing.yml`의 `cron`을 바꿉니다.
예를 들어 목요일 한국 시간 오전 10시는 `0 1 * * 4`입니다.
`config/settings.json`의 `timezone`은 날짜 표기와 수집 기준에 쓰이며,
그 파일의 `schedule` 설명만 바꿔서는 실제 예약 시각이 바뀌지 않습니다.

- 중지: Actions → 해당 워크플로 → 메뉴에서 `Disable workflow`.
- 재개: 같은 화면에서 `Enable workflow`.
- 별도 `BRIEFING_ENABLED`나 API 관련 변수는 필요하지 않습니다.
- 예약은 기본 브랜치의 워크플로로 실행됩니다. 다른 브랜치에만 저장하면 예약되지 않습니다.
- 공개 저장소는 장기간 활동이 없으면 GitHub 정책에 따라 예약이 비활성화될 수 있습니다.
- Fork로 복사한 경우 Actions 활성화를 별도로 확인하고 수동 실행부터 시험합니다.

## 7. 저장된 자료를 ChatGPT에 전달하기

저장소를 읽을 수 있는 ChatGPT/Codex 환경이라면 저장소를 연결한 뒤 아래처럼 요청합니다.
일반 채팅이 비공개 GitHub 링크를 자동으로 읽을 수 있다고 가정하지 마세요.

```text
이 저장소의 collections/latest.json이 가리키는 자료를 읽고,
AGENTS.md의 편집 기준에 따라 이번 주 브리핑 3~4건을 작성해줘.
자료 확인 범위와 수집 날짜를 밝히고, Markdown 문서로도 만들어줘.
유료 AI API는 사용하지 마.
```

저장소 연결 기능이 없다면 다음 방법을 사용합니다.

1. `collections/latest.json`을 열고 `path` 값을 확인합니다.
2. `collections/` 아래의 해당 `evidence.json`을 열어 `Download raw file` 등으로 내려받습니다.
   브라우저 화면이나 로그인 페이지를 저장한 HTML이 아니라 JSON 파일인지 확인합니다.
3. ChatGPT에 그 JSON 파일을 첨부합니다.
4. 별도 문서 `docs/CHAT_BRIEFING_PROMPT.ko.md`의 요청문을 붙여 넣습니다.
5. 이전에 소개한 논문을 제외하려면 기존 브리핑 또는 `data/history.json`도 함께 전달합니다.

유료 API 호출 없이 ChatGPT의 이용 한도 안에서 작성할 수 있습니다.
예약 수집과 ChatGPT 요청은 별개입니다. 이 구성은 자동 이메일이나 ChatGPT 알림을 보내지 않습니다.

## 8. 브리핑을 문서로 남기기

브리핑에는 원제, 저자, 확인된 소속, 발표일·발표처, 연구 유형, 심사 상태를 먼저 표시합니다.
이후 쉬운 해설, 한계, 확인된 결과물·기대 활용, 전문 용어 주석, 원문 링크를 붙입니다.
수상 연구 1건을 우선하고 로보틱스·양자 컴퓨팅·의학·AI/인지 등을 합쳐 보통 3~4건을 고릅니다.
관련 자료가 없으면 억지로 개수를 채우지 않습니다.

가장 쉬운 저장 방법은 ChatGPT가 작성한 Markdown을 검토한 뒤, 내 저장소에서
`Add file` → `Create new file`로 `briefings/YYYY-MM-DD/README.md`에 붙여 넣는 것입니다.
`YYYY-MM-DD`는 실제 작성일로 바꾸세요. ChatGPT가 파일을 만들었다고 해서 GitHub에
자동 업로드된 것은 아닙니다. 저장소 쓰기 도구가 없는 채팅에서는 직접 저장해야 합니다.

자동 중복 방지 이력까지 연결하려면, 저장소 접근이 가능한 코딩 도구에 다음처럼 요청하세요.

```text
검토한 브리핑을 현재 코드의 validate/render 형식에 맞는 briefing.json과
사용한 evidence.json으로 저장하고 publish 명령으로 검증·기록해줘.
실제 소개한 자료 ID만 history에 남겨줘. 외부 AI API 호출은 하지 마.
```

`publish`는 로컬 문서와 소개 이력을 저장하는 보조 명령이며 자체적으로 GitHub에 푸시하지 않습니다.
단순히 Markdown만 저장하면 `data/history.json`은 갱신되지 않습니다. 그 경우 다음 요청에
기존 글을 첨부하거나 코딩 도구에 이력 갱신을 함께 요청하세요.
초안·문체 예시와 확정 소개 이력은 구분합니다.

## 9. 관심 분야와 분량 바꾸기

GitHub에서 `config/settings.json`을 열고 연필 모양 편집 버튼으로 수정할 수 있습니다.

- `lookback_days`: 검색 기간. 기본 45일입니다.
- `queries.robotics`: arXiv 로보틱스 검색식. 기본 `cat:cs.RO`.
- `queries.quantum`: arXiv 양자 컴퓨팅·오류 정정·프로세서 검색식.
- `queries.ai_mind`: AI·추론·인지 연계 검색식.
- `queries.medicine`: PubMed 검색식.
- `max_items`: 브리핑 검증 시 허용하는 최대 항목 수. 기본 4이며 수집 건수 제한이 아닙니다.
- `AGENTS.md`와 요청문: 독자의 배경, 설명 수준, 관심 분야, 문서 구성을 조정합니다.

JSON은 큰따옴표를 사용하고 마지막 항목 뒤에 쉼표를 붙이지 않습니다.
현재 출처별 검색 건수는 코드에 정해져 있으며, 검색어만 바꾼다고 모든 논문을 수집하지는 않습니다.
새 분야나 새 출처를 추가하려면 수집 코드 수정이 필요할 수 있습니다.

## 10. 자주 생기는 문제

**GitHub 링크에서 404가 나옵니다.**
Private 저장소라면 소유자 또는 초대받은 계정으로 로그인하세요. 앱 내부 브라우저와
일반 브라우저의 로그인 상태가 다를 수 있습니다. 공개로 전환하지 않아도 본인은 볼 수 있습니다.

**Actions에 워크플로가 안 보입니다.**
`.github/workflows/briefing.yml`이 기본 브랜치의 정확한 위치에 있는지 확인하세요.
바깥 폴더째 업로드한 경우 `weekly-research-starter/.github/...`가 되어 인식되지 않습니다.
YAML 들여쓰기와 Actions 활성화 상태도 확인합니다.

**Permission denied / 403 / git push 실패가 납니다.**
실패한 단계가 외부 자료 조회인지, GitHub 커밋·푸시인지 먼저 구분합니다.
저장소 쓰기 실패라면 워크플로의 `contents: write`, 저장소의
`Settings → Actions → General → Workflow permissions`, 조직 정책·브랜치 보호를 확인하세요.
관리자가 제한한 정책을 우회하지 말고 관리자에게 문의하거나 PR 기반 저장 방식으로 수정합니다.
실행 중 다른 커밋이 생겨 충돌했다면 강제 푸시하지 말고 최신 상태에서 다시 실행합니다.

**외부 출처가 429 또는 5xx를 반환합니다.**
요청 제한이나 일시 장애일 수 있습니다. 실패한 출처는 근거 파일의 `errors`에 기록됩니다.
코드는 일부 상태에서 제한적으로 재시도합니다. 간격 없이 계속 재실행하지 마세요.
모든 자료가 비어 있으면 실패하며 이전 보관함을 그대로 둡니다.
실행 성공 표시만 보지 말고 수집 시각·건수·오류도 확인하세요.

**같은 논문이 여러 주의 수집 파일에 보입니다.**
수집은 후보 보관이고 소개는 별도 작업입니다. 아직 읽지 않은 후보를 남기기 위해 회차 간
중복이 있을 수 있습니다. 소개 이력은 실제 브리핑에 사용한 자료를 기준으로 관리합니다.

**목요일에 채팅이나 이메일이 오지 않습니다.**
정상입니다. 이 구성은 자료 수집·저장만 예약합니다. 브리핑은 채팅에서 요청해야 합니다.
ChatGPT 예약 기능이나 이메일 발송은 이 프로젝트와 별도로 구성해야 합니다.

## 11. 다른 사람에게 배포하려는 유지관리자에게

현재 작업 저장소와 공개 배포 저장소를 분리하면 개인 자료와 소개 이력을 섞지 않을 수 있습니다.
시작용 ZIP은 코드·테스트·워크플로·설정·문서만 담고, `.git`, 자격 증명 파일, 기존 수집 자료,
발행 문서, 개인 소개 이력은 포함하지 않습니다.

배포 순서는 다음과 같습니다.

1. 본인이 배포할 권리가 있는 코드·문서의 라이선스를 결정합니다. MIT 같은 소프트웨어
   라이선스가 선택지가 될 수 있지만, 현재 준비본에는 라이선스를 임의로 부여하지 않았습니다.
2. 출처에서 수집한 초록·이미지·해설에는 원 출처의 이용 조건이 따릅니다.
   프로젝트 코드의 라이선스가 제3자 자료의 재배포 권한까지 주는 것은 아닙니다.
3. 새 Public 저장소를 만들고 **깨끗한 시작용 패키지**를 올립니다.
4. 선택한 LICENSE와 실제 배포 저장소 주소를 문서에 추가합니다.
5. Settings → General에서 `Template repository`를 켭니다.
6. 새 사용자는 `Use this template` → `Create a new repository`로 자신의 저장소를 만듭니다.
7. 새 저장소에서도 수동 수집·커밋 시험을 한 번 수행하고 예약 활성 상태를 확인합니다.

템플릿은 원본 파일도 복사합니다. 공개 템플릿용 저장소는 수집 워크플로를 Disable해
샘플 이력이 쌓이지 않게 유지하고, 새 사용자는 자신의 복사본에서 Enable 후 시험하게 안내하세요.
템플릿 지정 자체가 새 사용자 환경의 실행 성공을 보장하지는 않습니다.

이 안내서를 만들면서 기존 운영 저장소를 공개하거나 템플릿으로 전환하지는 않았습니다.
배포 전 원본 저장소 링크만 공유하면 비공개 접근 제한으로 상대방에게 404가 나올 수 있습니다.

## 12. 개발자용 로컬 실행

압축을 푼 프로젝트의 루트에서 실행합니다. 작업 폴더 이름은 자유롭습니다.

```bash
python --version
python -m unittest discover -s tests -v
python -m paper_research.briefing collect
python -m paper_research.briefing archive
```

Python 3.12 이상, 표준 라이브러리만 사용합니다. API 키나 `pip install` 단계는 없습니다.
필요하면 `python` 대신 해당 환경의 `python3` 명령을 사용하세요.
예약은 GitHub Actions에서 실행되므로 로컬 컴퓨터의 예약 프로그램 설정은 필요 없습니다.

## 공식 참고 문서

- GitHub Actions 예약: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- GitHub Actions 결제: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- 템플릿 저장소: https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository
- 라이선스 선택: https://choosealicense.com/
- arXiv API: https://info.arxiv.org/help/api/index.html
- NCBI E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- Crossref API: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- Nobel Prize API: https://www.nobelprize.org/about/developer-zone-2/
