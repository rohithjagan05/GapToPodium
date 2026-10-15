"""Checks that keep the Docker image in step with the code, without needing Docker installed."""

import re

from src.config import PROJECT_ROOT


def _pins(name: str) -> dict[str, str]:
    lines = (PROJECT_ROOT / name).read_text().splitlines()
    return dict(re.match(r"([\w.-]+)==(\S+)", ln).groups() for ln in lines if "==" in ln)


def test_api_requirements_match_the_main_pins():
    api, main = _pins("requirements-api.txt"), _pins("requirements.txt")
    assert {pkg: api[pkg] for pkg in api} == {pkg: main.get(pkg) for pkg in api}


def test_dockerfile_copies_every_module_the_api_imports():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text()
    api_source = (PROJECT_ROOT / "src" / "api.py").read_text()
    export_source = (PROJECT_ROOT / "src" / "export.py").read_text()
    imported = set(re.findall(r"from src\.(\w+) import", api_source + export_source))
    for module in imported | {"api"}:
        assert f"src/{module}.py" in dockerfile, f"Dockerfile does not copy src/{module}.py"
    assert "COPY serving/" in dockerfile


def test_container_listens_on_the_port_the_host_gives_it():
    assert "--host 0.0.0.0" in (PROJECT_ROOT / "Dockerfile").read_text()
    assert "${PORT:-8000}" in (PROJECT_ROOT / "Dockerfile").read_text()