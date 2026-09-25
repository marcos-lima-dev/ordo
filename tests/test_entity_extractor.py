import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.entity_extractor import EntityExtractor


class _FakeModel:
    def __init__(self, entities=None):
        self.entities = entities if entities is not None else []
        self.calls = []

    def predict_entities(self, message, labels, threshold):
        self.calls.append((message, list(labels), threshold))
        return self.entities


# =============================================
# EE-01 — extraction contract
# =============================================

def test_ee01_returns_list():
    model = _FakeModel(entities=[{"label": "produto", "text": "brie"}])
    extractor = EntityExtractor(model=model)
    result = extractor.extract_entities("manda brie", ("produto",))
    assert isinstance(result, list)
    assert result == [{"label": "produto", "text": "brie"}]


def test_ee01b_passes_labels_and_threshold():
    model = _FakeModel()
    extractor = EntityExtractor(model=model)
    extractor.extract_entities(
        "msg", ("produto", "marca"), threshold=0.42,
    )
    assert model.calls == [("msg", ["produto", "marca"], 0.42)]


def test_ee01c_default_threshold_is_0_3():
    model = _FakeModel()
    extractor = EntityExtractor(model=model)
    extractor.extract_entities("msg", ("produto",))
    assert model.calls[0][2] == 0.3


def test_ee01d_empty_returns_empty_list():
    model = _FakeModel(entities=[])
    extractor = EntityExtractor(model=model)
    assert extractor.extract_entities("", ("produto",)) == []


# =============================================
# EE-02 — shared model instance
# =============================================

def test_ee02_two_extractors_share_model(monkeypatch):
    fake_instance = object()
    calls = []

    def fake_from_pretrained(name):
        calls.append(name)
        return fake_instance

    monkeypatch.setattr("pipeline.entity_extractor._INSTANCES", {})
    monkeypatch.setattr(
        "pipeline.entity_extractor.GLiNER",
        type(
            "F",
            (),
            {"from_pretrained": staticmethod(fake_from_pretrained)},
        ),
    )

    a = EntityExtractor()
    b = EntityExtractor()
    assert a._model is b._model is fake_instance
    assert calls == ["urchade/gliner_medium"]


def test_ee02b_different_names_distinct_instances(monkeypatch):
    registry = {}

    def fake_from_pretrained(name):
        registry.setdefault(name, object())
        return registry[name]

    monkeypatch.setattr("pipeline.entity_extractor._INSTANCES", {})
    monkeypatch.setattr(
        "pipeline.entity_extractor.GLiNER",
        type(
            "F",
            (),
            {"from_pretrained": staticmethod(fake_from_pretrained)},
        ),
    )

    a = EntityExtractor(model_name="model-a")
    b = EntityExtractor(model_name="model-b")
    assert a._model is not b._model
    assert a._model is registry["model-a"]
    assert b._model is registry["model-b"]


def test_ee02c_injected_model_bypasses_singleton(monkeypatch):
    fake_instance = object()
    monkeypatch.setattr("pipeline.entity_extractor._INSTANCES", {})
    injected = object()
    extractor = EntityExtractor(model=injected)
    assert extractor._model is injected