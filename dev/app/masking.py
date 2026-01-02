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
        
        # 1. IP 주소 패턴 마스킹
        ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
        ips = re.findall(ip_pattern, masked_text)
        for i, ip in enumerate(list(set(ips))):
            placeholder = f"[IP_ADDR_{i}]"
            self.mapping_table[placeholder] = ip
            masked_text = masked_text.replace(ip, placeholder)

        # 2. 매뉴얼/문서 번호 패턴 (예: ABC-123) - 특정 회사 보안 매뉴얼 코드 대응
        doc_pattern = r'[A-Z]{3}-\d{3}'
        docs = re.findall(doc_pattern, masked_text)
        for i, doc in enumerate(list(set(docs))):
            placeholder = f"[DOC_REF_{i}]"
            self.mapping_table[placeholder] = doc
            masked_text = masked_text.replace(doc, placeholder)
            
        return masked_text

    def unmask(self, text: str) -> str:
        """LLM 답변에 포함된 플레이스홀더를 다시 원본 데이터로 복구합니다."""
        if not text:
            return text
            
        unmasked_text = text
        for placeholder, original in self.mapping_table.items():
            unmasked_text = unmasked_text.replace(placeholder, original)
        return unmasked_text