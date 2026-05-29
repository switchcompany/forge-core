#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CENTRAL_PATH="$SCRIPT_DIR"

printf "\n🧪 Forge Core — Setup\n"
printf "====================================\n\n"
printf "Central hub: ${GREEN}%s${NC}\n\n" "$CENTRAL_PATH"

if [[ $# -ge 1 ]]; then
  PROJECT_PATH="$1"
else
  read -r -p "Enter the full path to the target project: " PROJECT_PATH
fi

PROJECT_PATH="${PROJECT_PATH/#\~/$HOME}"

if [[ ! -d "$PROJECT_PATH" ]]; then
  printf "${RED}Error:${NC} directory not found: %s\n" "$PROJECT_PATH"
  exit 1
fi

printf "Setting up Forge Core in ${GREEN}%s${NC}\n\n" "$PROJECT_PATH"

mkdir -p \
  "$PROJECT_PATH/.github/prompts" \
  "$PROJECT_PATH/.github/ISSUE_TEMPLATE" \
  "$PROJECT_PATH/.github/workflows" \
  "$PROJECT_PATH/knowledge-packs"

copy_file() {
  local source="$1"
  local target="$2"
  cp "$source" "$target"
  printf "  • copied %s\n" "${target#"$PROJECT_PATH"/}"
}

copy_file "$CENTRAL_PATH/.github/copilot-instructions.md" "$PROJECT_PATH/.github/copilot-instructions.md"
copy_file "$CENTRAL_PATH/.github/copilot-setup-steps.yml" "$PROJECT_PATH/.github/copilot-setup-steps.yml"
copy_file "$CENTRAL_PATH/.github/workflows/copilot-setup-steps.yml" "$PROJECT_PATH/.github/workflows/copilot-setup-steps.yml"
copy_file "$CENTRAL_PATH/.github/agent-config.yml" "$PROJECT_PATH/.github/agent-config.yml"
copy_file "$CENTRAL_PATH/.github/ISSUE_TEMPLATE/analyze-and-test.yml" "$PROJECT_PATH/.github/ISSUE_TEMPLATE/analyze-and-test.yml"

for prompt in "$CENTRAL_PATH/.github/prompts/"*.prompt.md; do
  copy_file "$prompt" "$PROJECT_PATH/.github/prompts/$(basename "$prompt")"
done

for pack in "$CENTRAL_PATH/knowledge-packs/"*.md; do
  copy_file "$pack" "$PROJECT_PATH/knowledge-packs/$(basename "$pack")"
done

if [[ ! -f "$PROJECT_PATH/LEARNINGS.md" ]]; then
  copy_file "$CENTRAL_PATH/LEARNINGS.md" "$PROJECT_PATH/LEARNINGS.md"
else
  printf "  • kept existing LEARNINGS.md (not overwritten)\n"
fi

python3 - "$PROJECT_PATH/.github/agent-config.yml" "$CENTRAL_PATH" <<'PY'
from pathlib import Path
import sys

config_path = Path(sys.argv[1])
central_path = sys.argv[2]
text = config_path.read_text()
lines = []
for line in text.splitlines():
    if line.startswith("central_agent_path:"):
        lines.append(f'central_agent_path: "{central_path}"')
    else:
        lines.append(line)
config_path.write_text("\n".join(lines) + "\n")
PY

printf "\n${GREEN}✅ Forge Core files installed${NC}\n"
printf "${GREEN}✅ Central path configured${NC}\n"
printf "${GREEN}✅ Knowledge packs synced${NC}\n"

printf "\nNext steps:\n"
printf "  1. Open the target project in your IDE or terminal\n"
printf "  2. Run with any AI runtime (Copilot, Claude, GPT, local LLM)\n"
printf "  3. Execute the full-workflow or targeted prompt\n"
printf "  4. Review LEARNINGS.md after each run for new patterns\n\n"
