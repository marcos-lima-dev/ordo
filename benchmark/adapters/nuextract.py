import json
import re
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from .base import CandidateAdapter, register_adapter

@register_adapter("nuextract")
class NuExtractAdapter(CandidateAdapter):
    def __init__(self, model_name="Numind/NuExtract-tiny-v1.5", device="cpu"):
        self.model_name = model_name
        self.device = device
        print(f"Carregando modelo {model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map=device
        )
        self._build_prompt_template()

    def _build_prompt_template(self):
        self.schema = """{
  "intent": "ADD_ITEM" or "REMOVE_ITEM" or "CHANGE_QUANTITY" or "QUERY_PRICE" or "QUERY_AVAILABILITY" or "CONFIRM_ORDER" or "CANCEL_ORDER" or "REPLACE_ITEM" or "UNKNOWN",
  "product_term": "string" or null,
  "quantity": {
    "value": number or null,
    "value_origin": "EXPLICIT" or "INFERRED" or "NOT_INFORMED",
    "unit": "string" or null,
    "unit_origin": "EXPLICIT" or "INFERRED" or "NOT_INFORMED"
  },
  "explicit_presentation": "string" or null,
  "explicit_brand": "string" or null,
  "contextual_references": ["string"] or [],
  "missing_information": ["quantity", "unit", "brand", "presentation", "product_specification"] or [],
  "catalog_candidates": ["CQ-XX"] or [],
  "product_resolution_status": "EXACT_MATCH" or "HIGH_CONFIDENCE" or "AMBIGUOUS" or "NOT_FOUND"
}"""
        self.template = """### Template:
{schema}

### Text:
{text}

### Response:
"""

    def predict(self, message: str) -> dict:
        full_prompt = self.template.format(schema=self.schema, text=message)
        inputs = self.tokenizer(full_prompt, return_tensors="pt").to(self.device)
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=False,
            pad_token_id=self.tokenizer.eos_token_id
        )
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        try:
            json_str = self._extract_json(response)
            parsed = json.loads(json_str)
            return self._normalize(parsed)
        except Exception as e:
            print(f"Erro ao parsear resposta: {e}")
            print(f"Resposta bruta (primeiros 500 chars): {response[:500]}...")
            return self._fallback()

    def _extract_json(self, text: str) -> str:
        markdown_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if markdown_match:
            text = markdown_match.group(1)
        else:
            start = text.rfind('{')
            if start == -1:
                raise ValueError("Nenhum JSON encontrado")
            text = text[start:]
        text = text.replace('\x00', '').strip()
        brace_count = 0
        in_string = False
        escape_next = False
        end = 0
        for i, ch in enumerate(text):
            if escape_next:
                escape_next = False
                continue
            if ch == '\\':
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                brace_count += 1
            elif ch == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
        if brace_count != 0 or end == 0:
            raise ValueError("JSON incompleto ou malformado")
        return text[:end]

    def _normalize(self, parsed: dict) -> dict:
        required_fields = [
            "intent", "product_term", "explicit_presentation", "explicit_brand",
            "contextual_references", "missing_information", "catalog_candidates",
            "product_resolution_status"
        ]
        defaults = {
            "intent": "UNKNOWN",
            "product_term": None,
            "explicit_presentation": None,
            "explicit_brand": None,
            "contextual_references": [],
            "missing_information": [],
            "catalog_candidates": [],
            "product_resolution_status": "NOT_FOUND"
        }
        for field in required_fields:
            if field not in parsed or parsed[field] is None:
                parsed[field] = defaults[field]
            if field in ["contextual_references", "missing_information", "catalog_candidates"]:
                if not isinstance(parsed[field], list):
                    parsed[field] = []
        quantity = parsed.get("quantity")
        if quantity is None or not isinstance(quantity, dict):
            parsed["quantity"] = {
                "value": None,
                "value_origin": "NOT_INFORMED",
                "unit": None,
                "unit_origin": "NOT_INFORMED"
            }
        else:
            q_defaults = {
                "value": None,
                "value_origin": "NOT_INFORMED",
                "unit": None,
                "unit_origin": "NOT_INFORMED"
            }
            for key, val in q_defaults.items():
                if key not in quantity or quantity[key] is None:
                    quantity[key] = val
            parsed["quantity"] = quantity
        return parsed

    def _fallback(self) -> dict:
        return {
            "intent": "UNKNOWN",
            "product_term": None,
            "quantity": {
                "value": None,
                "value_origin": "NOT_INFORMED",
                "unit": None,
                "unit_origin": "NOT_INFORMED"
            },
            "explicit_presentation": None,
            "explicit_brand": None,
            "contextual_references": [],
            "missing_information": [],
            "catalog_candidates": [],
            "product_resolution_status": "NOT_FOUND"
        }

    @property
    def name(self) -> str:
        return "NuExtract-tiny-1.5"