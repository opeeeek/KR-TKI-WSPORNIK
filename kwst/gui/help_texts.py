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


def help_for(path: str) -> str:
    if path in HELP:
        return HELP[path]
    tail = path.split(".")
    for k in (".".join(tail[-2:]), tail[-1]):
        if k in HELP:
            return HELP[k]
    return ""
