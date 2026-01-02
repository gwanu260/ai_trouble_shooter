import re

class MaskingManager:
    def __init__(self):
        # 마스킹된 항목과 원본 데이터를 저장할 딕셔너리
        self.mapping_table = {}

    def mask(self, text: str) -> str:
        """텍스트에서 민감 정보를 마스킹하고 매핑 테이블에 기록합니다."""
        if not text:
            return text
            
        masked_text = text
        
        # 1. IP 주소 패턴 추출 및 마스킹
        ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
        ips = re.findall(ip_pattern, masked_text)
        for i, ip in enumerate(list(set(ips))): # 중복 제거
            placeholder = f"IP_ADDR_{i}"
            self.mapping_table[placeholder] = ip
            # LLM이 구분하기 쉽도록 대괄호를 감싸서 교체합니다.
            masked_text = masked_text.replace(ip, f"[{placeholder}]")

        # 2. 매뉴얼/문서 번호 패턴 (예: ABC-123) 추출 및 마스킹
        doc_pattern = r'[A-Z]{3}-\d{3}'
        docs = re.findall(doc_pattern, masked_text)
        for i, doc in enumerate(list(set(docs))):
            placeholder = f"DOC_REF_{i}"
            self.mapping_table[placeholder] = doc
            masked_text = masked_text.replace(doc, f"[{placeholder}]")
            
        return masked_text

    def unmask(self, text: str) -> str:
        """LLM 답변 속의 플레이스홀더를 대괄호 유무와 상관없이 원본으로 복구합니다."""
        if not text:
            return text
            
        unmasked_text = text
        for placeholder, original in self.mapping_table.items():
            # 케이스 1: LLM이 대괄호를 유지한 경우 [IP_ADDR_0] -> 192.168...
            unmasked_text = unmasked_text.replace(f"[{placeholder}]", original)
            # 케이스 2: LLM이 대괄호를 벗긴 경우 IP_ADDR_0 -> 192.168...
            unmasked_text = unmasked_text.replace(placeholder, original)
            
        return unmasked_text