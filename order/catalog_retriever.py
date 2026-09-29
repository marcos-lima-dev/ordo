import json
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from difflib import get_close_matches

from order.evidence import Evidence


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
        self.alias_records = {}  # (alias_text_lower, product_id) -> record
        for alias in self.aliases:
            text = alias["alias_text"].lower()
            product_id = alias["product_id"]
            if text not in self.alias_to_product:
                self.alias_to_product[text] = []
            self.alias_to_product[text].append(product_id)
            self.alias_records[(text, product_id)] = alias

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

    def _add_evidence(
        self,
        candidates: Dict[str, List[Evidence]],
        cid: str,
        stream: str,
        match_kind: str,
        match_strength: str,
        alias_text: Optional[str] = None,
    ) -> None:
        """
        Append a structured Evidence to the candidate's list.
        Insertion order of the SKU key is preserved (setdefault-created
        on first match), matching legacy retrieval order.
        """
        kwargs = {
            "sku": cid,
            "stream": stream,
            "match_kind": match_kind,
            "match_strength": match_strength,
        }
        if match_kind == "ALIAS" and alias_text is not None:
            rec = self.alias_records.get((alias_text, cid))
            if rec is not None:
                kwargs["source"] = rec.get("source")
                kwargs["approved"] = rec.get("approved")
        candidates.setdefault(cid, []).append(Evidence(**kwargs))

    def _retrieve_core(
        self, query: str, source: str
    ) -> Tuple[List[str], Dict[str, List[Evidence]]]:
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

        candidates: Dict[str, List[Evidence]] = {}

        # 1. Alias exato
        if product_query in self.alias_to_product:
            for cid in self.alias_to_product[product_query]:
                self._add_evidence(
                    candidates, cid, source, "ALIAS", "EXACT", product_query
                )

        # 2. Nome normalizado exato
        if product_query in self.name_to_product:
            for cid in self.name_to_product[product_query]:
                self._add_evidence(candidates, cid, source, "NAME", "EXACT")

        # 3. Original name exato
        if product_query in self.original_to_product:
            for cid in self.original_to_product[product_query]:
                self._add_evidence(
                    candidates, cid, source, "ORIGINAL_NAME", "EXACT"
                )

        # 4. Token overlap (só se houver product_tokens não-vazios)
        if product_tokens:
            for alias, ids in self.alias_to_product.items():
                alias_tokens = alias.split()
                if all(t in alias_tokens for t in product_tokens):
                    for cid in ids:
                        self._add_evidence(
                            candidates, cid, source, "ALIAS", "TOKEN", alias
                        )
                elif all(t in product_tokens for t in alias_tokens):
                    for cid in ids:
                        self._add_evidence(
                            candidates, cid, source, "ALIAS", "SUBSET", alias
                        )

            for name, ids in self.name_to_product.items():
                name_tokens = name.split()
                if all(t in name_tokens for t in product_tokens):
                    for cid in ids:
                        self._add_evidence(candidates, cid, source, "NAME", "TOKEN")
                elif all(t in product_tokens for t in name_tokens):
                    for cid in ids:
                        self._add_evidence(candidates, cid, source, "NAME", "SUBSET")

            # Fuzzy SÓ quando há tokens (nunca em query vazia)
            if not candidates:
                all_aliases = list(self.alias_to_product.keys())
                matches = get_close_matches(product_query, all_aliases, n=3, cutoff=0.8)
                for match in matches:
                    for cid in self.alias_to_product[match]:
                        self._add_evidence(
                            candidates, cid, source, "ALIAS", "FUZZY", match
                        )

        # 5. Filtro de apresentação
        if presentation_filter:
            filtered = {}
            for cid, ev_list in candidates.items():
                product = self._get_product_by_id(cid)
                if product:
                    apres = product["apresentacao_individual"].lower()
                    if (
                        presentation_filter in apres
                        or normalize_term(apres) == presentation_filter
                    ):
                        filtered[cid] = ev_list
            candidates = filtered

        return list(candidates.keys()), candidates

    def retrieve_with_provenance(
        self,
        query: str,
        brand: Optional[str] = None,
        presentation: Optional[str] = None,
    ) -> Tuple[List[str], Dict[str, List[Evidence]]]:
        """
        Retorna (candidatos, evidências).
        CR-01: query vazia após normalização → []
        CR-03: preserva evidência original + normalizada (não substitutiva).
        Ordem determinística: ORIGINAL em ordem de descoberta, depois NORMALIZED-only.

        P101: para o MESMO SKU, evidências de ambos os streams são acumuladas
        na mesma lista — nenhuma evidência positiva é descartada pela agregação.
        P102: nunca promover (nenhum stream positivo → lista permanece não-positiva).
        P103: nunca cruzar SKUs (cada SKU tem sua própria lista).
        """
        original_normalized = normalize_query(query)
        if not original_normalized:
            return [], {}

        candidates_original, ev_original = self._retrieve_core(query, "ORIGINAL")
        candidates_normalized, ev_normalized = self._retrieve_core(
            original_normalized, "NORMALIZED"
        )

        ordered: List[str] = []
        seen = set()
        provenance: Dict[str, List[Evidence]] = {}
        for cid in candidates_original:
            if cid not in seen:
                ordered.append(cid)
                seen.add(cid)
                provenance[cid] = list(ev_original.get(cid, []))
        for cid in candidates_normalized:
            if cid not in seen:
                ordered.append(cid)
                seen.add(cid)
                provenance[cid] = list(ev_normalized.get(cid, []))
            else:
                # Same SKU across streams: extend, never replace.
                provenance[cid].extend(ev_normalized.get(cid, []))

        # Constraints de brand/presentation (preservam evidência)
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

        return (
            ordered,
            {cid: provenance[cid] for cid in ordered if cid in provenance},
        )

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