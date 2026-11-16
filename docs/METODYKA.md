# Metodyka obliczeń — KRÓTKI WSPORNIK ST

Dokument opisuje jawnie wszystkie algorytmy i wzory. Oznaczenia podstaw: **[N]** — wymaganie normatywne
EN 1992-1-1, **[I]** — załącznik informacyjny (zał. J), **[Z]** — zalecenie inżynierskie (nie wymóg EC2),
**[M]** — kontrola modelu / numeryczna.

Jednostki wewnętrzne: N, mm, MPa, N·mm. Konwersje wyłącznie na wejściu/wyjściu (`kwst/core/units.py`); kluczowe
wzory sprawdzeń liczone są z analizą wymiarową (klasa `Q`), która zgłasza błąd przy niezgodnym wymiarze.

## 1. Edycje normy i parametry

* Edycja aktywna: **PN-EN 1992-1-1:2008 + AC:2010 + NA:2010** (EN 1992-1-1:2004).
* Edycja **EN 1992-1-1:2023** jest zarejestrowana jako niezaimplementowana — jej wybór blokuje obliczenia
  (brak przenikania wymagań między edycjami; każdy moduł sprawdza zgodność edycji).
* Każdy parametr (`kwst/normative_parameters.py`) ma: wartość, źródło (punkt/wzór/tablica), kategorię
  (EN / NDP / INF / ENG), wartość zalecaną EN, status. Wartości NDP wymagają potwierdzenia przez projektanta —
  bez potwierdzenia werdykt jest warunkowy. Parametry o niepewnej wartości tablicowej (tabl. 10.2, f_Rd wg 10.9.5.2)
  są oznaczone jako blokujące: sprawdzenie daje status „wymaga osobnej weryfikacji” do czasu indywidualnego
  potwierdzenia.

Najważniejsze wartości: γ_c = 1,4 (NA PL; zalecane EN 1,5), γ_s = 1,15, α_cc = α_ct = 1,0, ν' = 1 − f_ck/250 (6.57N),
k₁ = 1,0, k₂ = 0,85, k₃ = 0,75 (6.60–6.62), k₁(J.3) = 0,25, k₂(J.3) = 0,5, 1,0 ≤ tan θ ≤ 2,5 (J.3(1)),
C_Rd,c = 0,18/γ_c, k₁ = 0,15, v_min = 0,035·k^1,5·f_ck^0,5, ν = 0,6(1 − f_ck/250) (6.6N), Δc_dev = 10 mm,
φ_m,min = 4φ / 7φ (tabl. 8.1N), F_wd = 0,5·A_s·f_yd (8.6(2)).

## 2. Materiały

* Beton: wartości z tabl. 3.1 (f_ck, f_cm, f_ctm, f_ctk,0,05, E_cm), kontrolowane wzorami tabl. 3.1 [M].
* f_cd = α_cc·f_ck/γ_c (3.15); f_ctd = α_ct·f_ctk,0,05/γ_c (3.16); do przyczepności f_ctk,0,05 ≤ wartość dla C60/75
  (8.4.2(2)).
* Stal: f_yk 400–600 MPa, klasy A/B/C (zał. C), f_yd = f_yk/γ_s, E_s = 200 GPa.

## 3. Obciążenia i kombinacje

* Oddziaływania charakterystyczne → kombinacje EN 1990: (6.10) lub (6.10a)/(6.10b) z ψ wg tabl. A1.1; SGU
  quasi-stała (6.16b) i charakterystyczna (6.14b); wyjątkowa (6.11b).
* Oddziaływania obliczeniowe → wyłącznie kombinacja `ULS_DIRECT` z mnożnikiem 1,0. Każda inna konfiguracja jest
  błędem krytycznym (ochrona przed podwójnym stosowaniem γ).
* Wypadkowa na stronie wspornika: V = Σf·V_i, H = Σf·H_i, M = Σf·(M_i + V_i·e_x,i), e_y = Σf·V_i·e_y,i / V.
* H_Ed ≥ k·V_Ed — tylko jako świadome założenie użytkownika ze źródłem (brak źródła = błąd).

## 4. Model STM wspornika (zał. J.3, rys. J.5)

Układ lokalny: ξ — odległość od lica słupa (w kierunku wysięgu), y — w górę od górnej powierzchni.

**Węzeł A (CCT)** na osi cięgna (y_A = −c_t), w przecięciu z linią działania wypadkowej (V, H, M):

    ξ_A = a_c + M/V + H·a_H/V,     a_H = c_t + t_p   (H na górnej powierzchni płyty)

**Węzeł B (CCC)** — hydrostatyczna strefa ściskana o wysokości x_c przy licu: y_B = −(h_c − x_c/2), z0 = d − x_c/2.

* tryb `face` (rys. J.5): ξ_B = 0, F_c = V·ξ_A/z0;
* tryb `in_column` (domyślny, konserwatywny [Z]): pozioma ścianka węzła (przekazująca V) w obrysie słupa,
  a_B = x_c·V/F_c, ξ_B = −a_B/2, co daje rozwiązanie zamknięte

      F_c = V/(2·z0) · [ξ_A + √(ξ_A² + 2·x_c·z0)]

Siły: T = F_c + H (H > 0 od słupa; H < 0 pomijana jako korzystna, jeżeli tak ustawiono), C = √(F_c² + V²),
tan θ = V/F_c = z0/(ξ_A − ξ_B). Dla trybu `face` jest to dokładnie F_td = F_Ed·a_c/z0 + H_Ed·(a_H + z0)/z0.

**Węzeł C** — zakotwienie cięgna w słupie (podpora modelu lokalnego). Wsporniki dwustronne: cięgno ciągłe A_L–C–A_R,
C w osi słupa.

**Rozwiązanie macierzowe [M]**: model (węzły, pręty, podpory, obciążenia) jest zawsze rozwiązywany niezależnie
ogólnym solverem (`stm_solver`): macierz równowagi A·f = −P, rząd z SVD, klasyfikacja: wyznaczalny / niewyznaczalny
(metoda sztywności, ostrzeżenie) / mechanizm (blokada wyniku). Residua węzłów, ΣF_x, ΣF_y, ΣM; porównanie z
rozwiązaniem zamkniętym (różnica > 1e−6 → błąd krytyczny).

### 4.1 Dobór wysokości strefy ściskanej x_c

x_c jest parametrem swobodnym dopuszczalnego pola naprężeń (twierdzenie o dolnej ocenie nośności). Przedział
dopuszczalny: 0 < x_c ≤ d − c_t (węzeł B nie zachodzi na strefę cięgna u = 2c_t) oraz 1,0 ≤ tan θ ≤ 2,5 [I].

* `optimal` — sprawdzenie: minimalizacja max η po {krzyżulec A, krzyżulec B, węzeł A (docisk, ścianka krzyżulca),
  węzeł B, cięgno, zakotwienia, gięcie (8.1)}; wymiarowanie: najmniejsze x_c (minimalne T) przy η_betonu ≤ 1.
  Przeszukiwanie: siatka 64 punktów + złoty podział / bisekcja (deterministyczne).
* `node_limit` — najmniejsze x_c spełniające σ_B ≤ min(σ_Rd,max CCC; σ_Rd,max krzyżulca).
* `user` — x_c lub z0 podane przez użytkownika (kontrola przedziału).

Brak przedziału dopuszczalnego → **model poza zakresem** (bardzo krótki wspornik: tan θ > 2,5; długi: tan θ < 1,
a_c ≥ z0). Program informuje o metodzie alternatywnej (belka 6.1/6.2, MES) — nie wykonuje jej, a werdykt nie może być
pozytywny.

### 4.2 Geometria stref

* Efektywna płyta: a_ef = a_p − 2|e| (e — mimośród wypadkowej względem środka płyty, łącznie z H·t_p/V),
  t_A = min(b_p, b) − 2|e_y|, t_B = b − 2|e_y| [Z].
* Szerokość krzyżulca przy A (rys. 6.27): w_A = a_ef·sin θ + u·cos θ, u = 2c_t.
* Przy B (węzeł hydrostatyczny): w_B = √(x_c² + a_B²).
* Kontrola, czy krawędzie krzyżulca i strefy węzłowe leżą w obrysie betonu (istotne dla skosu dolnej krawędzi) [M].
* Krzyżulec butelkowy, gdy dostępna szerokość w połowie długości b > 1,2·max(w_A, w_B); w przeciwnym razie
  pryzmatyczny. Model wachlarzowy nie dotyczy (obciążenie skupione).

## 5. Sprawdzenia

| Sprawdzenie | Wzór | Źródło |
|---|---|---|
| Krzyżulec przy A / B | σ = C/(w·t) ≤ 0,6·ν'·f_cd (lub f_cd) | 6.5.2, (6.55)/(6.56) [N] |
| Węzeł A — docisk | V/(a_ef·t_A) ≤ k₂·ν'·f_cd | 6.5.4(4)b, (6.61), rys. 6.27 [N] |
| Węzeł A — ścianka krzyżulca | C/(w_A·t_A) ≤ k₂·ν'·f_cd | (6.61) [N] |
| Węzeł B | F_c/(x_c·t_B) ≤ k₁·ν'·f_cd | 6.5.4(4)a, (6.60) [N] |
| Zwiększenie 10% | ×1,10 tylko z opisanym uzasadnieniem | 6.5.4(5) [N] |
| Cięgno | T ≤ A_s·f_yd | 6.5.3 [N] |
| Oś cięgna | \|c_t,model − c_t,zbr\| ≤ 0,05·d | [M] |
| Docisk lokalny | F_Rdu = A_c0·f_cd·√(A_c1/A_c0) ≤ 3·f_cd·A_c0 | 6.7, (6.63) [N] |
| Rozłupywanie | T = ¼(b−a)/b·F lub ¼(1−0,7a/h)·F, h = H/2; T ≤ ΣA_sw·f_ywd·sin γ | 6.5.3(3), (6.58)/(6.59) [N] |
| Nachylenie | 1,0 ≤ tan θ ≤ 2,5; a_c < z0 | J.3(1) [I] |
| Strzemiona poziome | A_s,lnk ≥ k₁·A_s,main gdy a_c < 0,5h_c | J.3(2) [I] |
| Strzemiona pionowe | A_s,lnk ≥ k₂·F_Ed/f_yd gdy a_c > 0,5h_c i F_Ed > V_Rd,c | J.3(3), 6.2.2 [I] |
| V_Rd,c | (6.2.a/b), (6.3N), σ_cp = −H/(b·h_c) | 6.2.2(1) [N] |
| Graniczna V | V_Ed ≤ 0,5·b·d·ν·f_cd | 6.2.2(6), (6.5) [N] |
| Zakotwienie | l_bd = α₁…α₅·(φ/4)(σ_sd/f_bd) ≥ l_b,min ≤ l_dost | 8.4.2–8.4.4, (8.2)–(8.6) [N] |
| Pręt przyspawany | F_btd = l_td·φ_t·σ_td ≤ F_wd; σ_sd − F_btd/A_s | 8.6(2), (8.8N) [N] |
| Gięcie | φ_m ≥ 4φ / 7φ; φ_m ≥ F_bt(1/a_b + 1/(2φ))/f_cd | 8.3, tabl. 8.1N, (8.1) [N] |
| Otulina | c_nom = max{c_min,b; c_min,dur; 10} + Δc_dev | 4.4.1, tabl. 4.2, 4.4N [N] |
| Rozstaw | a ≥ max{φ; d_g + 5; 20} | 8.2(2) [N] |
| A_s,min / A_s,max | 0,26·f_ctm/f_yk·b·d ≥ 0,0013·b·d; 0,04·A_c | 9.2.1.1 — analogia [Z] |
| Wysokość pod zewn. krawędzią płyty | h ≥ 0,5·h_c | [Z] (por. ACI 318 rozdz. 16.5) |
| Oparcie prefabrykatu | a₁ = F/(b₁·f_Rd) ≥ a₁,min (tabl. 10.2) ≤ a_p | 10.9.5.2 [N], wartości do potwierdzenia |
| Rysy (uproszczone) | σ_s,qp = T_qp/A_s → tabl. 7.2N lub 7.3N | 7.3.3(2) [N], bez korekt (7.6N)/(7.7N) |

Długości dostępne zakotwień (J.3(4), 6.5.4(7)): od wewnętrznej krawędzi płyty oporowej (strona obciążenia) i od
prętów pionowych przy bliższej krawędzi słupa (strona słupa); dla prętów odgiętych — wzdłuż osi pręta (prosta + łuk +
ramię pionowe, rys. 8.1a); dla pętli, haków i prętów prostych — do zewnętrznej krawędzi pręta. Siła w zakotwieniu =
siła w cięgnie (σ_sd = T/A_s,prov ≤ f_yd).

Przy pręcie przyspawanym przyjmowana jest korzystniejsza z dwóch ścieżek normowych: α₄ = 0,7 (tabl. 8.2) albo
redukcja σ_sd o F_btd/A_s (8.6(2)) z α₄ = 1,0 (bez podwójnego liczenia).

## 6. Dobór zbrojenia

1. Dla każdej dozwolonej średnicy i 1–2 warstw: c_t z układu → A_s,req z modelu STM (tryb wymiarowania, wszystkie
   kombinacje SGN).
2. Liczba prętów n ≥ ⌈A_s,req/A_φ⌉, zwiększana, dopóki układ się mieści (rozstaw 8.2) i zakotwienia/gięcie są
   wykonalne (zwiększenie A_s obniża σ_sd i l_bd); typy zakotwienia: wybrany przez użytkownika, potem pętla, pręt
   przyspawany, odgięcie.
3. Wybór: minimalne A_s (dalej mniej warstw / prętów). Nie są proponowane układy kolidujące lub niemieszczące się.
4. Strzemiona: minimalne pole spełniające J.3(2)/(3), rozłupywanie (6.5.3(3)) i minimum konstrukcyjne [Z];
   korekta iteracyjna po pełnym sprawdzeniu.

## 7. Werdykt

* **OBLICZENIA ZABLOKOWANE** — błędy krytyczne danych/modelu (np. mechanizm, niezgodność rozwiązań, edycja
  niezaimplementowana).
* **MODEL POZA ZAKRESEM STOSOWANIA** — kontrole zakresu modelu (J.3(1), a_c < z0, oś cięgna) wymagają osobnej
  weryfikacji.
* **NIE SPEŁNIONO** — co najmniej jedno sprawdzenie niespełnione.
* **SPEŁNIONO WARUNKOWO** — wszystkie sprawdzenia spełnione, NDP niepotwierdzone.
* **SPEŁNIONO W ZAKRESIE PROGRAMU** — wszystko spełnione, NDP potwierdzone; zawsze z listą pozycji wymagających
  osobnej weryfikacji (słup, płyta stalowa, …).

Raport PDF nie zawiera pozytywnego wniosku ogólnego, jeżeli werdykt nie jest pozytywny.
