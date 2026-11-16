## Krótki wspornik ST — program dla Windows (64-bit)

Projektowanie i sprawdzanie krótkich wsporników żelbetowych metodą Strut-and-Tie wg PN-EN 1992-1-1 (6.5, zał. J.3,
rozdz. 8, 9, 10.9.5). Interfejs i obsługa jak w programie BelkaŻB.

### Pliki

* **`KrotkiWspornikST.exe`** — program (jeden plik, bez instalacji). Pobierz i uruchom dwuklikiem.
  Wymaga składnika Microsoft Edge WebView2 Runtime (standardowo obecny w Windows 10 i 11); gdy go brak, program
  otworzy się w domyślnej przeglądarce.
* **`KrotkiWspornikST.html`** — ten sam program w przeglądarce (dowolny system): otwórz plik w Chrome/Edge/Firefox.

Projekty zapisywane są w plikach `.kwst` (JSON) — ten sam plik otwiera program .exe, wersja przeglądarkowa
i silnik referencyjny Python (`python -m kwst projekt.kwst`). Ostatni stan pracy jest zapamiętywany automatycznie
(`%LOCALAPPDATA%\KrotkiWspornikST`).

### Ostrzeżenie Windows SmartScreen

Program nie ma płatnego podpisu cyfrowego, więc przy pierwszym uruchomieniu Windows może pokazać okno
„System Windows ochronił ten komputer”. Kliknij **„Więcej informacji”**, a następnie **„Uruchom mimo to”**.

### Uwaga

Wyniki wymagają weryfikacji przez uprawnionego projektanta. Przed użyciem w dokumentacji potwierdź parametry NDP
(zakładka *Dane* → *Parametry normowe* → *Parametry NDP…*). Szczegóły: `docs/UZYTKOWNIK.md`, `docs/METODYKA.md`,
`docs/WALIDACJA.md`.
