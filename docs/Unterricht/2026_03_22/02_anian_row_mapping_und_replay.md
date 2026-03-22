# An Anian – Warum das neue Row-Mapping und der Replay-Ansatz die saubere Lösung sind

## Was konkret verbessert wurde

### 1. Explizite Mapping-Dataclass

Statt einer schwer lesbaren Tupelliste gibt es jetzt eine eigene Struktur:

```python
@dataclass(slots=True, frozen=True)
class RowDisplayMapping:
    row_order: list[int]
    cli_to_state: dict[int, int]
    state_to_cli: dict[int, int]
```

Das ist deutlich sprechender. Man erkennt sofort, welche Information gespeichert wird und wofür sie gedacht ist.

## 2. Beide Richtungen sind sauber vorhanden

Die Abbildung funktioniert jetzt in beide Richtungen:

- `to_state_index(cli_row)`
- `to_cli_row(state_row_index)`

Das ist wichtig, weil die CLI mit sichtbaren Reihennummern arbeitet, die Engine aber mit internen Indizes.

## 3. Die Anzeige bleibt benutzerfreundlich

Für die Benutzer bleibt die Darstellung angenehm:

- Reihe 1
- Reihe 2
- Reihe 3
- Reihe 4

Die Reihen können also weiterhin sinnvoll sortiert angezeigt werden, ohne dass der interne Zustand verbogen wird.

## 4. `GameState` bleibt unangetastet

Genau das ist architektonisch sauber:

- View-Logik darf anzeigen
- Engine-Logik darf verändern
- aber View-Logik soll nicht in `state.rows` hineinschreiben

## 5. Der Fehler mit falschen Reihennummern wird korrekt gelöst

Der wichtige Punkt ist nicht nur das Mapping, sondern **wann** das Mapping verwendet wird.

Bei der Rundenauflösung kann sich die Reihenfolge während der einzelnen Schritte verändern. Deshalb reicht es nicht, erst ganz am Ende auf den Endzustand zu schauen.

## Warum der Replay-Schritt nötig ist

Das ist der entscheidende fachliche Punkt.

Wenn man nach `resolve_round(...)` einfach schreibt:

```python
cli_row = mapping.to_cli_row(result.row_index)
```

bekommt man nur die Reihennummer im **Endzustand**.

Das wäre aber fachlich falsch, wenn die Aktion zu einem früheren Zeitpunkt stattgefunden hat, an dem die sichtbare Reihenfolge noch anders war.

## Die saubere Lösung

Deshalb ist der jetzige Ansatz richtig:

1. Zustand **vor** der Auflösung merken
2. Ergebnisse Schritt für Schritt durchgehen
3. für jeden Einzelschritt das Mapping auf einem passenden Schattenzustand berechnen
4. danach diesen Schattenzustand fortschreiben

Im aktuellen Repo sieht man das an der Kombination aus:

- `format_results_for_cli(...)`
- `shadow_state = deepcopy(before_state)`
- `apply_result_to_shadow_state(...)`

## Warum das besser ist als ein Schnellschuss

Ein Schnellschuss hätte vielleicht den sichtbaren Bug kurzfristig verdeckt, aber nicht das eigentliche fachliche Problem gelöst.

Der Replay-Ansatz ist besser, weil er die Frage korrekt beantwortet:

> Welche CLI-Reihe war **zum Zeitpunkt dieser Aktion** gemeint?

Genau diese Frage muss die Ausgabe beantworten.

## Fazit

Ihre Lösungsidee geht in die richtige Richtung und der jetzige Stand ist eine echte Verbesserung:

- lesbarer
- sauberer getrennt
- fachlich korrekt
- robuster gegen Folgefehler

Der wichtigste Gedanke ist dabei:

> Nicht der Endzustand ist für die Anzeige eines Schritts entscheidend, sondern der Zustand zum Zeitpunkt dieses Schritts.
