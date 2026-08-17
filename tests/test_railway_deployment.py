from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_railway_declares_the_nested_asgi_start_command():
    railway_config = (ROOT / "railway.toml").read_text(encoding="utf-8")
    start_script = ROOT / "start.sh"

    assert 'builder = "RAILPACK"' in railway_config
    assert 'startCommand = "./start.sh"' in railway_config
    assert start_script.stat().st_mode & 0o111
    assert "tvc_api.main:app" in start_script.read_text(encoding="utf-8")
