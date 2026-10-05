# 수동 IPP 수정본 재검증

대상 브랜치: fix/manual-ipp-driver
초기 커밋: f72f54a

## 초기 수정본에서 발견하여 보완한 항목

1. 앱 version만 바뀌어 통합 manifest와 불일치: 개발 단계에서는 양쪽 모두 upstream 1.12.0 유지.
2. 앱만 URI를 보정하여 HA 상태 조회 키가 다를 수 있음: 통합의 저장·설정 복원·기존 항목 보정에서도 정규화.
3. Debian bookworm SpliX 패키지 설치만으로 최신 M2020 지원을 가정함: OpenPrinting 2.0.2 릴리스 커밋을 고정하여 빌드하고 M2020 PPD 생성을 이미지 빌드 게이트로 추가.
4. lpinfo 첫 항목에서 awk가 종료되어 큰 목록에서 pipefail/SIGPIPE 가능: 목록 전체를 읽은 후 선택하고, 복수 후보는 진단 후 선택하지 않음.
5. 빈 TSV 필드를 | 문자로 처리하여 사용자의 이름/위치에 |가 있으면 잘못 읽을 수 있음: 원래 탭 구분자를 직접 분리.
6. HTTP/IPP 기본 포트를 일괄 631로 처리: 각 스킴 기본 포트 적용. IPv6 URI 처리.
7. 단순 TCP 연결을 Online으로 표시하여 HTML 관리자 페이지도 성공할 수 있음: Get-Printer-Attributes로 응답 유형·IPP 성공 상태·request-id 확인. Print-Job은 전송하지 않음.
8. 회귀 테스트를 CI에 포함하고 fix/** 브랜치에서도 CI 실행하도록 수정.

## 실행한 검증

- python3 -m unittest discover -s tests -v: 15개 통과
- Bash 스크립트 전체 문법 검사: 통과
- Python 통합 및 IPP probe compileall: 통과
- 앱 및 CI/Release YAML 파싱: 통과
- 앱/통합 버전 일치: 통과
- git diff --check: 통과
- 로컬 HTTP 서버 대상으로 실제 IPP 요청/응답 왕복: 통과
- OpenPrinting 2.0.2 실제 소스의 M2020 모델 정의·필터·빌드 의존성 확인

## 아직 검증하지 않은 항목

- Docker 이미지 빌드 및 컨테이너 시작: 현재 실행 환경에 Docker/Podman 없음
- HA Supervisor/통합 실기동·UI 저장·발견: 접근 가능한 HA 인스턴스 없음
- A8004T의 실제 IPP 응답 및 프린터 큐 처리
- SL-M2029의 실제 1페이지 출력 및 iPhone AirPrint 발견
- amd64/aarch64 빌드: 포크에 업로드 후 GitHub CI로 확인 필요

현재 판단: 로컬 회귀 검증을 통과한 개발 수정본. 설치/출력 성공을 보장하는 상태는 아님.

포크의 GitHub Actions를 활성화한 후 CI를 다시 트리거하여 두 아키텍처 빌드를 확인합니다.
