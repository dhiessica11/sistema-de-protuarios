#!/usr/bin/env python3
"""Atualização local de desenvolvimento após CI do commit da branch passar."""

import fcntl
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BRANCH = "desenvolvimento"
REPOSITORY = "dhiessica11/sistema-de-protuarios"
ORIGENS = {
    f"https://github.com/{REPOSITORY}.git",
    f"https://github.com/{REPOSITORY}",
    f"git@github.com:{REPOSITORY}.git",
}


class DeployError(Exception):
    pass


def comando(*args, capturar=False):
    result = subprocess.run(
        args,
        cwd=REPO,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capturar else None,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    return result.stdout.strip() if capturar else ""


def validar_ambiente():
    try:
        linhas = (REPO / ".env").read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DeployError("Não foi possível ler o arquivo .env do projeto.") from exc
    valores = [
        linha.split("=", 1)[1].strip().strip("\"'")
        for linha in linhas
        if linha.strip().startswith("DJANGO_SETTINGS_MODULE=")
    ]
    if valores != ["config.settings.dev"]:
        raise DeployError(
            "A automação exige DJANGO_SETTINGS_MODULE=config.settings.dev no .env."
        )
    if comando("git", "remote", "get-url", "origin", capturar=True) not in ORIGENS:
        raise DeployError("O remoto origin não corresponde ao repositório esperado.")
    if comando("git", "branch", "--show-current", capturar=True) != BRANCH:
        raise DeployError("O checkout deve estar na branch desenvolvimento.")
    if comando("git", "status", "--porcelain", "--untracked-files=all", capturar=True):
        raise DeployError(
            "Existem alterações locais não ignoradas; atualização interrompida."
        )


def ci_aprovado(sha):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise DeployError("Identificador de commit inválido.")
    url = (
        f"https://api.github.com/repos/{REPOSITORY}/actions/workflows/ci.yml/runs"
        f"?branch={BRANCH}&event=push&head_sha={sha}&per_page=30"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "prontuario-deploy-dev",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            dados = json.load(response)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise DeployError(
            "Não foi possível consultar o CI do GitHub; tente mais tarde."
        ) from exc
    runs = [
        r
        for r in dados.get("workflow_runs", [])
        if r.get("head_sha") == sha
        and r.get("head_branch") == BRANCH
        and r.get("event") == "push"
    ]
    if not runs:
        raise DeployError("Nenhuma execução de CI por push encontrada para o commit.")
    run = max(runs, key=lambda r: r.get("run_number", 0))
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise DeployError(
            "O CI do commit ainda não terminou com sucesso; aguardando próxima verificação."
        )


def health():
    request = urllib.request.Request(
        "http://127.0.0.1:8000/health/", headers={"User-Agent": "prontuario-deploy-dev"}
    )
    # Docker pode levar alguns segundos para iniciar o Django.
    import time

    for tentativa in range(15):
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                if response.status == 200 and json.load(response).get("status") == "ok":
                    return
        except (OSError, ValueError, urllib.error.URLError):
            pass
        if tentativa < 14:
            time.sleep(2)
    raise DeployError("O health check não respondeu; verifique os logs dos containers.")


def executar(state_dir):
    validar_ambiente()
    comando("git", "fetch", "origin", BRANCH)
    sha = comando("git", "rev-parse", f"refs/remotes/origin/{BRANCH}", capturar=True)
    local = comando("git", "rev-parse", "HEAD", capturar=True)
    marker = state_dir / "ultimo-deploy.txt"
    if (
        marker.exists()
        and marker.read_text(encoding="ascii").strip() == sha
        and local == sha
    ):
        print("Nenhuma atualização pendente.")
        return
    ci_aprovado(sha)
    try:
        comando("git", "merge-base", "--is-ancestor", local, sha)
    except subprocess.CalledProcessError as exc:
        raise DeployError(
            "A branch local divergiu do GitHub; atualização interrompida."
        ) from exc
    # Os containers usam bind mount: pare-os antes de trocar os arquivos.
    comando("docker", "compose", "stop", "web", "worker")
    comando("git", "merge", "--ff-only", sha)
    comando("docker", "compose", "build", "web", "worker")
    comando("docker", "compose", "up", "-d", "--wait", "db", "redis")
    comando(
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
    comando("docker", "compose", "up", "-d", "web", "worker")
    health()
    tmp = marker.with_suffix(".tmp")
    tmp.write_text(sha + "\n", encoding="ascii")
    tmp.replace(marker)
    print(f"Atualização de desenvolvimento concluída: {sha[:12]}")


def main():
    state_dir = (
        Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
        / "prontuario-ed"
    )
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (state_dir / "deploy.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise DeployError("Outra atualização já está em execução.") from exc
        executar(state_dir)


if __name__ == "__main__":
    try:
        main()
    except (DeployError, subprocess.CalledProcessError, OSError) as exc:
        print(f"Atualização não concluída: {exc}", file=sys.stderr)
        sys.exit(1)
