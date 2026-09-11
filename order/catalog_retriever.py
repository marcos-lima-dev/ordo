# order/catalog_retriever.py
import json
from pathlib import Path
from typing import List, Set, Optional
import re
from difflib import get_close_matches

PRESENTATION_TERMS = {
    "forma", "formas", "barra", "barras", "bloco", "blocos",
    "bisnaga", "bisnagas", "peça", "peças", "pote", "potes",
    "saco", "sacos", "garrafa", "garrafas", "caixa", "caixas",
    "balde", "baldes", "pacote", "pacotes", "fração", "vácuo",
    "unidade", "triângulo", "cartela", "cartelas"
}

def normalize_term(term: str) -> str:
    """Remove plural e normaliza para singular."""
    if term.endswith("s") and len(term) > 3:
        return term[:-1]
    return term

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
        # Alias → product_ids
        self.alias_to_product = {}
        for alias in self.aliases:
            text = alias["alias_text"].lower()
            product_id = alias["product_id"]
            if text not in self.alias_to_product:
                self.alias_to_product[text] = []
            self.alias_to_product[text].append(product_id)
        
        # Nome normalizado → product_id
        self.name_to_product = {}
        for product in self.catalog:
            name = product["normalized_name"].lower()
            pid = product["product_id"]
            if name not in self.name_to_product:
                self.name_to_product[name] = []
            self.name_to_product[name].append(pid)
        
        # Original name → product_id
        self.original_to_product = {}
        for product in self.catalog:
            orig = product.get("original_name", "").lower()
            pid = product["product_id"]
            if orig:
                if orig not in self.original_to_product:
                    self.original_to_product[orig] = []
                self.original_to_product[orig].append(pid)
        
        # Marca → product_ids
        self.brand_to_product = {}
        for product in self.catalog:
            brand = product["brand"].lower()
            pid = product["product_id"]
            if brand not in self.brand_to_product:
                self.brand_to_product[brand] = []
            self.brand_to_product[brand].append(pid)
    
    def retrieve(self, query: str) -> List[str]:
        query_lower = query.lower()
        tokens = query_lower.split()
        
        # Detecta apresentação
        presentation_filter = None
        for token in tokens:
            if token in PRESENTATION_TERMS:
                presentation_filter = normalize_term(token)
                break
        
        # Remove termos de apresentação
        product_tokens = [t for t in tokens if normalize_term(t) not in PRESENTATION_TERMS]
        product_query = " ".join(product_tokens) if product_tokens else query_lower
        
        candidates = set()
        
        # 1. Busca por alias exato
        if product_query in self.alias_to_product:
            candidates.update(self.alias_to_product[product_query])
        
        # 2. Busca fuzzy (para erros de digitação)
        if not candidates:
            all_aliases = list(self.alias_to_product.keys())
            matches = get_close_matches(product_query, all_aliases, n=3, cutoff=0.8)
            for match in matches:
                candidates.update(self.alias_to_product[match])
        
        # 3. Busca por tokens no alias
        for alias, ids in self.alias_to_product.items():
            alias_tokens = alias.split()
            if all(t in alias_tokens for t in product_tokens):
                candidates.update(ids)
            elif all(t in product_tokens for t in alias_tokens):
                candidates.update(ids)
        
        # 4. Busca por nome normalizado (tokenizado e fuzzy)
        for name, ids in self.name_to_product.items():
            name_tokens = name.split()
            if all(t in name_tokens for t in product_tokens):
                candidates.update(ids)
            elif all(t in product_tokens for t in name_tokens):
                candidates.update(ids)
            elif product_query in name:
                candidates.update(ids)
        
        # 5. Busca por original_name (para produtos com parênteses)
        for orig, ids in self.original_to_product.items():
            if product_query in orig:
                candidates.update(ids)
        
        # 6. Busca por marca
        for brand, ids in self.brand_to_product.items():
            if product_query in brand or brand in product_query:
                candidates.update(ids)
        
        # 7. Se nada encontrou, tenta uma última busca fuzzy no nome
        if not candidates:
            all_names = list(self.name_to_product.keys())
            matches = get_close_matches(product_query, all_names, n=3, cutoff=0.7)
            for match in matches:
                candidates.update(self.name_to_product[match])
        
        # 8. Filtra por apresentação
        if presentation_filter:
            filtered = []
            for cid in candidates:
                product = self._get_product_by_id(cid)
                if product:
                    apres = product["apresentacao_individual"].lower()
                    if presentation_filter in apres or normalize_term(apres) == presentation_filter:
                        filtered.append(cid)
            candidates = set(filtered)
        
        return list(candidates)
    
    def retrieve_with_constraints(self, query: str, brand: Optional[str] = None, presentation: Optional[str] = None) -> List[str]:
        candidates = self.retrieve(query)
        if brand:
            brand_lower = brand.lower()
            filtered = []
            for cid in candidates:
                product = self._get_product_by_id(cid)
                if product and brand_lower in product["brand"].lower():
                    filtered.append(cid)
            candidates = filtered
        if presentation:
            pres_lower = presentation.lower()
            filtered = []
            for cid in candidates:
                product = self._get_product_by_id(cid)
                if product and pres_lower in product["apresentacao_individual"].lower():
                    filtered.append(cid)
            candidates = filtered
        return candidates
    
    def _get_product_by_id(self, product_id: str):
        for product in self.catalog:
            if product["product_id"] == product_id:
                return product
        return None