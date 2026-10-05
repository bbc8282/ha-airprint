# ipTIME USB 프린터용 수동 IPP 지원 (검증 중)

이 브랜치는 자동 Bonjour 검색과 별도로 CUPS 드라이버를 지정합니다.
기준: upstream 1.12.0. 실제 SL-M2029 출력은 아직 검증하지 않았습니다.

## 설치

1. 기존 앱 및 HA 설정을 백업합니다. 기존 AirPrint 앱을 중지하고 자동 시작을 끕니다.
2. 이 브랜치의 airprint 폴더를 HA의 /addons/airprint 에 복사합니다.
   NAS의 일반 폴더가 아니라 **HA OS 내부 /addons** 경로입니다.
3. 앱 스토어 새로고침 후 로컬 앱 AirPrint IPP Manual을 설치합니다.
   config.yaml의 image 항목을 제거했으므로 수정한 Dockerfile을 로컬 빌드합니다.
   기존 공식 이미지로 실행하면 수정 사항이 반영되지 않습니다.
4. 주소 편집 기능도 필요하면 custom_components/airprint를 HA /config/custom_components/airprint에 덮어쓰고 HA를 재시작합니다.
   HACS 자동 업데이트가 이 변경을 덮어쓸 수 있습니다.
5. 기존 HA AirPrint 통합이 새 앱의 상태 API(동일 HA 호스트의 8099)에 연결하는지 확인합니다.
   기존 앱과 새 앱은 동시에 실행하지 않습니다.
6. 프린터 편집 화면에서 device를 아래의 **전체 URI**로 변경합니다.

```text
ipp://192.168.0.21:631/printers/ipTIME_Printer
```

앱 구성 YAML에서 기존 printers 목록은 유지하고 다음 최상위 항목을 추가합니다.
통합은 printers만 갱신하므로 driver_overrides는 유지됩니다.

```yaml
driver_overrides:
  - device: ipp://192.168.0.21:631/printers/ipTIME_Printer
    model: Samsung M2020 Series
```

재시작 후 로그에서 M2020 드라이버 목록과 `driver ...`, 출력 URI를 확인합니다.
먼저 1페이지로 시험 출력하세요. M2029와 SpliX M2020의 실제 호환성은 시험해야 합니다.
IPP 대상 Online은 원격 인쇄 큐의 유효한 IPP 응답을 뜻하며 USB 프린터 준비 상태를 보장하지 않습니다.
ipTIME 대상의 토너 및 페이지 수는 SNMP로 추정하지 않습니다.

## 변경

- OpenPrinting SpliX 2.0.2 릴리스 커밋 고정 빌드. M2020 PPD 생성 실패 시 이미지 빌드 실패
- driver_overrides로 검색 결과 없이 모델 드라이버 선택 (SpliX 우선)
- IPP 경로가 포함된 무스킴 주소는 ipp://로 보정. HA 통합 설정에는 전체 URI 권장
- IPP Get-Printer-Attributes로 큐 응답 확인. 단순 TCP 포트 접근성으로 성공 처리하지 않음
- 빈 location 필드가 driver 필드를 밀어버리는 TSV 읽기 수정
- 프린터 편집 화면에 device 입력 노출

## 검증 및 롤백

`python3 -m unittest discover -s tests`의 15개 테스트와 Bash/Python 문법 검사를 통과했습니다.
기존 무스킴 주소는 HA 통합에서도 보정하며, 이에 따라 일부 엔티티 식별자가 변경될 수 있습니다.
GitHub Actions에서 amd64/aarch64 Docker 이미지 빌드와 hassfest를 통과했습니다.
HA 통합 실기동과 실물 출력은 아직 검증하지 않았습니다.
롤백은 수정 앱 중지 → 기존 통합 파일 복구 → 기존 앱 재시작 순서입니다.
