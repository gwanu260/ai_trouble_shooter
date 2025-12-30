# Connection refused / Timeout 계열

## 증상
- 서비스 호출 시 다음 중 하나가 발생
- `Connection refused`
- `TimeoutError`
- `ReadTimeout`

## 대표 원인
1) 대상 서비스 다운/포트 미오픈
2) Security Group / NACL / 방화벽 차단
3) DNS 설정 문제
4) 프록시 환경 설정 누락

## 해결 방법
- 대상 호스트/포트 health check
- 인바운드/아웃바운드 규칙 확인
- 컨테이너 네트워크/서비스 디스커버리 점검

## 재발 방지
- /health 엔드포인트 상시 모니터링
- 배포 파이프라인에 smoke test 추가

## 시그니처
- signature: `NETWORK:connection refused`
- tags: network, timeout, infra
