# 저장소 가이드라인

## 프로젝트 구조 및 모듈 구성
핵심 코드는 `src/`에 위치: `config.py`가 기본값을 중앙화하고, `data/`는 데이터 수집을 처리하며, `features/`는 NR7/ORB 지표를 계산하고, `screen/` 및 `backtest/`가 워크플로우를 구동하며, `notify/` 및 `store/`는 알림과 영속성을 담당하고, `cli.py`와 선택적 `app.py`가 진입점을 노출합니다. 실험을 위해 `notebooks/`를 사용하고 검증된 재사용 가능한 로직을 `src/`로 승격시킵니다. 종속성이나 런타임 설정이 변경될 때마다 `.env.example`과 `requirements.md`를 최신 상태로 유지하세요.

## 빌드, 테스트 및 개발 명령어
설치하기 전에 깨끗한 가상환경을 생성하세요(`python -m venv .venv` + 활성화). `pip install -r requirements.txt`로 종속성을 설치합니다. `python -m src.cli screener daily`, `python -m src.cli monitor --provider intraday --simulate`, `python -m src.cli backtest --strategy orb_nr7 --universe KOSPI200`로 주요 플로우를 실행하고, CLI 플래그를 `config.py`와 동기화된 상태로 유지하세요.

## 코딩 스타일 및 명명 규칙
PEP 8을 따르고, 4칸 들여쓰기, 모듈과 함수는 snake_case, 클래스는 CapWords를 사용합니다. 공개 함수에 타입 힌트를 주석으로 달고 특성 함수는 순수하게 유지하며, 공유 상수는 `config.py`에 둡니다. 동작이 명확하지 않은 곳에 간결한 독스트링을 사용하고 CLI 옵션 이름이 사용자 대면 용어를 반영하도록 합니다.

## 테스트 가이드라인
`pytest`를 사용하고 `tests/` 아래에 `src/` 레이아웃을 미러링합니다 (예: `tests/features/test_nr7.py`). 외부 데이터 제공업체를 모킹하고 ORB 시뮬레이션을 위한 결정론적 재생 픽스처를 시드합니다. 새 모듈의 경우 >85% 커버리지를 목표로 하고 변경 사항을 제출하기 전에 `pytest`를 실행하세요.

## 커밋 및 풀 리퀘스트 가이드라인
`feat(screen): add liquidity filter`와 같은 Conventional Commit 접두사를 채택합니다. 각 풀 리퀘스트에는 간단한 문제 설명, 변경 요약, 테스트 증거(`pytest` 출력 또는 모니터 로그), 설정 또는 스키마 업데이트에 대한 메모가 필요합니다. 관련 이슈를 연결하고 데이터, 스크리닝 또는 인프라 구성 요소가 변경될 때 해당 소유자의 리뷰를 요청하세요.

## 환경 및 보안 참고사항
`.env`를 커밋하지 마세요; `.env.example`에서 생성하고 인라인으로 새 키를 설명하세요. Slack, Telegram 또는 데이터베이스 액세스를 위한 시크릿은 환경 변수나 시크릿 저장소에 유지해야 하며, 선택적 종속성(예: TA-Lib)은 보호된 임포트와 `requirements.md`의 설치 메모로 우아하게 저하되어야 합니다.