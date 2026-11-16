# Instrukcja użytkownika — Krótki wspornik ST

## Układ okna

Pasek górny: nazwa projektu, plik, **Nowy / Otwórz / Zapisz / Zapisz jako…**, **Drukuj / PDF**, **Raport HTML**,
**?** (o programie) i pole stanu (zielone – spełniono, pomarańczowe – warunkowo, czerwone – niespełnione / błąd).

Zakładki:

| Zakładka | Zawartość |
|---|---|
| **Dane** | grupy pól (geometria, płyta oporowa, słup, materiały i otulina, obciążenia i kombinacje, zbrojenie główne, strzemiona, model STM, parametry normowe, dane projektu); obok – schemat wspornika, model J.3 kombinacji decydującej i tabela kombinacji. Nad polami – podgląd wyników (chipy) i pasek doboru. Podział dane / schemat można przeciągać. |
| **Model STM** | rysunek modelu wybranej kombinacji (pola naprężeń w kolorach η, siły, szerokości stref, reakcje), parametry modelu J.3, siły w prętach, kontrola modelu i walidacja automatyczna, założenia. Klik w węzeł / pręt – okno elementu z jego sprawdzeniami. |
| **Zbrojenie wspornika** | rysunek zbrojenia i przekrój przy licu słupa, zbrojenie główne i strzemiona, zakotwienia (f_bd, σ_sd, l_b,rqd, α₁…α₅, l_bd, l_dost), zestawienie stali, przebieg doboru; eksport DXF. |
| **Podsumowanie** | wynik, element krytyczny, karty wyników, komunikaty, lista niespełnionych warunków i tabela wszystkich sprawdzeń. |
| **Optymalizacja** | siatka wymiarów, klasy betonu i średnice; wyniki z możliwością dodania najlepszego wariantu do projektu. |
| **Raport obliczeń** | raport pełny lub skrócony; zapis HTML, .odt, DXF, JSON, CSV; druk / PDF. |

## Typowy przebieg pracy

1. **Dane → Geometria / Płyta / Słup** – wymiary w mm. Wymiary wspornika można też zmieniać przeciągając niebieskie
   uchwyty na schemacie (krok 5 mm).
2. **Materiały i otulina** – klasa betonu, stal (lista ustawia f_yk i klasę ciągliwości), ekspozycja, klasa
   konstrukcji, Δc_dev; otulina c_nom liczona automatycznie (pole ręczne – opcjonalnie).
3. **Obciążenia** – oddziaływania V, H [kN], M [kNm], e_y [mm]; rodzaj *charakterystyczne* (kombinowane wg PN-EN 1990)
   albo *obliczeniowe* (bez ponownego mnożenia przez γ). Kombinacje automatyczne lub ręczne.
4. **Zbrojenie** – dobór automatyczny (domyślnie) albo ręczny; przycisk **⇩ Przyjmij dobrane jako ręczne** przepisuje
   wynik doboru do pól, aby go dalej edytować.
5. **Parametry normowe** – **Parametry NDP…**: wartości, źródła i statusy; potwierdzenie NDP oraz parametrów
   „do potwierdzenia z treścią normy” (bez potwierdzenia nie są stosowane, a wynik jest warunkowy).
6. **Podsumowanie** – kliknij warunek („Jak obliczono”: wzór, oznaczenia, podstawienie, uwagi), podstawę normową
   (objaśnienie punktu) albo **pokaż →** (przejście do danych, od których zależy warunek – podświetlone).
7. **Raport obliczeń** – zapis / druk.

## Warianty i pliki

Warianty – zakładki nad schematem (**+** kopiuje bieżący, dwuklik zmienia nazwę, **×** usuwa); **Porównaj warianty**
w pasku doboru. Projekt (wszystkie warianty) zapisywany jest w pliku `.kwst` (JSON); ostatni stan jest zapamiętywany
automatycznie (program .exe: `%LOCALAPPDATA%\KrotkiWspornikST\autosave.json`, przeglądarka: pamięć strony).
W wersji artefaktu dostępne są **Moje projekty** (zapis na koncie) i pobieranie plików.

## Interpretacja wyników

| Status | Znaczenie |
|---|---|
| SPEŁNIONO | E_d ≤ R_d (η ≤ 1) |
| NIE SPEŁNIONO | warunek normowy niespełniony |
| WYMAGA OSOBNEJ WERYFIKACJI | poza zakresem programu albo zalecenie inżynierskie niespełnione |
| NIE DOTYCZY | warunek nie ma zastosowania |

Wynik ogólny: **SPEŁNIONO W ZAKRESIE PROGRAMU** (NDP potwierdzone), **SPEŁNIONO WARUNKOWO** (NDP niepotwierdzone),
**NIE SPEŁNIONO**, **MODEL POZA ZAKRESEM STOSOWANIA** (np. tan θ < 1 – element nie jest krótkim wspornikiem),
**OBLICZENIA ZABLOKOWANE** (błędy danych lub modelu). Lokalny model wspornika nie sprawdza słupa, łożyska, spoin
ani skręcania – te pozycje są wymienione jako wymagające osobnej weryfikacji.

## Skróty

F2 – raport, Ctrl+S – zapisz, Ctrl+Shift+S – zapisz jako, Ctrl+O – otwórz, Ctrl+N – nowy, Ctrl+P – drukuj raport,
Esc – zamknij okno.

## Silnik referencyjny

`python -m kwst projekt.kwst` – analiza projektu silnikiem Python (wzorzec testów krzyżowych);
`python -m kwst --selftest` – autotest silnika.
