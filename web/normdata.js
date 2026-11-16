/* WYGENEROWANE przez tools/export_normdata.py z kwst/normative_parameters.py — nie edytować ręcznie. */
(function (g) { g.WSN_DATA = {
 "editions": {
  "EC2-2004-PL": {
   "id": "EC2-2004-PL",
   "title": "PN-EN 1992-1-1:2008 + AC:2010 + NA:2010 (EN 1992-1-1:2004, 1. generacja)",
   "implemented": true,
   "description": "Pełna implementacja: 6.5 (STM), zał. J.3, rozdz. 8, wybrane przepisy rozdz. 4, 6.2, 6.7, 7.3, 9.2, 10.9.5.",
   "params": [
    {
     "key": "gamma_c",
     "symbol": "γ_c",
     "value": 1.4,
     "unit": "-",
     "clause": "EN 1992-1-1 §2.4.2.4(1), tabl. 2.1N",
     "category": "NDP",
     "description": "Współczynnik częściowy dla betonu — sytuacje trwałe i przejściowe.",
     "recommended": 1.5,
     "na_note": "PN-EN 1992-1-1:2008/NA:2010: γ_c = 1,4 (wartość krajowa różna od zalecanej 1,5).",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "gamma_s",
     "symbol": "γ_s",
     "value": 1.15,
     "unit": "-",
     "clause": "EN 1992-1-1 §2.4.2.4(1), tabl. 2.1N",
     "category": "NDP",
     "description": "Współczynnik częściowy dla stali zbrojeniowej — sytuacje trwałe i przejściowe.",
     "recommended": 1.15,
     "na_note": "PN-EN 1992-1-1:2008/NA:2010: wartość zalecana.",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "gamma_c_acc",
     "symbol": "γ_c,acc",
     "value": 1.2,
     "unit": "-",
     "clause": "EN 1992-1-1 §2.4.2.4(1), tabl. 2.1N",
     "category": "NDP",
     "description": "Współczynnik częściowy dla betonu — sytuacje wyjątkowe.",
     "recommended": 1.2,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "gamma_s_acc",
     "symbol": "γ_s,acc",
     "value": 1.0,
     "unit": "-",
     "clause": "EN 1992-1-1 §2.4.2.4(1), tabl. 2.1N",
     "category": "NDP",
     "description": "Współczynnik częściowy dla stali — sytuacje wyjątkowe.",
     "recommended": 1.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "alpha_cc",
     "symbol": "α_cc",
     "value": 1.0,
     "unit": "-",
     "clause": "EN 1992-1-1 §3.1.6(1)P",
     "category": "NDP",
     "description": "Współczynnik efektów długotrwałych i niekorzystnego sposobu przyłożenia obciążenia (ściskanie).",
     "recommended": 1.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "alpha_ct",
     "symbol": "α_ct",
     "value": 1.0,
     "unit": "-",
     "clause": "EN 1992-1-1 §3.1.6(2)P",
     "category": "NDP",
     "description": "Współczynnik efektów długotrwałych dla wytrzymałości na rozciąganie.",
     "recommended": 1.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "Es",
     "symbol": "E_s",
     "value": 200000.0,
     "unit": "MPa",
     "clause": "EN 1992-1-1 §3.2.7(4)",
     "category": "EN",
     "description": "Moduł sprężystości stali zbrojeniowej (wartość obliczeniowa).",
     "recommended": null,
     "na_note": "",
     "status": "przyjęta wg treści normy",
     "blocking": false,
     "editable": true
    },
    {
     "key": "nu_prime_div",
     "symbol": "250 w ν' = 1 − f_ck/250",
     "value": 250.0,
     "unit": "MPa",
     "clause": "EN 1992-1-1 §6.5.2(2), wzór (6.57N)",
     "category": "NDP",
     "description": "Mianownik we wzorze na współczynnik redukcyjny ν' (krzyżulce i węzły).",
     "recommended": 250.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "strut_cracked",
     "symbol": "0,6 w (6.56)",
     "value": 0.6,
     "unit": "-",
     "clause": "EN 1992-1-1 §6.5.2(2), wzór (6.56)",
     "category": "EN",
     "description": "Współczynnik nośności krzyżulca w strefie zarysowanej: σ_Rd,max = 0,6·ν'·f_cd.",
     "recommended": null,
     "na_note": "",
     "status": "przyjęta wg treści normy",
     "blocking": false,
     "editable": true
    },
    {
     "key": "k1_node",
     "symbol": "k₁",
     "value": 1.0,
     "unit": "-",
     "clause": "EN 1992-1-1 §6.5.4(4)a), wzór (6.60)",
     "category": "NDP",
     "description": "Węzły ściskane bez zakotwionych cięgien (CCC): σ_Rd,max = k₁·ν'·f_cd.",
     "recommended": 1.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "k2_node",
     "symbol": "k₂",
     "value": 0.85,
     "unit": "-",
     "clause": "EN 1992-1-1 §6.5.4(4)b), wzór (6.61)",
     "category": "NDP",
     "description": "Węzły ściskano-rozciągane z cięgnem zakotwionym w jednym kierunku (CCT).",
     "recommended": 0.85,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "k3_node",
     "symbol": "k₃",
     "value": 0.75,
     "unit": "-",
     "clause": "EN 1992-1-1 §6.5.4(4)c), wzór (6.62)",
     "category": "NDP",
     "description": "Węzły ściskano-rozciągane z cięgnami w więcej niż jednym kierunku (CTT).",
     "recommended": 0.75,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "k4_node",
     "symbol": "k₄",
     "value": 3.0,
     "unit": "-",
     "clause": "EN 1992-1-1 §6.5.4(6)",
     "category": "NDP",
     "description": "Górna granica dla węzłów w trójosiowym ściskaniu — NIE stosowana automatycznie.",
     "recommended": 3.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "node_increase",
     "symbol": "1,10",
     "value": 1.1,
     "unit": "-",
     "clause": "EN 1992-1-1 §6.5.4(5)",
     "category": "EN",
     "description": "Dopuszczalne zwiększenie σ_Rd,max węzła o 10% przy spełnieniu warunków 6.5.4(5).",
     "recommended": null,
     "na_note": "",
     "status": "przyjęta wg treści normy",
     "blocking": false,
     "editable": true
    },
    {
     "key": "J3_k1",
     "symbol": "k₁ (J.3)",
     "value": 0.25,
     "unit": "-",
     "clause": "EN 1992-1-1 zał. J.3(2)",
     "category": "INF",
     "description": "Minimalne strzemiona poziome/ukośne A_s,lnk ≥ k₁·A_s,main gdy a_c < 0,5·h_c.",
     "recommended": 0.25,
     "na_note": "Zał. J jest informacyjny — status w PL wymaga potwierdzenia z NA.",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "J3_k2",
     "symbol": "k₂ (J.3)",
     "value": 0.5,
     "unit": "-",
     "clause": "EN 1992-1-1 zał. J.3(3)",
     "category": "INF",
     "description": "Minimalne strzemiona pionowe A_s,lnk ≥ k₂·F_Ed/f_yd gdy a_c > 0,5·h_c i F_Ed > V_Rd,c.",
     "recommended": 0.5,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "J3_tan_min",
     "symbol": "tan θ_min",
     "value": 1.0,
     "unit": "-",
     "clause": "EN 1992-1-1 zał. J.3(1)",
     "category": "INF",
     "description": "Dolna granica nachylenia krzyżulca we wsporniku: 1,0 ≤ tan θ.",
     "recommended": null,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "J3_tan_max",
     "symbol": "tan θ_max",
     "value": 2.5,
     "unit": "-",
     "clause": "EN 1992-1-1 zał. J.3(1)",
     "category": "INF",
     "description": "Górna granica nachylenia krzyżulca we wsporniku: tan θ ≤ 2,5.",
     "recommended": null,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "CRdc_num",
     "symbol": "0,18 w C_Rd,c = 0,18/γ_c",
     "value": 0.18,
     "unit": "-",
     "clause": "EN 1992-1-1 §6.2.2(1)",
     "category": "NDP",
     "description": "Współczynnik nośności na ścinanie elementów bez zbrojenia poprzecznego.",
     "recommended": 0.18,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "k1_shear",
     "symbol": "k₁ (6.2.2)",
     "value": 0.15,
     "unit": "-",
     "clause": "EN 1992-1-1 §6.2.2(1)",
     "category": "NDP",
     "description": "Współczynnik wpływu naprężeń normalnych σ_cp.",
     "recommended": 0.15,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "vmin_coef",
     "symbol": "0,035 w v_min",
     "value": 0.035,
     "unit": "-",
     "clause": "EN 1992-1-1 §6.2.2(1), wzór (6.3N)",
     "category": "NDP",
     "description": "v_min = 0,035·k^(3/2)·f_ck^(1/2).",
     "recommended": 0.035,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "nu_shear_coef",
     "symbol": "0,6 w ν = 0,6(1 − f_ck/250)",
     "value": 0.6,
     "unit": "-",
     "clause": "EN 1992-1-1 §6.2.2(6), wzór (6.6N)",
     "category": "NDP",
     "description": "Współczynnik redukcyjny wytrzymałości betonu zarysowanego przy ścinaniu.",
     "recommended": 0.6,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "shear_max_factor",
     "symbol": "0,5 w V_Ed ≤ 0,5·b_w·d·ν·f_cd",
     "value": 0.5,
     "unit": "-",
     "clause": "EN 1992-1-1 §6.2.2(6), wzór (6.5)",
     "category": "EN",
     "description": "Graniczna siła poprzeczna przy obciążeniu blisko podpory.",
     "recommended": null,
     "na_note": "",
     "status": "przyjęta wg treści normy",
     "blocking": false,
     "editable": true
    },
    {
     "key": "sigma_cp_max",
     "symbol": "0,2 f_cd",
     "value": 0.2,
     "unit": "-",
     "clause": "EN 1992-1-1 §6.2.2(1)",
     "category": "EN",
     "description": "Ograniczenie σ_cp < 0,2·f_cd.",
     "recommended": null,
     "na_note": "",
     "status": "przyjęta wg treści normy",
     "blocking": false,
     "editable": true
    },
    {
     "key": "bearing_max",
     "symbol": "3,0 w (6.63)",
     "value": 3.0,
     "unit": "-",
     "clause": "EN 1992-1-1 §6.7(2), wzór (6.63)",
     "category": "EN",
     "description": "Górna granica nośności na docisk: F_Rdu ≤ 3,0·f_cd·A_c0.",
     "recommended": null,
     "na_note": "",
     "status": "przyjęta wg treści normy",
     "blocking": false,
     "editable": true
    },
    {
     "key": "bond_coef",
     "symbol": "2,25 w (8.2)",
     "value": 2.25,
     "unit": "-",
     "clause": "EN 1992-1-1 §8.4.2(2), wzór (8.2)",
     "category": "EN",
     "description": "f_bd = 2,25·η₁·η₂·f_ctd.",
     "recommended": null,
     "na_note": "",
     "status": "przyjęta wg treści normy",
     "blocking": false,
     "editable": true
    },
    {
     "key": "eta1_poor",
     "symbol": "η₁ (słabe warunki)",
     "value": 0.7,
     "unit": "-",
     "clause": "EN 1992-1-1 §8.4.2(2)",
     "category": "EN",
     "description": "Współczynnik warunków przyczepności dla 'innych' (słabych) warunków.",
     "recommended": null,
     "na_note": "",
     "status": "przyjęta wg treści normy",
     "blocking": false,
     "editable": true
    },
    {
     "key": "fctk_bond_cap",
     "symbol": "f_ctk,0,05 ≤ C60/75",
     "value": 3.1,
     "unit": "MPa",
     "clause": "EN 1992-1-1 §8.4.2(2)",
     "category": "EN",
     "description": "Ograniczenie f_ctk,0,05 do wartości dla C60/75 przy wyznaczaniu f_bd.",
     "recommended": null,
     "na_note": "",
     "status": "przyjęta wg treści normy",
     "blocking": false,
     "editable": true
    },
    {
     "key": "lbmin_ratio",
     "symbol": "0,3 w l_b,min",
     "value": 0.3,
     "unit": "-",
     "clause": "EN 1992-1-1 §8.4.4(1), wzór (8.6)",
     "category": "EN",
     "description": "l_b,min = max{0,3·l_b,rqd; 10φ; 100 mm} (rozciąganie).",
     "recommended": null,
     "na_note": "",
     "status": "przyjęta wg treści normy",
     "blocking": false,
     "editable": true
    },
    {
     "key": "alpha235_min",
     "symbol": "α₂α₃α₅ ≥ 0,7",
     "value": 0.7,
     "unit": "-",
     "clause": "EN 1992-1-1 §8.4.4(1), wzór (8.5)",
     "category": "EN",
     "description": "Dolne ograniczenie iloczynu α₂·α₃·α₅.",
     "recommended": null,
     "na_note": "",
     "status": "przyjęta wg treści normy",
     "blocking": false,
     "editable": true
    },
    {
     "key": "mandrel_small",
     "symbol": "φ_m,min (φ ≤ 16)",
     "value": 4.0,
     "unit": "φ",
     "clause": "EN 1992-1-1 §8.3(2), tabl. 8.1N",
     "category": "NDP",
     "description": "Minimalna średnica trzpienia dla odgięć, haków i pętli: 4φ dla φ ≤ 16 mm.",
     "recommended": 4.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "mandrel_large",
     "symbol": "φ_m,min (φ > 16)",
     "value": 7.0,
     "unit": "φ",
     "clause": "EN 1992-1-1 §8.3(2), tabl. 8.1N",
     "category": "NDP",
     "description": "Minimalna średnica trzpienia dla odgięć, haków i pętli: 7φ dla φ > 16 mm.",
     "recommended": 7.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "fcd_mandrel_cap",
     "symbol": "f_cd ≤ C55/67",
     "value": 55.0,
     "unit": "MPa",
     "clause": "EN 1992-1-1 §8.3(3)",
     "category": "EN",
     "description": "We wzorze (8.1) nie przyjmuje się f_cd większego niż dla klasy C55/67 (f_ck = 55 MPa).",
     "recommended": null,
     "na_note": "",
     "status": "przyjęta wg treści normy",
     "blocking": false,
     "editable": true
    },
    {
     "key": "hook_extension",
     "symbol": "≥ 5φ",
     "value": 5.0,
     "unit": "φ",
     "clause": "EN 1992-1-1 §8.4.1, rys. 8.1b,c",
     "category": "EN",
     "description": "Minimalne przedłużenie proste za odgięciem / hakiem standardowym (rys. 8.1).",
     "recommended": null,
     "na_note": "",
     "status": "do potwierdzenia z treścią rys. 8.1",
     "blocking": false,
     "editable": true
    },
    {
     "key": "fwd_factor",
     "symbol": "F_wd = k·A_s·f_yd",
     "value": 0.5,
     "unit": "-",
     "clause": "EN 1992-1-1 §8.6(2), wzór (8.8N)",
     "category": "NDP",
     "description": "Nośność spoiny pręta poprzecznego jako ułamek A_s·f_yd pręta kotwionego (wartość przykładowa normy 'np. 0,5') — wymaga potwierdzenia dla stosowanej technologii spawania.",
     "recommended": 0.5,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "spacing_k1",
     "symbol": "k₁ (8.2)",
     "value": 1.0,
     "unit": "-",
     "clause": "EN 1992-1-1 §8.2(2)",
     "category": "NDP",
     "description": "Minimalny odstęp w świetle: max{k₁·φ; d_g + k₂; 20 mm}.",
     "recommended": 1.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "spacing_k2",
     "symbol": "k₂ (8.2)",
     "value": 5.0,
     "unit": "mm",
     "clause": "EN 1992-1-1 §8.2(2)",
     "category": "NDP",
     "description": "Minimalny odstęp w świetle: max{k₁·φ; d_g + k₂; 20 mm}.",
     "recommended": 5.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "delta_c_dev",
     "symbol": "Δc_dev",
     "value": 10.0,
     "unit": "mm",
     "clause": "EN 1992-1-1 §4.4.1.3(1)P",
     "category": "NDP",
     "description": "Odchyłka wykonawcza otuliny (wartość zalecana; redukcja możliwa przy kontroli jakości).",
     "recommended": 10.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "delta_c_dur_gamma",
     "symbol": "Δc_dur,γ",
     "value": 0.0,
     "unit": "mm",
     "clause": "EN 1992-1-1 §4.4.1.2(6)",
     "category": "NDP",
     "description": "Dodatkowy element bezpieczeństwa otuliny.",
     "recommended": 0.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "delta_c_dur_st",
     "symbol": "Δc_dur,st",
     "value": 0.0,
     "unit": "mm",
     "clause": "EN 1992-1-1 §4.4.1.2(7)",
     "category": "NDP",
     "description": "Redukcja otuliny przy stali nierdzewnej.",
     "recommended": 0.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "delta_c_dur_add",
     "symbol": "Δc_dur,add",
     "value": 0.0,
     "unit": "mm",
     "clause": "EN 1992-1-1 §4.4.1.2(8)",
     "category": "NDP",
     "description": "Redukcja otuliny przy dodatkowym zabezpieczeniu.",
     "recommended": 0.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "As_min_coef",
     "symbol": "0,26 w A_s,min",
     "value": 0.26,
     "unit": "-",
     "clause": "EN 1992-1-1 §9.2.1.1(1), wzór (9.1N)",
     "category": "ENG",
     "description": "A_s,min = 0,26·f_ctm/f_yk·b_t·d — zastosowanie do wspornika przez analogię do belek (zał. J.3 nie określa minimum zbrojenia głównego).",
     "recommended": 0.26,
     "na_note": "",
     "status": "zalecenie — stosowanie decyzją projektanta",
     "blocking": false,
     "editable": true
    },
    {
     "key": "As_min_abs",
     "symbol": "0,0013 w A_s,min",
     "value": 0.0013,
     "unit": "-",
     "clause": "EN 1992-1-1 §9.2.1.1(1), wzór (9.1N)",
     "category": "ENG",
     "description": "A_s,min ≥ 0,0013·b_t·d — analogia do belek.",
     "recommended": 0.0013,
     "na_note": "",
     "status": "zalecenie — stosowanie decyzją projektanta",
     "blocking": false,
     "editable": true
    },
    {
     "key": "As_max_coef",
     "symbol": "0,04 A_c",
     "value": 0.04,
     "unit": "-",
     "clause": "EN 1992-1-1 §9.2.1.1(3)",
     "category": "ENG",
     "description": "A_s,max = 0,04·A_c — analogia do belek.",
     "recommended": 0.04,
     "na_note": "",
     "status": "zalecenie — stosowanie decyzją projektanta",
     "blocking": false,
     "editable": true
    },
    {
     "key": "fRd_dry",
     "symbol": "f_Rd = 0,4 f_cd",
     "value": 0.4,
     "unit": "-",
     "clause": "EN 1992-1-1 §10.9.5.2(2)",
     "category": "EN",
     "description": "Wytrzymałość obliczeniowa na docisk w oparciach — połączenia 'na sucho'.",
     "recommended": null,
     "na_note": "",
     "status": "do potwierdzenia z treścią normy",
     "blocking": true,
     "editable": true
    },
    {
     "key": "fRd_other",
     "symbol": "f_Rd ≤ 0,85 f_cd",
     "value": 0.85,
     "unit": "-",
     "clause": "EN 1992-1-1 §10.9.5.2(2)",
     "category": "EN",
     "description": "Wytrzymałość obliczeniowa na docisk w oparciach — pozostałe przypadki (f_bed ≤ 0,85 f_cd).",
     "recommended": null,
     "na_note": "",
     "status": "do potwierdzenia z treścią normy",
     "blocking": true,
     "editable": true
    },
    {
     "key": "table_10_2",
     "symbol": "tabl. 10.2",
     "value": 1.0,
     "unit": "-",
     "clause": "EN 1992-1-1 §10.9.5.2, tabl. 10.2",
     "category": "EN",
     "description": "Minimalne długości oparcia netto a₁ — wartości tablicowe wbudowane w program.",
     "recommended": null,
     "na_note": "",
     "status": "do potwierdzenia z treścią normy",
     "blocking": true,
     "editable": false
    },
    {
     "key": "wmax_X0_XC1",
     "symbol": "w_max (X0, XC1)",
     "value": 0.4,
     "unit": "mm",
     "clause": "EN 1992-1-1 §7.3.1(5), tabl. 7.1N",
     "category": "NDP",
     "description": "Graniczna szerokość rys — klasy X0, XC1 (kombinacja quasi-stała).",
     "recommended": 0.4,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "wmax_other",
     "symbol": "w_max (XC2–XS3)",
     "value": 0.3,
     "unit": "mm",
     "clause": "EN 1992-1-1 §7.3.1(5), tabl. 7.1N",
     "category": "NDP",
     "description": "Graniczna szerokość rys — pozostałe klasy ekspozycji.",
     "recommended": 0.3,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "gamma_G_sup",
     "symbol": "γ_G,sup",
     "value": 1.35,
     "unit": "-",
     "clause": "EN 1990 tabl. A1.2(B)",
     "category": "NDP",
     "description": "Współczynnik częściowy oddziaływań stałych niekorzystnych.",
     "recommended": 1.35,
     "na_note": "PN-EN 1990:2004/NA:2010",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "gamma_G_inf",
     "symbol": "γ_G,inf",
     "value": 1.0,
     "unit": "-",
     "clause": "EN 1990 tabl. A1.2(B)",
     "category": "NDP",
     "description": "Współczynnik częściowy oddziaływań stałych korzystnych.",
     "recommended": 1.0,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "gamma_Q",
     "symbol": "γ_Q",
     "value": 1.5,
     "unit": "-",
     "clause": "EN 1990 tabl. A1.2(B)",
     "category": "NDP",
     "description": "Współczynnik częściowy oddziaływań zmiennych.",
     "recommended": 1.5,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "xi",
     "symbol": "ξ",
     "value": 0.85,
     "unit": "-",
     "clause": "EN 1990 tabl. A1.2(B), wzór (6.10b)",
     "category": "NDP",
     "description": "Współczynnik redukcyjny oddziaływań stałych niekorzystnych w (6.10b).",
     "recommended": 0.85,
     "na_note": "",
     "status": "do potwierdzenia z NA",
     "blocking": false,
     "editable": true
    },
    {
     "key": "outer_depth_ratio",
     "symbol": "h(x_zew)/h_c ≥ 0,5",
     "value": 0.5,
     "unit": "-",
     "clause": "Zalecenie konstrukcyjne (por. ACI 318, rozdz. 16.5 — odniesienie porównawcze)",
     "category": "ENG",
     "description": "Wysokość wspornika pod zewnętrzną krawędzią płyty oporowej nie mniejsza niż 0,5·h_c.",
     "recommended": null,
     "na_note": "",
     "status": "zalecenie — stosowanie decyzją projektanta",
     "blocking": false,
     "editable": true
    },
    {
     "key": "h_link_zone",
     "symbol": "strefa strzemion poziomych",
     "value": 0.6666666666666666,
     "unit": "d",
     "clause": "Zalecenie konstrukcyjne (por. rys. J.6a; ACI 318 rozdz. 16.5 — odniesienie porównawcze)",
     "category": "ENG",
     "description": "Strzemiona poziome rozmieszczane w strefie ≈ 2/3·d poniżej zbrojenia głównego.",
     "recommended": null,
     "na_note": "",
     "status": "zalecenie — stosowanie decyzją projektanta",
     "blocking": false,
     "editable": true
    },
    {
     "key": "tie_axis_tol",
     "symbol": "tolerancja osi cięgna",
     "value": 0.05,
     "unit": "d",
     "clause": "Kontrola modelu (6.5.3, 6.5.4(7))",
     "category": "ENG",
     "description": "Dopuszczalna odchyłka osi cięgna w modelu od środka ciężkości zbrojenia.",
     "recommended": null,
     "na_note": "",
     "status": "zalecenie — stosowanie decyzją projektanta",
     "blocking": false,
     "editable": true
    }
   ]
  },
  "EC2-2023": {
   "id": "EC2-2023",
   "title": "EN 1992-1-1:2023 (2. generacja) — NIEZAIMPLEMENTOWANA",
   "implemented": false,
   "description": "Szkielet do przyszłej implementacji. Parametry 2. generacji nie są dostępne; program nie przenosi do niej wymagań 1. generacji.",
   "params": []
  }
 },
 "categoryLabel": {
  "EN": "wartość normatywna (treść normy)",
  "NDP": "parametr krajowy (NDP)",
  "INF": "załącznik informacyjny / NDP",
  "ENG": "zalecenie inżynierskie (nie wymóg EC2)"
 },
 "t31": {
  "C12/15": [
   12,
   15,
   20,
   1.6,
   1.1,
   2.0,
   27
  ],
  "C16/20": [
   16,
   20,
   24,
   1.9,
   1.3,
   2.5,
   29
  ],
  "C20/25": [
   20,
   25,
   28,
   2.2,
   1.5,
   2.9,
   30
  ],
  "C25/30": [
   25,
   30,
   33,
   2.6,
   1.8,
   3.3,
   31
  ],
  "C30/37": [
   30,
   37,
   38,
   2.9,
   2.0,
   3.8,
   33
  ],
  "C35/45": [
   35,
   45,
   43,
   3.2,
   2.2,
   4.2,
   34
  ],
  "C40/50": [
   40,
   50,
   48,
   3.5,
   2.5,
   4.6,
   35
  ],
  "C45/55": [
   45,
   55,
   53,
   3.8,
   2.7,
   4.9,
   36
  ],
  "C50/60": [
   50,
   60,
   58,
   4.1,
   2.9,
   5.3,
   37
  ],
  "C55/67": [
   55,
   67,
   63,
   4.2,
   3.0,
   5.5,
   38
  ],
  "C60/75": [
   60,
   75,
   68,
   4.4,
   3.1,
   5.7,
   39
  ],
  "C70/85": [
   70,
   85,
   78,
   4.6,
   3.2,
   6.0,
   41
  ],
  "C80/95": [
   80,
   95,
   88,
   4.8,
   3.4,
   6.3,
   42
  ],
  "C90/105": [
   90,
   105,
   98,
   5.0,
   3.5,
   6.6,
   44
  ]
 },
 "t44N": {
  "X0": [
   10,
   10,
   10,
   10,
   15,
   20
  ],
  "XC1": [
   10,
   10,
   10,
   15,
   20,
   25
  ],
  "XC2/XC3": [
   10,
   15,
   20,
   25,
   30,
   35
  ],
  "XC4": [
   15,
   20,
   25,
   30,
   35,
   40
  ],
  "XD1/XS1": [
   20,
   25,
   30,
   35,
   40,
   45
  ],
  "XD2/XS2": [
   25,
   30,
   35,
   40,
   45,
   50
  ],
  "XD3/XS3": [
   30,
   35,
   40,
   45,
   50,
   55
  ]
 },
 "expGroup": {
  "X0": "X0",
  "XC1": "XC1",
  "XC2": "XC2/XC3",
  "XC3": "XC2/XC3",
  "XC4": "XC4",
  "XD1": "XD1/XS1",
  "XS1": "XD1/XS1",
  "XD2": "XD2/XS2",
  "XS2": "XD2/XS2",
  "XD3": "XD3/XS3",
  "XS3": "XD3/XS3"
 },
 "structClasses": [
  "S1",
  "S2",
  "S3",
  "S4",
  "S5",
  "S6"
 ],
 "t72N": {
  "160": [
   40,
   32,
   25
  ],
  "200": [
   32,
   25,
   16
  ],
  "240": [
   20,
   16,
   12
  ],
  "280": [
   16,
   12,
   8
  ],
  "320": [
   12,
   10,
   6
  ],
  "360": [
   10,
   8,
   5
  ],
  "400": [
   8,
   6,
   4
  ],
  "450": [
   6,
   5,
   null
  ]
 },
 "t73N": {
  "160": [
   300,
   300,
   200
  ],
  "200": [
   300,
   250,
   150
  ],
  "240": [
   250,
   200,
   100
  ],
  "280": [
   200,
   150,
   50
  ],
  "320": [
   150,
   100,
   null
  ],
  "360": [
   100,
   50,
   null
  ]
 },
 "t102": {
  "line": [
   25,
   30,
   40
  ],
  "ribbed": [
   55,
   70,
   80
  ],
  "concentrated": [
   90,
   110,
   140
  ]
 },
 "psi": {
  "Q_A": [
   "Kat. A — mieszkalne",
   0.7,
   0.5,
   0.3
  ],
  "Q_B": [
   "Kat. B — biurowe",
   0.7,
   0.5,
   0.3
  ],
  "Q_C": [
   "Kat. C — zebrań",
   0.7,
   0.7,
   0.6
  ],
  "Q_D": [
   "Kat. D — handlowe",
   0.7,
   0.7,
   0.6
  ],
  "Q_E": [
   "Kat. E — magazynowe",
   1.0,
   0.9,
   0.8
  ],
  "Q_F": [
   "Kat. F — ruch pojazdów ≤ 30 kN",
   0.7,
   0.7,
   0.6
  ],
  "Q_G": [
   "Kat. G — ruch pojazdów 30–160 kN",
   0.7,
   0.5,
   0.3
  ],
  "Q_H": [
   "Kat. H — dachy",
   0.0,
   0.0,
   0.0
  ],
  "S": [
   "Śnieg (H ≤ 1000 m n.p.m.)",
   0.5,
   0.2,
   0.0
  ],
  "S_H": [
   "Śnieg (H > 1000 m n.p.m.)",
   0.7,
   0.5,
   0.2
  ],
  "W": [
   "Wiatr",
   0.6,
   0.2,
   0.0
  ],
  "T": [
   "Temperatura (nie pożarowa)",
   0.6,
   0.5,
   0.0
  ]
 },
 "steelGrades": {
  "B500SP": [
   500.0,
   "C"
  ],
  "RB500W": [
   500.0,
   "C"
  ],
  "BSt500S": [
   500.0,
   "B"
  ],
  "B500A": [
   500.0,
   "A"
  ],
  "B500B": [
   500.0,
   "B"
  ],
  "B500C": [
   500.0,
   "C"
  ],
  "B450C": [
   450.0,
   "C"
  ],
  "RB400W": [
   400.0,
   "C"
  ],
  "Inna": [
   500.0,
   "B"
  ]
 },
 "ductility": {
  "A": [
   1.05,
   2.5
  ],
  "B": [
   1.08,
   5.0
  ],
  "C": [
   1.15,
   7.5
  ]
 },
 "defaults": {
  "schema_version": 1,
  "variant": {
   "name": "Wariant 1",
   "geometry": {
    "layout": "single",
    "construction": "monolithic",
    "b": 400.0,
    "column": {
     "h_col": 400.0,
     "b_col": 400.0,
     "above": 400.0,
     "below": 700.0,
     "cover": 30.0,
     "phi_long": 20.0,
     "phi_link": 8.0,
     "N_Ed": 0.0
    },
    "right": {
     "side": "R",
     "l_c": 400.0,
     "h_c": 550.0,
     "h_e": 350.0,
     "x_slope": 0.0,
     "a_c": 250.0,
     "plate": {
      "kind": "steel_plate",
      "length": 150.0,
      "width": 300.0,
      "thickness": 20.0,
      "offset": 0.0
     },
     "a_H_user": null,
     "d_user": null,
     "x_c_user": null,
     "z0_user": null
    },
    "left": {
     "side": "L",
     "l_c": 400.0,
     "h_c": 550.0,
     "h_e": 350.0,
     "x_slope": 0.0,
     "a_c": 250.0,
     "plate": {
      "kind": "steel_plate",
      "length": 150.0,
      "width": 300.0,
      "thickness": 20.0,
      "offset": 0.0
     },
     "a_H_user": null,
     "d_user": null,
     "x_c_user": null,
     "z0_user": null
    },
    "left_mirror": true,
    "precast": {
     "support_type": "concentrated",
     "dry_connection": true,
     "f_bed": 0.0,
     "restraint_considered": false
    }
   },
   "materials": {
    "concrete": "C30/37",
    "steel_name": "B500SP",
    "steel_fyk": 500.0,
    "steel_class": "C",
    "link_fyk": 500.0,
    "Es": 200000.0,
    "d_g": 16.0,
    "exposure": "XC1",
    "structural_class": "S4",
    "delta_c_dev": 10.0,
    "c_nom_user": null,
    "design_situation": "persistent"
   },
   "loads": {
    "actions": [
     {
      "name": "G1",
      "side": "R",
      "category": "G",
      "nature": "characteristic",
      "source": "beam_reaction",
      "V": 180000.0,
      "H": 0.0,
      "M": 0.0,
      "e_x": 0.0,
      "e_y": 0.0,
      "note": "Reakcja od ciężaru własnego belki i stropu"
     },
     {
      "name": "Q1",
      "side": "R",
      "category": "Q_B",
      "nature": "characteristic",
      "source": "beam_reaction",
      "V": 120000.0,
      "H": 0.0,
      "M": 0.0,
      "e_x": 0.0,
      "e_y": 0.0,
      "note": "Reakcja od obciążenia użytkowego"
     },
     {
      "name": "H1",
      "side": "R",
      "category": "G",
      "nature": "characteristic",
      "source": "other",
      "V": 0.0,
      "H": 40000.0,
      "M": 0.0,
      "e_x": 0.0,
      "e_y": 0.0,
      "note": "Siła pozioma od ograniczenia odkształceń (skurcz/pełzanie) — wartość charakterystyczna"
     }
    ],
    "combination_mode": "auto",
    "combinations": [],
    "settings": {
     "method": "6.10ab",
     "gamma_G_sup": 1.35,
     "gamma_G_inf": 1.0,
     "gamma_Q": 1.5,
     "xi": 0.85,
     "include_sls": true,
     "H_min_enabled": false,
     "H_min_ratio": 0.2,
     "H_min_source": ""
    }
   },
   "reinforcement": {
    "main": {
     "auto": true,
     "phi": 20.0,
     "n_per_layer": 4,
     "layers": 1,
     "layer_gap": null,
     "anchor_load": "loop",
     "anchor_column": "bend_down",
     "mandrel_load": null,
     "mandrel_column": null,
     "column_leg": null,
     "front_leg": null,
     "welded_bar_phi": null,
     "bond": "poor",
     "alpha3_mode": "conservative",
     "K_alpha3": 0.05
    },
    "links": {
     "auto": true,
     "h_phi": 10.0,
     "h_count": 3,
     "h_zone": null,
     "v_phi": 8.0,
     "v_count": 0,
     "i_phi": 10.0,
     "i_count": 0,
     "min_constructive_h": 2
    },
    "allowed_diameters": [
     12.0,
     14.0,
     16.0,
     20.0,
     25.0,
     28.0,
     32.0
    ]
   },
   "stm": {
    "mode": "auto",
    "lever_arm": "optimal",
    "node_b_position": "in_column",
    "strut_limit": "6.56",
    "node_10pct": false,
    "node_10pct_justification": "",
    "include_aH": true,
    "neglect_favourable_H": true,
    "manual": {
     "nodes": [],
     "members": [],
     "supports": [],
     "loads": []
    }
   },
   "normative": {
    "edition": "EC2-2004-PL",
    "overrides": {},
    "override_notes": {},
    "ndp_confirmed": false,
    "confirmed_params": [],
    "apply_engineering_recommendations": true
   }
  },
  "info": {
   "name": "Nowy projekt",
   "number": "",
   "object": "",
   "element": "Wspornik krótki W-1",
   "designer": "",
   "checker": "",
   "notes": ""
  },
  "action": {
   "name": "G",
   "side": "R",
   "category": "G",
   "nature": "characteristic",
   "source": "beam_reaction",
   "V": 0.0,
   "H": 0.0,
   "M": 0.0,
   "e_x": 0.0,
   "e_y": 0.0,
   "note": ""
  },
  "combination": {
   "name": "KOMB",
   "kind": "ULS",
   "factors": {},
   "note": ""
  },
  "node": {
   "id": "N1",
   "x": 0.0,
   "y": 0.0
  },
  "member": {
   "id": "M1",
   "n1": "N1",
   "n2": "N2",
   "kind": "strut",
   "width": 100.0,
   "thickness": 400.0,
   "As": 0.0
  },
  "support": {
   "node": "N1",
   "ux": true,
   "uy": true,
   "bearing_width": 100.0
  },
  "load": {
   "node": "N1",
   "Fx": 0.0,
   "Fy": 0.0
  }
 }
}; })(typeof window !== 'undefined' ? window : globalThis);
