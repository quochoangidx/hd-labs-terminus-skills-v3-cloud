from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "setup_agent_hooks.py"
SPEC = importlib.util.spec_from_file_location("setup_agent_hooks", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_install_skill_links_is_idempotent(tmp_path: Path) -> None:
    (tmp_path / ".agent/skills").mkdir(parents=True)
    MODULE.ensure_skill_links(tmp_path)
    MODULE.ensure_skill_links(tmp_path)

    for relative in (".agents/skills", ".codex/skills", ".claude/skills"):
        assert (tmp_path / relative).is_symlink()
        assert (tmp_path / relative).resolve() == (tmp_path / ".agent/skills").resolve()


def test_trust_updates_preserve_existing_settings(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    codex = tmp_path / "config.toml"
    codex.write_text('model = "gpt-5.6-sol"\n', encoding="utf-8")
    claude = tmp_path / "claude.json"
    claude.write_text(json.dumps({"theme": "dark", "projects": {}}), encoding="utf-8")

    MODULE.trust_codex(repo, codex)
    MODULE.trust_codex(repo, codex)
    MODULE.trust_claude(repo, claude)
    MODULE.trust_claude(repo, claude)

    codex_text = codex.read_text(encoding="utf-8")
    assert 'model = "gpt-5.6-sol"' in codex_text
    assert codex_text.count(f'[projects."{repo}"]') == 1
    assert 'trust_level = "trusted"' in codex_text
    claude_data = json.loads(claude.read_text(encoding="utf-8"))
    assert claude_data["theme"] == "dark"
    assert claude_data["projects"][str(repo)]["hasTrustDialogAccepted"] is True
