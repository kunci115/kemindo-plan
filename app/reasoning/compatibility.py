"""Chemical compatibility / storage-safety check. DETERMINISTIC.

Flags hazardous co-storage among recommended/quoted products using hazard class
keywords from products.json. This is the kind of domain depth that impresses
process engineers — the copilot won't recommend storing an oxidizer next to a
flammable solid.

Reference: standard segregation matrix (oxidizers / acids / bases / flammable /
water-reactive). Demo-grade; defer to site HSE + SDS for compliance.
"""
from __future__ import annotations
from typing import Any

# coarse class detection from the hazard_class free-text field
_CLASSES = {
    "oxidizer": ["oxidi"],
    "flammable": ["flammable"],
    "acid": ["corrosive", "acid"],
    "base": ["corrosive"],          # refined below by formula
    "water_reactive": ["dangerous when wet", "water"],
    "toxic": ["toxic", "harmful", "env-hazard", "env-hazard"],
}

# pairs that must be segregated (symmetric)
_INCOMPATIBLE = {
    frozenset({"oxidizer", "flammable"}): "Oxidizer + flammable: fire/explosion risk. Segregate.",
    frozenset({"oxidizer", "acid"}): "Oxidizer + acid: may release toxic gas / violent reaction. Segregate.",
    frozenset({"acid", "base"}): "Acid + base: exothermic neutralization on contact. Segregate.",
    frozenset({"water_reactive", "acid"}): "Water-reactive + aqueous acid: gas evolution. Segregate.",
    frozenset({"water_reactive", "oxidizer"}): "Water-reactive + oxidizer: ignition risk. Segregate.",
    frozenset({"flammable", "acid"}): "Flammable + oxidizing acid: ignition risk. Keep apart.",
}


def classify(product: dict[str, Any]) -> set[str]:
    hz = (product.get("hazard_class") or "").lower()
    formula = (product.get("formula") or "")
    cls: set[str] = set()
    for c, kws in _CLASSES.items():
        if any(k in hz for k in kws):
            cls.add(c)
    # refine acid vs base
    if "acid" in cls and ("OH" in formula or "Ca(OH)" in formula or "NaOH" in formula):
        cls.discard("acid")
        cls.add("base")
    if product.get("name", "").lower().find("acid") >= 0:
        cls.add("acid"); cls.discard("base")
    return cls


def check_pairwise(products: list[dict[str, Any]]) -> dict[str, Any]:
    """Return any incompatible storage pairs among the given products."""
    tagged = [(p, classify(p)) for p in products]
    warnings: list[dict[str, Any]] = []
    for i in range(len(tagged)):
        for j in range(i + 1, len(tagged)):
            (pa, ca), (pb, cb) = tagged[i], tagged[j]
            for x in ca:
                for y in cb:
                    key = frozenset({x, y})
                    if key in _INCOMPATIBLE:
                        warnings.append({
                            "product_a": pa["name"], "product_b": pb["name"],
                            "classes": [x, y],
                            "warning": _INCOMPATIBLE[key],
                        })
    return {
        "checked": [p["name"] for p in products],
        "safe": not warnings,
        "warnings": warnings,
        "note": "Storage-segregation guidance only. Defer to site HSE + SDS for compliance.",
    }
