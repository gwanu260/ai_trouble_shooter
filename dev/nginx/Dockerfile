# nginx:alpine 을 기반으로 이미지 구성 -> 컨테이너 가동
# -> 자동구등(그렇게 만들어진 이미지)
FROM nginx:alpine
# web.conf 경로 수정 (핵심)
COPY nginx/web.conf /etc/nginx/conf.d/default.conf