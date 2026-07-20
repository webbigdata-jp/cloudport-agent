#!/usr/bin/env bash
# Build code.zip for Alibaba Cloud Function Compute Web Function
# (Custom Runtime, Linux x86_64, CPython 3.12).
#
# Only the application entry point, compatibility layer, optional Streamlit
# config, generated bootstrap, and installed runtime dependencies are packaged.
# Repository documentation, tests, smoke_test.py, deploy.sh itself, and other
# development files are intentionally excluded.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
BUILD_DIR="${BUILD_DIR:-.fc-build}"
VENV_DIR="${VENV_DIR:-.venv-fc}"
ZIP_FILE="${ZIP_FILE:-code.zip}"
KEEP_BUILD_DIR="${KEEP_BUILD_DIR:-0}"
ALLOW_UNSUPPORTED_BUILD_HOST="${ALLOW_UNSUPPORTED_BUILD_HOST:-0}"
CHECK_ONLY="${CHECK_ONLY:-0}"

RUNTIME_FILES=(
  app.py
  cloudport_compat.py
)

TEMP_FILES=()
cleanup() {
  local path
  for path in "${TEMP_FILES[@]:-}"; do
    [[ -n "$path" ]] && rm -f "$path"
  done
  if [[ "$KEEP_BUILD_DIR" != "1" ]]; then
    rm -rf "$BUILD_DIR" "$VENV_DIR"
  fi
}
trap cleanup EXIT

for cmd in uv zip unzip; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $cmd" >&2
    exit 1
  }
done

for file in "${RUNTIME_FILES[@]}" requirements.txt; do
  [[ -f "$file" ]] || {
    echo "ERROR: required file not found: $file" >&2
    exit 1
  }
done

HOST_OS="$(uname -s)"
HOST_ARCH="$(uname -m)"
if [[ "$HOST_OS" != "Linux" || "$HOST_ARCH" != "x86_64" ]]; then
  if [[ "$ALLOW_UNSUPPORTED_BUILD_HOST" != "1" ]]; then
    cat >&2 <<EOF_HOST
ERROR: deploy.sh must run on Linux x86_64 because pip installs host-native
wheels into the Function Compute ZIP.
Detected: ${HOST_OS}/${HOST_ARCH}

Supported examples:
  - Linux x86_64
  - WSL2 on an x86_64 Windows host

Native macOS/Windows builds are not supported by this script.
Set ALLOW_UNSUPPORTED_BUILD_HOST=1 only when you have independently verified
that every installed wheel matches the FC runtime.
EOF_HOST
    exit 1
  fi
fi

if [[ "$CHECK_ONLY" == "1" ]]; then
  echo "Source validation passed."
  echo "Build target: Linux/x86_64, Python ${PYTHON_VERSION}"
  echo "Runtime source files: ${RUNTIME_FILES[*]}"
  echo "Optional source file: .streamlit/config.toml"
  echo "Development files are not copied by deploy.sh."
  exit 0
fi

echo "[1/5] Preparing Python ${PYTHON_VERSION} build environment..."
rm -rf "$BUILD_DIR" "$VENV_DIR" "$ZIP_FILE"
uv venv "$VENV_DIR" --python "$PYTHON_VERSION" --seed

PYTHON_BIN="$VENV_DIR/bin/python"
[[ -x "$PYTHON_BIN" ]] || {
  echo "ERROR: Python was not created at $PYTHON_BIN" >&2
  exit 1
}

if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
  echo "[info] pip was not seeded; installing pip into $VENV_DIR..."
  uv pip install --python "$PYTHON_BIN" pip
fi

BUILD_PYTHON_VERSION="$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$BUILD_PYTHON_VERSION" != "$PYTHON_VERSION" ]]; then
  echo "ERROR: requested Python $PYTHON_VERSION, created Python $BUILD_PYTHON_VERSION" >&2
  exit 1
fi

echo "[2/5] Copying runtime application files..."
mkdir -p "$BUILD_DIR"
cp "${RUNTIME_FILES[@]}" "$BUILD_DIR/"

if [[ -f .streamlit/config.toml ]]; then
  mkdir -p "$BUILD_DIR/.streamlit"
  cp .streamlit/config.toml "$BUILD_DIR/.streamlit/config.toml"
fi

echo "[3/5] Installing runtime dependencies..."
"$PYTHON_BIN" -m pip install \
  --disable-pip-version-check \
  --only-binary=:all: \
  --target "$BUILD_DIR" \
  --requirement requirements.txt

cat > "$BUILD_DIR/bootstrap" <<'BOOTSTRAP'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export HOME="${STREAMLIT_HOME:-/tmp}"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

if [[ -n "${PYTHON_BIN:-}" ]]; then
  runtime_python="$PYTHON_BIN"
elif command -v python3.12 >/dev/null 2>&1; then
  runtime_python="$(command -v python3.12)"
elif command -v python3 >/dev/null 2>&1; then
  runtime_python="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  runtime_python="$(command -v python)"
else
  echo "ERROR: Python 3.12 runtime not found (tried python3.12, python3, python)." >&2
  exit 127
fi

runtime_version="$($runtime_python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$runtime_version" != "3.12" ]]; then
  echo "ERROR: code.zip targets Python 3.12, but $runtime_python is Python $runtime_version." >&2
  echo "Use an FC custom runtime that provides Python 3.12." >&2
  exit 1
fi

exec "$runtime_python" -m streamlit run app.py \
  --global.developmentMode=false \
  --server.address=0.0.0.0 \
  --server.port="${FC_CUSTOM_LISTEN_PORT:-9000}" \
  --server.headless=true
BOOTSTRAP
chmod +x "$BUILD_DIR/bootstrap"

echo "[4/5] Creating $ZIP_FILE..."
(
  cd "$BUILD_DIR"
  zip -rq -y "../$ZIP_FILE" .
)

ZIP_LIST_FILE="$(mktemp)"
TEMP_FILES+=("$ZIP_LIST_FILE")
unzip -Z1 "$ZIP_FILE" > "$ZIP_LIST_FILE"

for required_entry in app.py cloudport_compat.py bootstrap; do
  if ! grep -Fx "$required_entry" "$ZIP_LIST_FILE" >/dev/null; then
    echo "ERROR: $required_entry is missing from the root of $ZIP_FILE" >&2
    exit 1
  fi
done

for forbidden_entry in \
  main.py pyproject.toml README.md smoke_test.py deploy.sh \
  MIGRATION_NOTES.md TESTING.md TEST_RESULTS.md REPO_INTEGRATION.md; do
  if grep -Fx "$forbidden_entry" "$ZIP_LIST_FILE" >/dev/null; then
    echo "ERROR: development file was unexpectedly packaged: $forbidden_entry" >&2
    exit 1
  fi
done

echo "[5/5] Package validation passed."
echo "Created: $ZIP_FILE ($(du -h "$ZIP_FILE" | cut -f1))"
echo "Build Python: $($PYTHON_BIN --version 2>&1)"
echo "Build host: ${HOST_OS}/${HOST_ARCH}"
echo "Packaged application files: ${RUNTIME_FILES[*]}, bootstrap"
echo "Upload $ZIP_FILE to an Alibaba Cloud Function Compute Web Function (Custom Runtime)."
