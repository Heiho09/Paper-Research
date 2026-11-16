# 주간 논문 수집 자동화

목요일 오전 9시(한국 시간)에 공개 연구 자료를 수집해 이 저장소에 저장합니다.
**유료 AI API와 API 키는 사용하지 않습니다.** 브리핑은 사용자가 ChatGPT에 요청할 때 작성합니다.

## 처음 시작하기

1. [GitHub 제작·배포 안내서](docs/GITHUB_AUTOMATION_GUIDE.ko.md)의 3~5절을 따라 저장소를 만듭니다.
2. `.github/workflows/briefing.yml`이 기본 브랜치에 있는지 확인합니다.
3. Actions → Weekly research collection → Run workflow로 시험합니다.
4. 첫 성공 후 `collections/README.md`에서 최근 수집 자료를 읽습니다.
5. 자료의 `evidence.json`을 ChatGPT에 첨부하고 [브리핑 요청문](docs/CHAT_BRIEFING_PROMPT.ko.md)을 사용합니다.

저장소가 Private이면 로그인한 소유자와 접근 권한을 받은 사람만 웹에서 볼 수 있습니다.
이 패키지에는 다른 사람의 수집 자료·브리핑·소개 이력을 넣지 않았습니다.

## 구성

- `paper_research/`: 공개 출처 수집, 저장, 채팅에서 작성한 원고의 검증·렌더링.
- `config/settings.json`: 관심 분야 검색어·날짜 범위. 모델 설정 없음.
- `.github/workflows/briefing.yml`: 목요일 수집 예약과 수동 실행.
- `tests/`: 수집·보관·중복 이력 검증.
- `AGENTS.md`: 브리핑 편집 기준.
- `examples/style-guide.md`: 문체 참고용 예시. 소개 이력에 포함하지 않음.
- `tools/export_starter.py`: 개인 운영 자료를 제외한 시작용 ZIP 재생성 도구.

## 로컬 실행 (선택)

Python 3.12 이상이 있는 컴퓨터에서 프로젝트 폴더로 이동한 후 실행합니다.

```bash
python -m unittest discover -s tests -v
python -m paper_research.briefing collect
python -m paper_research.briefing archive
```

기본은 최근 45일 후보 수집입니다. 논문 본문이 아닌 초록·서지정보를 수집합니다.
추가 과금 여부는 GitHub Actions의 플랜별 실행·저장 한도와 ChatGPT 이용 플랜에서 확인하세요.
라이선스는 배포자가 선택한 LICENSE 파일을 확인합니다. 없으면 이용 허락이 자동 부여된 것으로
간주하지 말고 배포자에게 확인하세요. 수집 출처의 자료에는 별도 이용 조건이 적용됩니다.
