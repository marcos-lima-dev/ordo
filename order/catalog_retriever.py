import json
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from difflib import get_close_matches

PRESENTATION_TERMS = {
    "forma", "formas", "barra", "barras", "bloco", "blocos",
    "bisnaga", "bisnagas", "peça", "peças", "pote", "potes",
    "saco", "sacos", "garrafa", "garrafas", "caixa", "caixas",
    "balde", "baldes", "pacote", "pacotes", "fração", "vácuo",
    "unidade", "triângulo", "cartela", "cartelas"
}

STOPWORDS = {
    "quero", "me", "manda", "coloca", "bota", "gostaria", "preciso",
    "de", "da", "do", "das", "dos", "a", "o", "as", "os",
    "um", "uma", "uns", "umas", "para", "por", "com", "sem",
    "e", "ou", "que", "qual", "quais",
    "também", "tambem", "mais", "so", "só",
}

QUANTITY_PATTERN = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:kg|quilos|quilo|k|g|gramas|l|litros)?",
    re.IGNORECASE,
)


def normalize_term(term: str) -> str:
    if term.endswith("s") and len(term) > 3:
        return term[:-1]
    return term


def normalize_query(message: str) -> str:
    """
    Remove ruído conversacional: verbos, quantidades, unidades, stopwords, apresentações.
    Retorna string vazia se não sobrar evidência lexical de produto.
    """
    text = message.lower()
    text = QUANTITY_PATTERN.sub(" ", text)
    tokens = re.findall(r"[a-záéíóúãõçâêôûî]{3,}", text)
    tokens = [
        t for t in tokens
        if t not in STOPWORDS
        and t not in PRESENTATION_TERMS
        and normalize_term(t) not in PRESENTATION_TERMS
    ]
    return " ".join(tokens)


class CatalogRetriever:
    def __init__(self):
        self.catalog = self._load_catalog()
        self.aliases = self._load_aliases()
        self._build_indexes()

    def _load_catalog(self):
        path = Path("data/catalog.json")
        with open(path) as f:
            return json.load(f)

    def _load_aliases(self):
        path = Path("data/aliases.json")
        with open(path) as f:
            return json.load(f)

    def _build_indexes(self):
        self.alias_to_product = {}
        for alias in self.aliases:
            text = alias["alias_text"].lower()
            product_id = alias["product_id"]
            if text not in self.alias_to_product:
                self.alias_to_product[text] = []
            self.alias_to_product[text].append(product_id)

        self.name_to_product = {}
        for product in self.catalog:
            name = product["normalized_name"].lower()
            pid = product["product_id"]
            if name not in self.name_to_product:
                self.name_to_product[name] = []
            self.name_to_product[name].append(pid)

        self.original_to_product = {}
        for product in self.catalog:
            orig = product.get("original_name", "").lower()
            pid = product["product_id"]
            if orig:
                if orig not in self.original_to_product:
                    self.original_to_product[orig] = []
                self.original_to_product[orig].append(pid)

        self.brand_to_product = {}
        for product in self.catalog:
            brand = product["brand"].lower()
            pid = product["product_id"]
            if brand not in self.brand_to_product:
                self.brand_to_product[brand] = []
            self.brand_to_product[brand].append(pid)

    def retrieve(self, query: str) -> List[str]:
        """Interface compatível. Usa proveniência internamente."""
        candidates, _ = self.retrieve_with_provenance(query)
        return candidates

    def retrieve_with_provenance(
        self,
        query: str,
        brand: Optional[str] = None,
        presentation: Optional[str] = None,
    ) -> Tuple[List[str], Dict[str, str]]:
        """
        Retorna (candidatos, proveniência).
        CR-01: query vazia após normalização → []
        CR-03: preserva evidência original + normalizada (não substitutiva).
        Ordem determinística: ORIGINAL em ordem de descoberta, depois NORMALIZED-only.
        Constraints de brand/presentation filtram SEM perder proveniência.
        """
        original_normalized = normalize_query(query)
        if not original_normalized:
            # CR-01: não há evidência lexical de produto
            return [], {}

        candidates_original, prov_original = self._retrieve_core(query, "ORIGINAL")
        candidates_normalized, prov_normalized = self._retrieve_core(
            original_normalized, "NORMALIZED"
        )

        # União determinística: ORIGINAL primeiro (ordem de descoberta), depois NORMALIZED-only
        ordered: List[str] = []
        seen = set()
        provenance: Dict[str, str] = {}
        for cid in candidates_original:
            if cid not in seen:
                ordered.append(cid)
                seen.add(cid)
                provenance[cid] = prov_original.get(cid, "ORIGINAL_MATCH")
        for cid in candidates_normalized:
            if cid not in seen:
                ordered.append(cid)
                seen.add(cid)
                provenance[cid] = prov_normalized.get(cid, "NORMALIZED_MATCH")

        # Constraints de brand/presentation (preservam proveniência)
        if brand:
            brand_lower = brand.lower()
            ordered = [
                cid for cid in ordered
                if (p := self._get_product_by_id(cid))
                and brand_lower in p["brand"].lower()
            ]

        if presentation:
            pres_lower = presentation.lower()
            ordered = [
                cid for cid in ordered
                if (p := self._get_product_by_id(cid))
                and pres_lower in p["apresentacao_individual"].lower()
            ]

        return ordered, {cid: provenance[cid] for cid in ordered if cid in provenance}

    def _retrieve_core(self, query: str, source: str) -> Tuple[List[str], Dict[str, str]]:
        """Motor de recuperação. Nunca chamado com query vazia."""
        q = query.lower().strip()
        if not q:
            return [], {}

        tokens = q.split()

        presentation_filter = None
        for token in tokens:
            if token in PRESENTATION_TERMS:
                presentation_filter = normalize_term(token)
                break

        product_tokens = [
            t for t in tokens
            if normalize_term(t) not in PRESENTATION_TERMS
        ]
        product_query = " ".join(product_tokens)

        candidates: Dict[str, str] = {}

        # 1. Alias exato
        if product_query in self.alias_to_product:
            for cid in self.alias_to_product[product_query]:
                candidates.setdefault(cid, f"{source}_ALIAS_EXACT")

        # 2. Nome normalizado exato
        if product_query in self.name_to_product:
            for cid in self.name_to_product[product_query]:
                candidates.setdefault(cid, f"{source}_NAME_EXACT")

        # 3. Original name exato
        if product_query in self.original_to_product:
            for cid in self.original_to_product[product_query]:
                candidates.setdefault(cid, f"{source}_ORIGINAL_EXACT")

        # 4. Token overlap (só se houver product_tokens não-vazios)
        if product_tokens:
            for alias, ids in self.alias_to_product.items():
                alias_tokens = alias.split()
                if all(t in alias_tokens for t in product_tokens):
                    for cid in ids:
                        candidates.setdefault(cid, f"{source}_ALIAS_TOKEN")
                elif all(t in product_tokens for t in alias_tokens):
                    for cid in ids:
                        candidates.setdefault(cid, f"{source}_ALIAS_SUBSET")

            for name, ids in self.name_to_product.items():
                name_tokens = name.split()
                if all(t in name_tokens for t in product_tokens):
                    for cid in ids:
                        candidates.setdefault(cid, f"{source}_NAME_TOKEN")
                elif all(t in product_tokens for t in name_tokens):
                    for cid in ids:
                        candidates.setdefault(cid, f"{source}_NAME_SUBSET")

            # Fuzzy SÓ quando há tokens (nunca em query vazia)
            if not candidates:
                all_aliases = list(self.alias_to_product.keys())
                matches = get_close_matches(product_query, all_aliases, n=3, cutoff=0.8)
                for match in matches:
                    for cid in self.alias_to_product[match]:
                        candidates.setdefault(cid, f"{source}_ALIAS_FUZZY")

        # 5. Filtro de apresentação
        if presentation_filter:
            filtered = {}
            for cid, prov in candidates.items():
                product = self._get_product_by_id(cid)
                if product:
                    apres = product["apresentacao_individual"].lower()
                    if (
                        presentation_filter in apres
                        or normalize_term(apres) == presentation_filter
                    ):
                        filtered[cid] = prov
            candidates = filtered

        return list(candidates.keys()), candidates

    def retrieve_with_constraints(
        self, query: str, brand: Optional[str] = None, presentation: Optional[str] = None
    ) -> List[str]:
        """Wrapper de compatibilidade. Prefira retrieve_with_provenance()."""
        candidates, _ = self.retrieve_with_provenance(
            query, brand=brand, presentation=presentation
        )
        return candidates

    def _get_product_by_id(self, product_id: str):
        for product in self.catalog:
            if product["product_id"] == product_id:
                return product
        return None