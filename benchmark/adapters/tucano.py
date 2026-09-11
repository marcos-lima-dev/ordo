import json
import re
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from .base import CandidateAdapter, register_adapter

@register_adapter("tucano")
class TucanoAdapter(CandidateAdapter):
    def __init__(self, model_size="0.5B", device="cpu"):
        model_map = {
            "0.5B": "Polygl0t/Tucano2-qwen-0.5B-Instruct",
            "1.5B": "Polygl0t/Tucano2-qwen-1.5B-Instruct",
            "3.7B": "Polygl0t/Tucano2-qwen-3.7B-Instruct",
        }
        self.model_size = model_size
        self.model_name = model_map.get(model_size, model_map["0.5B"])
        self.device = device
        print(f"Carregando modelo {self.model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype="auto",
            device_map=device
        )
        self._load_prompt()

    def _load_prompt(self):
        prompt_path = Path("prompts/semantic_interpreter_v1.txt")
        if prompt_path.exists():
            with open(prompt_path) as f:
                self.system_prompt = f.read()
        else:
            self.system_prompt = (
                "Você é um interpretador semântico de pedidos para uma distribuidora de queijos. "
                "Extraia as informações e retorne apenas JSON válido. "
                "A mensagem do cliente é:\n"
            )

    def predict(self, message: str) -> dict:
        full_prompt = f"{self.system_prompt}\n\n{message}\n\nResposta (apenas o JSON):"
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
            start = text.find('{')
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
        return f"Tucano2-{self.model_size}"