"""Eksport parametrów normowych i tablic z modułu Python do web/normdata.js.

Jedno źródło prawdy: kwst/normative_parameters.py (oraz katalogi materiałów). Silnik JavaScript
(web/engine.js) korzysta z wygenerowanego pliku — wartości nie są przepisywane ręcznie."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kwst.normative_parameters import (EDITIONS, TABLE_3_1, TABLE_4_4N, EXPOSURE_GROUP, STRUCTURAL_CLASSES,  # noqa: E402
                                       TABLE_7_2N, TABLE_7_3N, TABLE_10_2, PSI_TABLE, CATEGORY_LABEL)
from kwst.material_engine import STEEL_GRADES, DUCTILITY_CLASSES  # noqa: E402
from kwst.core.model import (Variant, ProjectInfo, LoadAction, LoadCombination, ManualNode, ManualMember,  # noqa: E402
                             ManualSupport, ManualLoad, SCHEMA_VERSION)
from kwst.core.serialization import to_dict  # noqa: E402


def main() -> None:
    eds = {}
    for k, e in EDITIONS.items():
        eds[k] = {
            "id": e.id, "title": e.title, "implemented": e.implemented, "description": e.description,
            "params": [{
                "key": p.key, "symbol": p.symbol, "value": p.value, "unit": p.unit, "clause": p.clause,
                "category": p.category, "description": p.description, "recommended": p.recommended,
                "na_note": p.na_note, "status": p.status, "blocking": p.blocking, "editable": p.editable,
            } for p in e.params.values()],
        }
    data = {
        "editions": eds,
        "categoryLabel": CATEGORY_LABEL,
        "t31": TABLE_3_1,
        "t44N": {k: list(v) for k, v in TABLE_4_4N.items()},
        "expGroup": EXPOSURE_GROUP,
        "structClasses": list(STRUCTURAL_CLASSES),
        "t72N": {str(k): list(v) for k, v in TABLE_7_2N.items()},
        "t73N": {str(k): list(v) for k, v in TABLE_7_3N.items()},
        "t102": {k: list(v) for k, v in TABLE_10_2.items()},
        "psi": {k: list(v) for k, v in PSI_TABLE.items()},
        "steelGrades": {k: list(v) for k, v in STEEL_GRADES.items()},
        "ductility": {k: list(v) for k, v in DUCTILITY_CLASSES.items()},
        "defaults": {
            "schema_version": SCHEMA_VERSION,
            "variant": to_dict(Variant()), "info": to_dict(ProjectInfo()), "action": to_dict(LoadAction()),
            "combination": to_dict(LoadCombination()), "node": to_dict(ManualNode()), "member": to_dict(ManualMember()),
            "support": to_dict(ManualSupport()), "load": to_dict(ManualLoad()),
        },
    }
    js = ("/* WYGENEROWANE przez tools/export_normdata.py z kwst/normative_parameters.py — nie edytować ręcznie. */\n"
          "(function (g) { g.WSN_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + "; })"
          "(typeof window !== 'undefined' ? window : globalThis);\n")
    out = ROOT / "web" / "normdata.js"
    out.write_text(js, encoding="utf-8")
    print(out, len(js), "B")


if __name__ == "__main__":
    main()
