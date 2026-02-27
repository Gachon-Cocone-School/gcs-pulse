import importlib.util
import re
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "migrate_and_seed.py"


def _load_migrate_and_seed_module():
    spec = importlib.util.spec_from_file_location("migrate_and_seed_script", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_role_email_lists_cover_privileged_roles():
    module = _load_migrate_and_seed_module()

    for role in ("gcs", "교수", "admin"):
        assert role in module.ROLE_EMAIL_LISTS
        emails = module.ROLE_EMAIL_LISTS[role]
        assert emails
        assert all(email == email.strip() for email in emails)
        assert all("@" in email for email in emails)


def test_seed_invite_code_generator_outputs_expected_format():
    module = _load_migrate_and_seed_module()

    code = module._generate_invite_code()

    assert len(code) == 8
    assert re.fullmatch(r"[A-Z0-9]{8}", code)


def test_seed_script_keeps_idempotent_terms_and_consents_sql():
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "INSERT INTO terms" in source
    assert "ON CONFLICT(type, version) DO UPDATE" in source
    assert "INSERT INTO consents" in source
    assert "ON CONFLICT(user_id, term_id) DO NOTHING" in source
