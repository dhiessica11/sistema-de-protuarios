"""A automação só executa comandos após aprovar a versão consultada."""

import importlib.util
import io
import json
import subprocess
from pathlib import Path

import pytest

PATH_SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "deploy_dev.py"
spec = importlib.util.spec_from_file_location("deploy_dev", PATH_SCRIPT)
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)
SHA = "a" * 40


def resposta(runs):
    return io.BytesIO(json.dumps({"workflow_runs": runs}).encode())


def run_ci(**overrides):
    return {
        "head_sha": SHA,
        "head_branch": "desenvolvimento",
        "event": "push",
        "run_number": 2,
        "status": "completed",
        "conclusion": "success",
        **overrides,
    }


def test_ci_exige_sucesso_do_commit_e_branch(monkeypatch):
    monkeypatch.setattr(deploy.urllib.request, "urlopen", lambda *_a, **_k: resposta([run_ci()]))
    deploy.ci_aprovado(SHA)
    for runs in [
        [],
        [run_ci(conclusion="failure")],
        [run_ci(status="in_progress", conclusion=None)],
        [run_ci(head_sha="b" * 40)],
        [run_ci(head_branch="main")],
        [run_ci(event="pull_request")],
        [run_ci(), run_ci(run_number=3, conclusion="failure")],
    ]:
        monkeypatch.setattr(
            deploy.urllib.request, "urlopen", lambda *_a, runs=runs, **_k: resposta(runs)
        )
        with pytest.raises(deploy.DeployError):
            deploy.ci_aprovado(SHA)


def test_deploy_falha_fechado_antes_docker(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(deploy, "validar_ambiente", lambda: None)

    def comando(*args, **_kwargs):
        calls.append(args)
        if args[:2] == ("git", "rev-parse"):
            return SHA
        return ""

    monkeypatch.setattr(deploy, "comando", comando)

    def negar(_sha):
        raise deploy.DeployError("CI não aprovado")

    monkeypatch.setattr(deploy, "ci_aprovado", negar)
    with pytest.raises(deploy.DeployError):
        deploy.executar(tmp_path)
    assert not any(c[0] == "docker" for c in calls)
    assert not (tmp_path / "ultimo-deploy.txt").exists()


def test_deploy_ordem_e_marcador(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(deploy, "validar_ambiente", lambda: None)
    monkeypatch.setattr(deploy, "ci_aprovado", lambda _sha: calls.append(("ci",)))
    monkeypatch.setattr(deploy, "health", lambda: calls.append(("health",)))

    def comando(*args, **_kwargs):
        calls.append(args)
        if args[:2] == ("git", "rev-parse"):
            return SHA
        return ""

    monkeypatch.setattr(deploy, "comando", comando)
    deploy.executar(tmp_path)
    assert calls.index(("ci",)) < calls.index(("docker", "compose", "stop", "web", "worker"))
    assert calls.index(("docker", "compose", "stop", "web", "worker")) < calls.index(
        ("git", "merge", "--ff-only", SHA)
    )
    assert (
        calls.index(
            (
                "docker",
                "compose",
                "run",
                "--rm",
                "--no-deps",
                "web",
                "python",
                "manage.py",
                "migrate",
                "--noinput",
            )
        )
        < calls.index(("docker", "compose", "up", "-d", "web", "worker"))
        < calls.index(("health",))
    )
    assert (tmp_path / "ultimo-deploy.txt").read_text().strip() == SHA


def test_falha_na_migracao_nao_marca_sucesso(tmp_path, monkeypatch):
    monkeypatch.setattr(deploy, "validar_ambiente", lambda: None)
    monkeypatch.setattr(deploy, "ci_aprovado", lambda _sha: None)

    def comando(*args, **_kwargs):
        if args[:2] == ("git", "rev-parse"):
            return SHA
        if args[:3] == ("docker", "compose", "run"):
            raise subprocess.CalledProcessError(1, args)
        return ""

    monkeypatch.setattr(deploy, "comando", comando)
    with pytest.raises(subprocess.CalledProcessError):
        deploy.executar(tmp_path)
    assert not (tmp_path / "ultimo-deploy.txt").exists()


def test_ambiente_recusa_arquivos_locais_e_settings_nao_dev(tmp_path, monkeypatch):
    monkeypatch.setattr(deploy, "REPO", tmp_path)
    env = tmp_path / ".env"
    env.write_text("DJANGO_SETTINGS_MODULE=config.settings.prod\n")
    with pytest.raises(deploy.DeployError, match="config.settings.dev"):
        deploy.validar_ambiente()
    env.write_text("DJANGO_SETTINGS_MODULE=config.settings.dev\n")

    def comando(*args, **_kwargs):
        if args[:3] == ("git", "remote", "get-url"):
            return "https://github.com/dhiessica11/sistema-de-protuarios.git"
        if args[:2] == ("git", "branch"):
            return "desenvolvimento"
        if args[:2] == ("git", "status"):
            return " M arquivo-local"
        raise AssertionError(args)

    monkeypatch.setattr(deploy, "comando", comando)
    with pytest.raises(deploy.DeployError, match="alterações locais"):
        deploy.validar_ambiente()


def test_falha_no_health_nao_marca_deploy(tmp_path, monkeypatch):
    monkeypatch.setattr(deploy, "validar_ambiente", lambda: None)
    monkeypatch.setattr(deploy, "ci_aprovado", lambda _sha: None)

    def comando(*args, **_kwargs):
        return SHA if args[:2] == ("git", "rev-parse") else ""

    def falha_health():
        raise deploy.DeployError("health indisponível")

    monkeypatch.setattr(deploy, "comando", comando)
    monkeypatch.setattr(deploy, "health", falha_health)
    with pytest.raises(deploy.DeployError, match="health"):
        deploy.executar(tmp_path)
    assert not (tmp_path / "ultimo-deploy.txt").exists()
