"""Wbudowana pomoc — opis każdego parametru wejściowego (ścieżka w modelu danych → opis)."""

HELP = {
    "geometry.layout": "Układ: wspornik jednostronny albo wsporniki dwustronne (symetryczne lub niesymetryczne) "
                       "z cięgnem ciągłym przez słup.",
    "geometry.construction": "Monolityczny lub prefabrykowany. Dla prefabrykowanego program dodaje wymagania "
                             "oparć wg §10.9.5 i przypomina o siłach od więzów (skurcz, pełzanie, temperatura).",
    "geometry.b": "Szerokość wspornika b (wymiar prostopadły do płaszczyzny modelu). Grubość krzyżulców i węzłów.",
    "geometry.column.h_col": "Wymiar słupa w płaszczyźnie wspornika. Określa długość zakotwienia cięgna w słupie "
                             "(J.3(4)) oraz miejsce na strefę węzłową B.",
    "geometry.column.b_col": "Wymiar słupa prostopadły do płaszczyzny wspornika.",
    "geometry.column.above": "Długość słupa nad wspornikiem — wyłącznie do rysunku.",
    "geometry.column.below": "Długość słupa pod wspornikiem — rysunek oraz maksymalna długość ramienia pionowego "
                             "pręta odgiętego w słupie.",
    "geometry.column.cover": "Otulina nominalna zbrojenia słupa (do strzemion). Wyznacza położenie prętów "
                             "pionowych przy bliższej krawędzi (początek długości zakotwienia wg J.3(4)).",
    "geometry.column.phi_long": "Średnica prętów podłużnych słupa.",
    "geometry.column.phi_link": "Średnica strzemion słupa.",
    "geometry.column.N_Ed": "Siła osiowa w słupie — informacyjnie (słup nie jest sprawdzany).",
    "l_c": "Długość wysięgu wspornika mierzona od lica słupa.",
    "h_c": "Wysokość wspornika przy licu słupa h_c. Wysokość użyteczna d = h_c − c_t.",
    "h_e": "Wysokość wspornika na końcu (zewnętrznej krawędzi). h_e < h_c → wspornik o zmiennej wysokości.",
    "x_slope": "Odległość od lica, od której zaczyna się skos dolnej krawędzi (0 = skos od lica).",
    "a_c": "Wysięg obciążenia a_c: odległość linii działania siły pionowej od lica słupa (J.3, rys. J.5).",
    "plate.kind": "Rodzaj oparcia: płyta stalowa, łożysko elastomerowe lub oparcie bezpośrednie (podać pole docisku).",
    "plate.length": "Wymiar płyty a_p wzdłuż wysięgu — długość ścianki docisku węzła A.",
    "plate.width": "Wymiar płyty b_p w poprzek wspornika — grubość efektywna węzła A i krzyżulca przy A.",
    "plate.thickness": "Grubość płyty t_p — wpływa na ramię siły poziomej a_H = c_t + t_p.",
    "plate.offset": "Przesunięcie środka płyty względem linii a_c (mimośród obciążenia względem płyty).",
    "materials.concrete": "Klasa betonu wg EN 1992-1-1 tabl. 3.1.",
    "materials.steel_name": "Gatunek stali zbrojeniowej (parametry wg deklaracji producenta).",
    "materials.steel_fyk": "Charakterystyczna granica plastyczności f_yk (400–600 MPa, zał. C).",
    "materials.steel_class": "Klasa ciągliwości A/B/C (zał. C, tabl. C.1).",
    "materials.link_fyk": "Granica plastyczności stali strzemion.",
    "materials.d_g": "Maksymalny wymiar kruszywa — odstępy prętów (8.2(2)).",
    "materials.exposure": "Klasa ekspozycji (tabl. 4.1) — c_min,dur wg tabl. 4.4N.",
    "materials.structural_class": "Klasa konstrukcji (zalecana S4 dla 50 lat; modyfikacje wg tabl. 4.3N — decyzja "
                                  "projektanta).",
    "materials.delta_c_dev": "Odchyłka wykonawcza Δc_dev (zalecane 10 mm; redukcja przy systemie jakości).",
    "materials.c_nom_user": "Ręcznie przyjęta otulina nominalna (do strzemion). Puste = wyznaczana automatycznie.",
    "materials.design_situation": "Sytuacja obliczeniowa: trwała/przejściowa lub wyjątkowa (współczynniki γ).",
    "stm.lever_arm": "Dobór wysokości strefy ściskanej x_c węzła B: optymalny (najkorzystniejsze dopuszczalne pole "
                     "naprężeń), z warunku granicznego naprężenia w węźle, lub wartość użytkownika.",
    "stm.node_b_position": "Położenie węzła B: w słupie (pozioma ścianka węzła w obrysie słupa — założenie "
                           "konserwatywne) lub na licu słupa (rys. J.5).",
    "stm.strut_limit": "Nośność krzyżulca: (6.56) dla strefy zarysowanej / z rozciąganiem poprzecznym, (6.55) "
                       "bez rozciągania poprzecznego.",
    "stm.node_10pct": "Zwiększenie σ_Rd,max węzłów o 10% wg 6.5.4(5) — wymaga spełnienia i opisania warunków.",
    "stm.include_aH": "Uwzględnienie ramienia siły poziomej a_H ponad osią cięgna (rys. J.5).",
    "stm.neglect_favourable_H": "Pomijanie korzystnej siły poziomej skierowanej do słupa.",
    "reinforcement.main.auto": "Automatyczny dobór zbrojenia głównego (średnica, liczba prętów, warstwy, kotwienie).",
    "reinforcement.main.anchor_load": "Sposób zakotwienia prętów głównych przy końcu wspornika (J.3(4)).",
    "reinforcement.main.anchor_column": "Sposób zakotwienia prętów głównych w słupie (J.3(4)).",
    "reinforcement.main.bond": "Warunki przyczepności (rys. 8.2). Pręty górne wsporników — zwykle 'słabe'.",
    "reinforcement.links.auto": "Automatyczny dobór strzemion wg J.3(2), J.3(3) i warunku rozłupywania (6.5.3(3)).",
    "normative.ndp_confirmed": "Potwierdzenie przez projektanta, że wartości NDP odpowiadają obowiązującemu "
                               "Załącznikowi Krajowemu. Bez potwierdzenia wynik jest warunkowy.",
}

HELP.update({
    "geometry.left_mirror": "Lewy wspornik jako lustrzane odbicie prawego (geometria). Obciążenia lewej strony "
                            "definiuje się osobno (strona L).",
    "geometry.precast.support_type": "Rodzaj podparcia elementu prefabrykowanego do tabl. 10.2 (minimalne a₁).",
    "geometry.precast.dry_connection": "Oparcie 'na sucho' (f_Rd = 0,4·f_cd) lub z podlewką (f_Rd = f_bed ≤ 0,85·f_cd).",
    "geometry.precast.f_bed": "Wytrzymałość obliczeniowa podlewki/zaprawy oparcia (połączenia nie-suche).",
    "geometry.precast.restraint_considered": "Potwierdzenie, że siły poziome od więzów (skurcz, pełzanie, "
                                             "temperatura) zostały rozważone — przy braku H w połączeniu "
                                             "prefabrykowanym program wymaga osobnej weryfikacji.",
    "loads.combination_mode": "Automatyczne kombinacje wg EN 1990 albo kombinacje zdefiniowane ręcznie.",
    "loads.settings.method": "Wzór kombinacji SGN: (6.10) albo para (6.10a)/(6.10b) — wybór wg Załącznika Krajowego.",
    "loads.settings.gamma_G_sup": "Współczynnik częściowy oddziaływań stałych niekorzystnych (tabl. A1.2(B)).",
    "loads.settings.gamma_Q": "Współczynnik częściowy oddziaływań zmiennych.",
    "loads.settings.xi": "Współczynnik redukcyjny ξ we wzorze (6.10b).",
    "loads.settings.include_sls": "Generowanie kombinacji SGU (quasi-stała, charakterystyczna) — kontrola rys.",
    "loads.settings.H_min_enabled": "Świadome założenie minimalnej siły poziomej H_Ed ≥ k·V_Ed. NIE jest wymaganiem "
                                    "EN 1992-1-1 — wymaga podania źródła.",
    "loads.settings.H_min_ratio": "Współczynnik k w założeniu H_Ed ≥ k·V_Ed.",
    "loads.settings.H_min_source": "Źródło / uzasadnienie przyjętej minimalnej siły poziomej (obowiązkowe).",
    "stm.mode": "Model automatyczny wg J.3 (rys. J.5) albo model ręczny (dowolna kratownica płaska).",
    "stm.node_10pct_justification": "Opis spełnienia warunków 6.5.4(5) uprawniających do zwiększenia σ_Rd,max.",
    "x_c_user": "Wysokość strefy ściskanej węzła B (tryb 'wartość użytkownika'); z0 = d − x_c/2.",
    "z0_user": "Ramię sił wewnętrznych z0 (stosowane, gdy nie podano x_c).",
    "a_H_user": "Odległość linii działania H od osi cięgna (domyślnie c_t + t_p).",
    "d_user": "Ręczna wysokość użyteczna d — dopuszczalna tylko ≤ h_c − c_t (wynikającej z układu prętów).",
    "reinforcement.main.phi": "Średnica prętów zbrojenia głównego (tryb ręczny).",
    "reinforcement.main.n_per_layer": "Liczba prętów w jednej warstwie (pętle wymagają liczby parzystej).",
    "reinforcement.main.layers": "Liczba warstw zbrojenia głównego (1–3).",
    "reinforcement.main.layer_gap": "Odstęp w świetle między warstwami (domyślnie s_min wg 8.2(2)).",
    "reinforcement.main.mandrel_load": "Średnica trzpienia gięcia przy końcu wspornika (domyślnie min. wg tabl. 8.1N); "
                                       "sprawdzana także wg (8.1).",
    "reinforcement.main.mandrel_column": "Średnica trzpienia gięcia w słupie.",
    "reinforcement.main.front_leg": "Długość ramienia pionowego pręta odgiętego na końcu wspornika (domyślnie "
                                    "maksymalna mieszcząca się).",
    "reinforcement.main.column_leg": "Długość ramienia pionowego w słupie (domyślnie wymagana z l_bd, min. 5φ).",
    "reinforcement.main.welded_bar_phi": "Średnica przyspawanego pręta poprzecznego (domyślnie = φ prętów głównych); "
                                         "nośność wg (8.8N) dla φ_t = 14–32 mm.",
    "reinforcement.main.alpha3_mode": "α₃ = 1,0 (konserwatywnie) albo obliczony ze strzemion pionowych wzdłuż l_bd.",
    "reinforcement.main.K_alpha3": "Współczynnik K wg rys. 8.4 (0,1 / 0,05 / 0).",
    "reinforcement.links.h_phi": "Średnica zamkniętych strzemion poziomych.",
    "reinforcement.links.h_count": "Liczba strzemion poziomych (każde dwucięte).",
    "reinforcement.links.h_zone": "Wysokość strefy rozmieszczenia strzemion poziomych poniżej zbrojenia głównego "
                                  "(domyślnie 2/3·d — zalecenie konstrukcyjne).",
    "reinforcement.links.v_phi": "Średnica zamkniętych strzemion pionowych.",
    "reinforcement.links.v_count": "Liczba strzemion pionowych między licem a obciążeniem.",
    "reinforcement.links.i_phi": "Średnica prętów ukośnych przy narożu wklęsłym (ograniczenie rys, J.3(5)).",
    "reinforcement.links.i_count": "Liczba prętów ukośnych (nie są wliczane do nośności na rozłupywanie).",
    "reinforcement.links.min_constructive_h": "Minimalna liczba strzemion poziomych stosowana w doborze "
                                              "automatycznym (zalecenie, nie wymóg EC2).",
    "normative.edition": "Edycja normy. Edycja 2. generacji (EN 1992-1-1:2023) nie jest zaimplementowana — program "
                         "nie miesza wymagań różnych edycji.",
    "normative.apply_engineering_recommendations": "Włącza sprawdzenia pomocnicze oznaczone jako zalecenia "
                                                   "inżynierskie (np. wysokość pod zewnętrzną krawędzią płyty).",
})


def help_for(path: str) -> str:
    if path in HELP:
        return HELP[path]
    tail = path.split(".")
    for k in (".".join(tail[-2:]), tail[-1]):
        if k in HELP:
            return HELP[k]
    return ""
