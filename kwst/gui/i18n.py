"""Lokalizacja interfejsu. Językiem podstawowym jest polski; angielski — opcjonalnie.

Teksty interfejsu są pisane po polsku i tłumaczone słownikiem ``EN``. Brak
tłumaczenia → tekst polski (nigdy pusty). Treść raportu i komunikaty silnika
obliczeniowego pozostają w języku polskim (język dokumentacji projektowej).
"""
from __future__ import annotations

_LANG = "pl"

EN = {
    # menu
    "&Plik": "&File", "&Edycja": "&Edit", "&Obliczenia": "&Analysis", "&Widok": "&View", "&Pomoc": "&Help",
    "Nowy projekt": "New project", "Otwórz…": "Open…", "Zapisz": "Save", "Zapisz jako…": "Save as…",
    "Biblioteka typowych wsporników…": "Library of typical corbels…", "Import obciążeń (CSV/Excel)…":
    "Import loads (CSV/Excel)…", "Eksport": "Export", "Raport PDF…": "PDF report…", "Arkusz Excel…": "Excel workbook…",
    "Sprawdzenia CSV…": "Checks CSV…", "Dane i wyniki JSON…": "Data and results JSON…", "Rysunek DXF…": "DXF drawing…",
    "Podgląd wydruku…": "Print preview…", "Ostatnie pliki": "Recent files", "Odzyskaj autozapis…": "Recover autosave…",
    "Zakończ": "Exit", "Cofnij": "Undo", "Ponów": "Redo", "Kopiuj wariant": "Duplicate variant",
    "Usuń wariant": "Delete variant", "Zmień nazwę wariantu…": "Rename variant…", "Ustawienia…": "Settings…",
    "Oblicz": "Calculate", "Obliczenia automatyczne": "Automatic calculation",
    "Przenieś dobrane zbrojenie do danych": "Apply designed reinforcement to input",
    "Optymalizacja…": "Optimisation…", "Zestawienie stali…": "Bar schedule…", "Geometria": "Geometry",
    "Model STM": "STM model", "Naprężenia / wykorzystanie": "Stresses / utilisation", "Zbrojenie": "Reinforcement",
    "Warstwy": "Layers", "Dopasuj widok": "Fit view", "Podświetl element krytyczny": "Highlight critical element",
    "Edycja uchwytami": "Edit with handles", "Narzędzie pomiaru": "Measure tool", "Motyw ciemny": "Dark theme",
    "Skala interfejsu": "UI scale", "Język": "Language", "Jednostki": "Units",
    "Pomoc — parametry": "Help — parameters", "Model obliczeniowy i ograniczenia": "Calculation model and limitations",
    "Status walidacji modułów": "Module validation status", "O programie": "About",
    # docki i zakładki
    "Dane wejściowe": "Input data", "Wyniki": "Results", "Szczegółowe obliczenia": "Detailed calculations",
    "Materiały": "Materials", "Obciążenia": "Loads", "Parametry normowe": "Code parameters",
    "Wariant:": "Variant:", "Kombinacja:": "Combination:", "Widok:": "View:",
    # wyniki
    "Werdykt": "Verdict", "Element krytyczny": "Critical element", "Komunikaty": "Messages",
    "Wykorzystanie": "Utilisation", "Szczegóły elementu": "Element details", "Siły wewnętrzne": "Internal forces",
    "Sprawdzenie": "Check", "Podstawa": "Basis", "Status": "Status", "Filtr:": "Filter:",
    "Wszystkie": "All", "Niespełnione": "Not satisfied", "Wymagające weryfikacji": "Requiring verification",
    "Spełnione": "Satisfied", "Wyniki nieaktualne — uruchom obliczenia (F5)": "Results out of date — run analysis (F5)",
    "Dodaj": "Add", "Usuń": "Remove", "Import…": "Import…", "Eksport CSV…": "Export CSV…",
    "Kopiuj z modelu automatycznego": "Copy from automatic model",
}

STATUS_EN = {"SPEŁNIONO": "SATISFIED", "NIE SPEŁNIONO": "NOT SATISFIED",
             "WYMAGA OSOBNEJ WERYFIKACJI": "SEPARATE VERIFICATION", "NIE DOTYCZY": "N/A"}


def set_language(lang: str) -> None:
    global _LANG
    _LANG = "en" if lang == "en" else "pl"


def language() -> str:
    return _LANG


def tr(text: str) -> str:
    if _LANG == "en":
        return EN.get(text, text)
    return text


def tr_status(status: str) -> str:
    return STATUS_EN.get(status, status) if _LANG == "en" else status
