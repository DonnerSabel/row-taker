from __future__ import annotations

import re
import stat
import textwrap
from pathlib import Path

SCRIPT_CONTENT = textwrap.dedent("""\
#!/usr/bin/env bash
set -eu

# UTF-8 stabil halten
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

EVENT_NAME="${GITHUB_EVENT_NAME:-}"
ACTOR="${GITHUB_ACTOR:-}"
REF_NAME="${GITHUB_REF_NAME:-}"
EVENT_BEFORE="${EVENT_BEFORE:-}"
EVENT_SHA="${EVENT_SHA:-}"
EVENT_PATH="${GITHUB_EVENT_PATH:-}"
INPUT_FROM_SHA="${INPUT_FROM_SHA:-}"
INPUT_TO_SHA="${INPUT_TO_SHA:-}"

printf '👤 Benutzer: %s\n' "$ACTOR"
printf '🔍 Branch: %s\n' "$REF_NAME"
printf '📦 Event: %s\n' "$EVENT_NAME"
printf '\n'

get_changed_from_event_json() {
  if [ -n "$EVENT_PATH" ] && [ -f "$EVENT_PATH" ] && command -v jq >/dev/null 2>&1; then
    jq -r '
      [ .commits[]? | .added[]?, .modified[]?, .removed[]? ]
      | unique
      | .[]
    ' "$EVENT_PATH" 2>/dev/null || true
  fi
}

CHANGED=""

if [ "$EVENT_NAME" = "push" ]; then
  if [ -n "$EVENT_BEFORE" ] && [ "$EVENT_BEFORE" != "0000000000000000000000000000000000000000" ]; then
    echo "ℹ️ Normaler Push-Fall."

    if git cat-file -e "$EVENT_BEFORE^{commit}" 2>/dev/null; then
      echo "ℹ️ Prüfe Diff von $EVENT_BEFORE bis $EVENT_SHA"
      CHANGED="$(git -c core.quotepath=off diff --name-only "$EVENT_BEFORE" "$EVENT_SHA")"
    else
      echo "⚠️ EVENT_BEFORE-Commit $EVENT_BEFORE ist lokal nicht verfügbar."
      echo "ℹ️ Fallback: Dateiliste aus Event-Payload lesen."
      CHANGED="$(get_changed_from_event_json)"
    fi
  else
    echo "ℹ️ Neuer Branch / erster Push erkannt."
    echo "ℹ️ Versuche Dateiliste aus Event-Payload zu lesen."
    CHANGED="$(get_changed_from_event_json)"

    if [ -z "$CHANGED" ]; then
      echo "ℹ️ Event-Payload enthält keine auswertbare Dateiliste."
      echo "ℹ️ Fallback: diff-tree auf EVENT_SHA."
      CHANGED="$(git -c core.quotepath=off diff-tree --root --no-commit-id --name-only -r "$EVENT_SHA" || true)"
    fi
  fi
elif [ "$EVENT_NAME" = "workflow_dispatch" ]; then
  TO="$INPUT_TO_SHA"
  FROM="$INPUT_FROM_SHA"

  if [ -z "$TO" ]; then
    TO="$EVENT_SHA"
  fi
  if [ -z "$FROM" ]; then
    FROM="${TO}^"
  fi

  echo "ℹ️ workflow_dispatch: prüfe Diff von $FROM bis $TO"
  CHANGED="$(git -c core.quotepath=off diff --name-only "$FROM" "$TO")"
else
  echo "❌ Nicht unterstütztes Event: $EVENT_NAME"
  exit 1
fi

echo "📄 Geänderte / hinzugefügte Dateien:"
printf '%s\n' "$CHANGED"
printf '\n'

if [ -z "$CHANGED" ]; then
  if [ "$EVENT_NAME" = "push" ] && [ "$EVENT_BEFORE" = "0000000000000000000000000000000000000000" ]; then
    echo "ℹ️ Keine Dateiliste im Event gefunden. Erlaube diesen Push."
    exit 0
  fi

  echo "❌ Konnte keine geänderten Dateien zuverlässig bestimmen."
  exit 1
fi

if [ "$ACTOR" = "BerndDonner" ] && [ "$REF_NAME" = "master" ]; then
  echo "🧑‍🏫 Lehrer auf master – keine Pfadprüfung erforderlich."
  exit 0
fi

printf '👤 Erwarteter Benutzer-Ordner: %s/\n\n' "$ACTOR"
allowed_prefixes="^(${ACTOR}/|common/|shared/|README\\.md|$)"
printf '🧩 Erlaubte Pfad-Präfixe (Regex): %s\n\n' "$allowed_prefixes"

violations="$(printf '%s\n' "$CHANGED" | grep -Ev "$allowed_prefixes" || true)"

if [ -n "$violations" ]; then
  echo "❌ Commit enthält Dateien außerhalb deines Verzeichnisses!"
  echo "👤 Erlaubt ist nur: ${ACTOR}/ (plus ggf. common/, shared/, README.md)"
  echo "🚫 Nicht erlaubte Dateien:"
  printf '%s\n' "$violations"
  exit 1
fi

echo "✅ Alle Änderungen befinden sich im erlaubten Bereich (${ACTOR}/ oder gemeinsame Bereiche)."
""")


NEW_TEST = textwrap.dedent('''

def test_new_branch_fallback_uses_event_payload_and_blocks_forbidden_path(
    script_path: Path, tmp_path: Path
):
    """
    Regressionstest für den real aufgetretenen Fehlerfall in der Action.

    Der Runner behandelt den Push fälschlich wie einen "neuen Branch / ersten Push"
    (EVENT_BEFORE = 000...).
    Der Commit selbst ändert aber eine verbotene Datei außerhalb des Schülerordners.

    Wichtig:
    - Ohne Auswertung der Event-Payload wäre CHANGED leer und der Push würde
      fälschlich erlaubt.
    - Mit korrektem Fallback auf GITHUB_EVENT_PATH muss der Verstoß erkannt werden.
    """
    repo = tmp_path / "repo"
    init_repo(repo)

    _base = commit_file(repo, "stemmer/a.txt", "1", "allowed base")
    bad_sha = commit_file(
        repo,
        "donner/5_minuten_ei/5_minuten_ei.ino",
        "boom",
        "touch donner",
    )

    event_path = tmp_path / "event_new_branch_with_forbidden_file.json"
    make_event_json(event_path, ["donner/5_minuten_ei/5_minuten_ei.ino"])

    env = {
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_ACTOR": "stemmer",
        "GITHUB_REF_NAME": "stemmer_teil_1",
        "EVENT_BEFORE": "0000000000000000000000000000000000000000",
        "EVENT_SHA": bad_sha,
        "GITHUB_EVENT_PATH": str(event_path),
    }
    res = run([str(script_path)], cwd=repo, env=env, check=False)

    assert res.returncode == 1, res.stdout
    assert "Neuer Branch / erster Push" in res.stdout
    assert "Event-Payload" in res.stdout
    assert "donner/5_minuten_ei/5_minuten_ei.ino" in res.stdout
''')


def replace_allows_new_branch_test(text: str) -> str:
    pattern = re.compile(
        r"def test_allows_new_branch_creation_without_commits\(script_path: Path, tmp_path: Path\):\n(?:    .*\n)+?(?=\ndef test_missing_before_commit_uses_event_fallback_and_blocks)",
        re.MULTILINE,
    )
    replacement = textwrap.dedent('''
    def test_allows_new_branch_creation_without_commits(script_path: Path, tmp_path: Path):
        """
        Echter Sonderfall:
        Neuer Branch / erster Push ohne Commit-Dateiliste im Event.

        Unterschied zum Regressionstest
        test_new_branch_fallback_uses_event_payload_and_blocks_forbidden_path:
        Dort liefert das Event verbotene Dateien und muss blockiert werden.
        Hier liefert das Event gar keine Commit-Dateien; dieser Push bleibt erlaubt.
        """
        repo = tmp_path / "repo"
        init_repo(repo)
        _ = commit_file(repo, "README.md", "hi", "init")

        event_path = tmp_path / "event.json"
        event_path.write_text(json.dumps({"commits": []}), encoding="utf-8")

        env = {
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_ACTOR": "stemmer",
            "GITHUB_REF_NAME": "stemmer_teil_1",
            "EVENT_BEFORE": "0000000000000000000000000000000000000000",
            "EVENT_SHA": git(repo, "rev-parse", "HEAD").stdout.strip(),
            "GITHUB_EVENT_PATH": str(event_path),
        }
        res = run([str(script_path)], cwd=repo, env=env, check=False)
        assert res.returncode == 0, res.stdout
        assert "Erlaube diesen Push" in res.stdout
    ''')
    new_text, n = pattern.subn(replacement + "\n", text, count=1)
    if n != 1:
        raise RuntimeError("Konnte test_allows_new_branch_creation_without_commits nicht robust ersetzen.")
    return new_text


def insert_new_test(text: str) -> str:
    marker = "\ndef test_missing_before_commit_uses_event_fallback_and_blocks"
    if "test_new_branch_fallback_uses_event_payload_and_blocks_forbidden_path" in text:
        return text
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError("Konnte Einfügemarker für den neuen Regressionstest nicht finden.")
    return text[:idx] + NEW_TEST + text[idx:]



def main() -> None:
    root = Path.cwd()
    test_file = root / "test_restrict_paths.py"
    tools_dir = root / "tools"
    script_file = tools_dir / "restrict_paths.sh"

    if not test_file.exists():
        raise SystemExit(f"Fehlt: {test_file}")

    tools_dir.mkdir(parents=True, exist_ok=True)
    script_file.write_text(SCRIPT_CONTENT, encoding="utf-8", newline="\n")
    script_file.chmod(script_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    text = test_file.read_text(encoding="utf-8")
    text = replace_allows_new_branch_test(text)
    text = insert_new_test(text)
    test_file.write_text(text, encoding="utf-8", newline="\n")

    print("Updated:")
    print(f" - {script_file}")
    print(f" - {test_file}")


if __name__ == "__main__":
    main()
