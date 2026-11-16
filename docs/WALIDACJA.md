# Walidacja i status weryfikacji — KRÓTKI WSPORNIK ST

## 1. Kontrole automatyczne wykonywane przy każdym obliczeniu

| Kontrola | Realizacja |
|---|---|
| Równowaga statyczna | residuum każdego węzła, ΣF_x, ΣF_y, ΣM ≤ tolerancja (1e−6 względnie) |
| Stateczność / wyznaczalność modelu | rząd macierzy równowagi (SVD); mechanizm → blokada wyniku |
| Niezależna weryfikacja sił | rozwiązanie zamknięte modelu J.5 vs solver macierzowy (różnica ≤ 1e−6) |
| Zgodność jednostek | analiza wymiarowa w sprawdzeniach (`Q.expect`), E_d i R_d tej samej wielkości |
| Poprawność geometrii | walidacja danych (dodatniość, a_c < l_c, płyta w obrysie, h_e ≤ h_c, …); pole naprężeń w obrysie |
| Parametry materiałowe | wartości tabl. 3.1 vs wzory tabl. 3.1 (f_ctm, f_ctk, E_cm, f_cm) |
| Współczynniki | 0 < ν' ≤ 1, γ ≥ 1, α_cc ≤ 1; parametry nadpisane wymagają uzasadnienia |
| Dodatniość nośności | R_d ≥ 0, brak NaN |
| Zgodność rysunku z modelem | sygnatura geometrii, współrzędne węzłów, kompletność prętów (`verify_scene`); wyniki nieaktualne → rysunek bez STM |
| Powtarzalność | odcisk wyników (SHA-256 z E_d, R_d, statusów) — identyczny dla identycznych danych |

## 2. Testy automatyczne (`tests/`, 85 testów)

| Plik | Zakres |
|---|---|
| `test_units.py` | konwersje jednostek, analiza wymiarowa, własności prętów |
| `test_materials.py` | tabl. 3.1 dla wszystkich klas, f_cd, ν', granice węzłów/krzyżulców, ograniczenie C60/75, edycje, źródła parametrów |
| `test_loads.py` | (6.10), (6.10a/b), SGU, wartości obliczeniowe bez γ, blokada podwójnych γ, H_min ze źródłem, mimośrody, CSV |
| `test_stm_solver.py` | rozwiązanie analityczne kratownicy, mechanizm, niewyznaczalność (metoda sztywności), błędne modele |
| `test_stm_generator.py` | zgodność z F_td = F·a_c/z0 + H(a_H+z0)/z0, równowaga momentów (tryb w słupie), węzeł hydrostatyczny, w_A, a_ef, optymalność x_c |
| `test_checks.py` | l_bd (8.3)–(8.6), l_b,min, α₁ dla odgięć, (8.1), (8.8N), (6.58)/(6.59), V_Rd,c, otulina, rozstaw — obliczenia ręczne |
| `test_control_cases.py` | 12 przypadków kontrolnych (§2) + wspornik dwustronny, prefabrykat, NDP |
| `test_reproducibility.py` | determinizm, zapis/odczyt bez zmiany wyników, kontrole walidacyjne |
| `test_reports_exports.py` | PDF (w tym brak pozytywnego wniosku przy wyniku negatywnym), Excel/CSV/JSON/DXF, zgodność rysunku, biblioteka, optymalizacja |
| `test_gui_smoke.py` | GUI offscreen: obliczenia, rysunek, uchwyty, cofanie, warianty, eksporty, zapis, motywy |

## 3. Przypadki kontrolne (wymaganie §14)

| # | Przypadek | Oczekiwany wynik (test) |
|---|---|---|
| 1 | obciążenie pionowe | SPEŁNIONO; T = F_c; H nie dotyczy |
| 2 | pionowe + poziome | T₁ ≥ T₀ + H; wpływ H uwzględniony |
| 3 | bardzo krótki wspornik | MODEL POZA ZAKRESEM (tan θ > 2,5) |
| 4 | duży wysięg | MODEL POZA ZAKRESEM (a_c ≥ z0), wskazana metoda belkowa |
| 5 | krytyczny krzyżulec | element krytyczny = krzyżulec, NIE SPEŁNIONO |
| 6 | krytyczny węzeł | element krytyczny = węzeł A (docisk), NIE SPEŁNIONO |
| 7 | niewystarczające zbrojenie | cięgno NIE SPEŁNIONO |
| 8 | niedostateczne zakotwienie | cięgno OK, zakotwienie NIE SPEŁNIONO |
| 9 | błędna geometria | OBLICZENIA ZABLOKOWANE z komunikatem |
| 10 | niestateczny model STM | stateczność NIE SPEŁNIONO, wynik zablokowany |
| 11 | granica zakresu (tan θ = 1,000) | SPEŁNIONO przy η = 1,000; poniżej — poza zakresem |
| 12 | niewykonalny układ prętów | rozstaw NIE SPEŁNIONO; auto-dobór blokuje z przyczyną |

## 4. Status modułów

| Moduł | Status | Podstawa |
|---|---|---|
| stm_solver | zweryfikowany | rozwiązania analityczne, residua, rząd, metoda sztywności |
| stm_generator | zweryfikowany | porównanie zamknięte/macierzowe w każdym obliczeniu, wzór J.5 |
| material_engine | zweryfikowany | tabl. 3.1 vs wzory |
| load_engine | zweryfikowany | testy kombinacji i ochrony przed podwójnym γ |
| visualization_engine | zweryfikowany | automatyczna kontrola zgodności rysunku z modelem |
| strut_checks, node_checks, tie_checks | częściowo zweryfikowany | obliczenia ręczne; **brak porównania z opublikowanym przykładem obliczeniowym** |
| anchorage_engine | częściowo zweryfikowany | wzory sprawdzone ręcznie; interpretacja długości dostępnej (J.3(4)) do oceny projektanta |
| reinforcement_design | częściowo zweryfikowany | długości w zestawieniu stali orientacyjne |
| design_optimizer, report_engine | częściowo zweryfikowany | testy funkcjonalne |
| sls_crack_check | nieweryfikowany | uproszczenie bez korekt (7.6N)/(7.7N) |
| precast_bearing | nieweryfikowany | wartości tabl. 10.2 i f_Rd do potwierdzenia — sprawdzenie nieaktywne bez potwierdzenia |

## 5. Elementy wymagające potwierdzenia przez projektanta

1. Wartości NDP względem obowiązującego PN-EN 1992-1-1/NA (w szczególności γ_c = 1,4, ν', k₁–k₃, parametry
   zał. J i jego status w Polsce) — przełącznik „Potwierdzam zgodność NDP”.
2. Wartości tablicowe §10.9.5 (tabl. 10.2, f_Rd) — potwierdzenie indywidualne w tabeli parametrów.
3. Przedłużenie ≥ 5φ za odgięciem (rys. 8.1) — oznaczone „do potwierdzenia z treścią rysunku”.
4. Porównanie z niezależnym, opublikowanym przykładem obliczeniowym krótkiego wspornika (np. z literatury
   krajowej) — **nie zostało wykonane**; zalecane przed użyciem produkcyjnym. Testy oparte są na niezależnych
   obliczeniach ręcznych zapisanych w kodzie testów.

## 6. Znane ograniczenia (wyświetlane także w programie i raporcie)

* brak sprawdzenia słupa i jego strefy węzłowej (reakcje modelu są raportowane jako „wymaga osobnej weryfikacji”);
* brak sprawdzenia płyty stalowej, łożysk, spoin, zakotwień mechanicznych (wg ETA);
* skręcanie od e_y — tylko redukcja szerokości efektywnej, skręcanie do osobnej weryfikacji;
* SGU — uproszczona kontrola rys, brak ugięć;
* węzły trójosiowe (k₄) nie są stosowane automatycznie;
* wsporniki długie (a_c ≥ z0) — poza zakresem;
* tłumaczenie angielskie obejmuje interfejs; raport i komunikaty silnika są w języku polskim.
