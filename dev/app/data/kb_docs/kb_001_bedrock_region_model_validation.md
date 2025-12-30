# Bedrock ValidationException: model identifier invalid

## 증상
- Bedrock InvokeModel 호출 시 다음과 같은 에러가 발생한다.
- 예시 로그:ValidationException: The provided model identifier is invalid.

## 대표 원인
1) **리전에서 해당 모델이 지원되지 않음**
   - 예: eu-west-2(London)에서 특정 Claude/Titan 모델이 미지원

2) 모델 ID 오타 또는 deprecated 모델 사용

## 해결 방법
- **지원 리전으로 변경**
  - 예: us-east-1, us-west-2 등 모델 지원 리전으로 전환
- 콘솔/CLI에서 **모델 ID와 리전 지원 여부 재확인**

## 재발 방지 체크리스트
- `.env`의 `AWS_REGION`과 `BEDROCK_MODEL_ID`를 “쌍으로” 검증하는 preflight 체크 추가
- CI에서 “모델/리전 매트릭스”를 테스트(가능하면 mock)

## 시그니처
- signature: `ValidationException:model identifier invalid`
- tags: bedrock, region, model_id
