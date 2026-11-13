#!/usr/bin/env bash
# Compiles the pure-Java engine + JUnit shim + engine tests with plain javac and runs every @Test.
# Needs only a JDK (no Maven, no network). Output goes to backend-java/out/engine-check (git-ignored).
# Exit code is non-zero when compilation, the purity check or any test fails.
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="out/engine-check"
rm -rf "$OUT"
mkdir -p "$OUT"

# Purity check: engine sources may import only java.* and com.stockanalyzer.engine.*
bad=$(grep -rhE '^\s*import\s' src/main/java/com/stockanalyzer/engine | grep -vE '^\s*import\s+(static\s+)?(java\.|com\.stockanalyzer\.engine\.)' || true)
if [ -n "$bad" ]; then
  echo "ENGINE PURITY VIOLATION: non-java.* imports in engine/:" >&2
  echo "$bad" >&2
  exit 2
fi

SOURCES=$(find tools/junit-shim src/main/java/com/stockanalyzer/engine src/test/java/com/stockanalyzer/engine tools/EngineTestRunner.java -name '*.java')
# shellcheck disable=SC2086
javac -proc:none -Xlint:none -encoding UTF-8 -d "$OUT" $SOURCES

CLASSES=$(cd src/test/java && find com/stockanalyzer/engine -name '*Test.java' | sed 's/\.java$//; s#/#.#g' | sort)
# shellcheck disable=SC2086
java -Dfile.encoding=UTF-8 -cp "$OUT" EngineTestRunner $CLASSES
