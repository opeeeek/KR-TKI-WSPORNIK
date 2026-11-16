# Instrukcja użytkownika — KRÓTKI WSPORNIK ST

## Układ okna

* **Panel lewy — Dane wejściowe**: zakładki *Geometria*, *Materiały*, *Obciążenia*, *Model STM*, *Zbrojenie*,
  *Parametry normowe*. Opis każdego parametru — w podpowiedzi (najechanie kursorem) oraz w *Pomoc → Pomoc —
  parametry*. Pola z przełącznikiem „ręcznie” pozwalają nadpisać wartość wyznaczaną automatycznie (obok widać
  wartość automatyczną).
* **Panel centralny — Rysunek**: widoki *Geometria*, *Model STM*, *Naprężenia / wykorzystanie*, *Zbrojenie*
  (Ctrl+1…4). Kółko myszy — zoom; prawy/środkowy przycisk lub Shift+lewy — przesuwanie; podwójne kliknięcie lub F —
  dopasowanie; kliknięcie elementu — szczegóły i powiązane sprawdzenia; *Widok → Warstwy* — warstwy.
* **Panel prawy — Wyniki**: werdykt, siły wewnętrzne, wymagane/przyjęte zbrojenie, element krytyczny, tabela
  wykorzystania, komunikaty, szczegóły wskazanego elementu.
* **Panel dolny — Szczegółowe obliczenia**: drzewo sprawdzeń z wzorem, symbolami, podstawieniem, E_d, R_d, η,
  statusem i wnioskiem; filtr statusów.

## Typowy przebieg pracy

1. *Plik → Dane projektu* — nazwa, element, projektant.
2. *Geometria* — układ (jedno-/dwustronny), wykonanie, wymiary słupa i wspornika, płyta oporowa.
3. *Materiały* — klasa betonu (parametry wyznaczone automatycznie są widoczne od razu), stal, ekspozycja, klasa
   konstrukcji.
4. *Obciążenia* — oddziaływania (charakterystyczne lub obliczeniowe!), kategorie ψ, ewentualnie kombinacje ręczne.
   Wartości obliczeniowe są stosowane bez współczynników częściowych.
5. *Model STM* — domyślnie model automatyczny J.3 z optymalnym doborem x_c; opcjonalnie wartość użytkownika lub
   model ręczny (przycisk „Kopiuj z modelu automatycznego” tworzy punkt wyjścia).
6. *Zbrojenie* — dobór automatyczny lub ręczny; *Obliczenia → Przenieś dobrane zbrojenie do danych* utrwala dobór.
7. *Parametry normowe* — przegląd NDP ze źródłami; potwierdzenie zgodności z NA (bez potwierdzenia wynik jest
   warunkowy); nadpisanie wartości wymaga uzasadnienia.
8. Obliczenia: automatycznie po każdej zmianie (*Obliczenia → Obliczenia automatyczne*) lub F5. Gdy wyniki są
   nieaktualne, rysunek pokazuje wyłącznie geometrię z danych (bez modelu STM) i baner ostrzegawczy.
9. Raport: *Plik → Eksport → Raport PDF* lub *Podgląd wydruku* (z drukowaniem). Eksporty: Excel, CSV, JSON, DXF.

## Edycja na rysunku

Przy włączonej *Edycji uchwytami* pomarańczowe uchwyty pozwalają przeciągać: położenie obciążenia (a_c), koniec
wspornika (l_c), wysokość na końcu (h_e) i przy licu (h_c). Fioletowy uchwyt węzła B zmienia x_c (program przełącza
się na tryb „wartość użytkownika”). W modelu ręcznym przeciąga się węzły kratownicy. Każda zmiana aktualizuje dane,
historię cofania i — w trybie automatycznym — wyniki.

## Warianty, historia, pliki

* Warianty: lista na pasku narzędzi; *Edycja → Kopiuj wariant* (Ctrl+D), zmiana nazwy, usuwanie.
* Cofnij/Ponów: Ctrl+Z / Ctrl+Y (do 300 kroków).
* Projekt `.kwst` (JSON), autozapis co N minut (*Edycja → Ustawienia*), *Plik → Odzyskaj autozapis*.
* *Plik → Biblioteka typowych wsporników* — gotowe przykłady jako nowe warianty.
* *Plik → Import obciążeń* — CSV (`;` lub `,`) lub Excel z kolumnami:
  `name, side, category, nature, source, V_kN, H_kN, M_kNm, e_x_mm, e_y_mm, note`.

## Optymalizacja

*Obliczenia → Optymalizacja*: wybór celu (stal, beton, wysokość, wysięg, koszt, η_max), zakresów h_c, l_c, b, klas
betonu i średnic. Każdy wariant przechodzi pełną analizę; niedopuszczalne są oznaczone z przyczyną. „Zastosuj
wybrany wariant” dodaje go jako nowy wariant projektu.

## Interpretacja wyników

| Status | Znaczenie |
|---|---|
| SPEŁNIONO | warunek spełniony (η ≤ 1) |
| NIE SPEŁNIONO | warunek normowy niespełniony |
| WYMAGA OSOBNEJ WERYFIKACJI | poza zakresem programu, niespełnione zalecenie inżynierskie, parametr niepotwierdzony lub model poza zakresem |
| NIE DOTYCZY | warunek nie ma zastosowania |

Werdykt pozytywny („SPEŁNIONO W ZAKRESIE PROGRAMU”) jest możliwy wyłącznie przy braku błędów i niespełnionych
sprawdzeń, w zakresie modelu i przy potwierdzonych NDP — zawsze z listą pozycji do osobnej weryfikacji.

## Ustawienia

*Edycja → Ustawienia*: jednostki siły (kN/N/MN), długości (mm/cm/m), naprężeń, momentów; autozapis; skala
interfejsu; język (polski/angielski — po ponownym uruchomieniu). *Widok → Motyw ciemny*.

## Autotest

`KrotkiWspornikST.exe --selftest` (lub `python -m kwst --selftest`) wykonuje obliczenia kontrolne, raport i eksporty;
wynik zapisywany jest do `%APPDATA%\KrotkiWspornikST\selftest.log` (wersja okienkowa) lub na konsolę.
