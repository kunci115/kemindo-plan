"""Chemical reasoning engine. DETERMINISTIC — not LLM.

The agent calls these as tools so dosage/stoichiometry never gets hallucinated.
Formulas are standard process-metallurgy / water-treatment heuristics. Demo
ranges; a site metallurgist must validate before field use.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

# ---- unit conversion ----
_MASS_TO_KG = {"mg": 1e-6, "g": 1e-3, "kg": 1.0, "ton": 1000.0, "mt": 1000.0, "t": 1000.0}


def convert_mass(value: float, frm: str, to: str) -> float:
    frm, to = frm.lower(), to.lower()
    if frm not in _MASS_TO_KG or to not in _MASS_TO_KG:
        raise ValueError(f"unknown mass unit: {frm} or {to}")
    return value * _MASS_TO_KG[frm] / _MASS_TO_KG[to]


@dataclass
class DosageResult:
    product: str
    basis: str
    dose_low: float
    dose_high: float
    unit: str
    total_low: float | None
    total_high: float | None
    total_unit: str | None
    note: str
    validate: str = "Validate with site metallurgist + product SDS before field use."

    def dict(self) -> dict[str, Any]:
        return asdict(self)


def dosage_lime_ph(ore_tons_per_day: float | None = None,
                   target_ph: float = 11.0) -> DosageResult:
    """Lime (Ca(OH)2) for CIL/CIP pH control. Heuristic 0.5-2.0 kg/t ore,
    skewed by target pH within the leach window 10.5-11.5."""
    span = max(0.0, min(1.0, (target_ph - 10.5) / 1.0))
    low = 0.5 + span * 0.5     # 0.5 -> 1.0
    high = 1.5 + span * 0.5    # 1.5 -> 2.0
    tl = th = None
    if ore_tons_per_day:
        tl = round(low * ore_tons_per_day, 1)
        th = round(high * ore_tons_per_day, 1)
    return DosageResult(
        product="Hydrated Lime Ca(OH)2 (P001)", basis="per ton ore",
        dose_low=round(low, 2), dose_high=round(high, 2), unit="kg/t",
        total_low=tl, total_high=th, total_unit="kg/day" if tl else None,
        note=f"Target leach pH {target_ph} (window 10.5-11.5). Higher pH avoids "
             f"HCN loss/safety but over-liming wastes reagent.",
    )


def dosage_activated_carbon(slurry_m3: float | None = None,
                            concentration_g_per_l: float = 20.0) -> DosageResult:
    low_c, high_c = 15.0, 25.0
    tl = th = None
    if slurry_m3:
        tl = round(low_c * slurry_m3, 1)   # g/L * m3 = kg (since 1 m3=1000 L, g*1000/1000)
        th = round(high_c * slurry_m3, 1)
    return DosageResult(
        product="Activated Carbon (P003)", basis="carbon concentration in tanks",
        dose_low=low_c, dose_high=high_c, unit="g/L",
        total_low=tl, total_high=th, total_unit="kg (inventory in circuit)" if tl else None,
        note="Coconut-shell, iodine no. >=1000. Check activity/fouling if recovery drops.",
    )


def dosage_hpal_acid(ore_tons_per_day: float | None = None) -> DosageResult:
    low, high = 250.0, 400.0  # kg H2SO4 per ton dry ore
    tl = th = None
    if ore_tons_per_day:
        tl = round(low * ore_tons_per_day / 1000, 1)
        th = round(high * ore_tons_per_day / 1000, 1)
    return DosageResult(
        product="Sulfuric Acid H2SO4 98% (P008)", basis="per ton dry ore (HPAL)",
        dose_low=low, dose_high=high, unit="kg/t",
        total_low=tl, total_high=th, total_unit="MT/day" if tl else None,
        note="HPAL nickel leaching. Highly ore-dependent (acid demand from gangue).",
    )


def dosage_smbs_detox(wad_cn_kg_per_day: float | None = None) -> DosageResult:
    """SMBS for SO2/air cyanide detox. ~2.5-5.0 g SMBS per g WAD CN."""
    low, high = 2.5, 5.0
    tl = th = None
    if wad_cn_kg_per_day:
        tl = round(low * wad_cn_kg_per_day, 1)
        th = round(high * wad_cn_kg_per_day, 1)
    return DosageResult(
        product="Sodium Metabisulfite (P010)", basis="per unit WAD cyanide",
        dose_low=low, dose_high=high, unit="g SMBS / g WAD CN",
        total_low=tl, total_high=th, total_unit="kg/day" if tl else None,
        note="SO2/air (INCO) detox. Needs Cu catalyst + pH ~8-9 + aeration.",
    )


# registry for the agent tool dispatcher
DOSAGE_FUNCS = {
    "lime_ph": dosage_lime_ph,
    "activated_carbon": dosage_activated_carbon,
    "hpal_acid": dosage_hpal_acid,
    "smbs_detox": dosage_smbs_detox,
}


def stoichiometry_neutralization(acid_kg: float, acid: str = "H2SO4",
                                 base: str = "Ca(OH)2") -> dict[str, Any]:
    """Mass of base to neutralize a given acid mass (molar-equivalent)."""
    MW = {"H2SO4": 98.08, "HCl": 36.46, "Ca(OH)2": 74.09, "NaOH": 40.0}
    EQ = {"H2SO4": 2, "HCl": 1, "Ca(OH)2": 2, "NaOH": 1}
    if acid not in MW or base not in MW:
        raise ValueError("supported: acids H2SO4/HCl, bases Ca(OH)2/NaOH")
    eq_acid = acid_kg / MW[acid] * EQ[acid]            # kmol equivalents
    base_kg = eq_acid / EQ[base] * MW[base]
    return {
        "acid": acid, "acid_kg": acid_kg, "base": base,
        "base_kg_required": round(base_kg, 2),
        "note": "Molar-equivalent stoichiometry, 100% purity basis. "
                "Divide by actual purity (e.g. /0.90 for 90% lime).",
    }
