#!/usr/bin/env python3
import subprocess
import tempfile
import shutil
import os
import sys

REPO = "https://github.com/ParabolInc/parabol.git"
ENV_PATH = "./.env"
IMAGE = "parabol:local"
LOCAL_DOCKERFILE = os.path.abspath("setup.dockerfile")
CACHE_DIR = os.path.abspath(".docker-cache")


def die(msg, code=1):
    print("ERROR:", msg, file=sys.stderr)
    sys.exit(code)


def run(cmd, env=None, allow_fail=False):
    """Run command, print it and exit on non-zero (unless allow_fail)."""
    print(">", " ".join(cmd))
    r = subprocess.run(cmd, env=env)
    if r.returncode != 0 and not allow_fail:
        sys.exit(r.returncode)
    return r.returncode


def run_output(cmd, env=None):
    """Run command and return stdout (text). Raises on non-zero."""
    print(">", " ".join(cmd))
    return subprocess.check_output(cmd, env=env, text=True)


def replace_line(path, needle, replacement):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out = []
    replaced = False

    for line in lines:
        if needle in line:
            out.append(replacement + "\n")
            replaced = True
        else:
            out.append(line)

    if not replaced:
        out.append(replacement + "\n")

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out)


def ensure_buildx(env):
    """Ensure buildx is available and a builder is active. Uses the provided env."""
    try:
        run_output(["docker", "info"], env=env)
    except subprocess.CalledProcessError:
        die("Cannot talk to Docker daemon. Upewnij się, że w tym shellu docker działa (rootless: poprawnie ustawiony DOCKER_HOST / XDG_RUNTIME_DIR).")

    bx = subprocess.run(["docker", "buildx", "version"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if bx.returncode != 0:
        die("docker buildx is not available in your docker CLI. Ensure docker CLI supports buildx.")

    try:
        result = run_output(["docker", "buildx", "ls"], env=env)
    except subprocess.CalledProcessError:
        die("Failed to list buildx builders. Check Docker daemon / buildx installation.")

    if "*" in result:
        print("buildx builder already active")
        return

    print("Creating and using a new buildx builder...")
    run(["docker", "buildx", "create", "--use"], env=env)


tmp = tempfile.mkdtemp(prefix="parabol-build-", dir=os.path.expanduser("~"))
print("tmp:", tmp)
os.makedirs(CACHE_DIR, exist_ok=True)

env = os.environ.copy()
env.setdefault("DOCKER_BUILDKIT", "1")

try:
    ensure_buildx(env)

    run(["git", "clone", "--depth", "1", REPO, tmp], env=env)

    env_example = os.path.join(tmp, ".env.example")
    if not os.path.exists(env_example):
        die(f".env.example not found in repo root ({env_example})")
    shutil.copyfile(env_example, ENV_PATH)

    replace_line(ENV_PATH, "# IS_ENTERPRISE", "IS_ENTERPRISE=true")
    replace_line(ENV_PATH, "HOST=", "HOST='10.127.80.126'")
    replace_line(ENV_PATH, "PROTO=", "PROTO='http'")
    replace_line(ENV_PATH, "PORT=", "PORT='80'")
    replace_line(ENV_PATH, "CDN_BASE_URL=", "CDN_BASE_URL='//10.127.80.126/parabol'")

    shutil.copyfile(ENV_PATH, os.path.join(tmp, ".env"))

    sha = run_output(["git", "-C", tmp, "rev-parse", "HEAD"], env=env).strip()

    build_cmd = [
        "docker", "buildx", "build",
        "--cache-from", f"type=local,src={CACHE_DIR}",
        "--cache-to", f"type=local,dest={CACHE_DIR},mode=max",
        "--build-arg", f"PUBLIC_URL=/parabol",
        "--build-arg", f"CDN_BASE_URL=//10.127.80.126/parabol",
        "--build-arg", f"DD_GIT_COMMIT_SHA={sha}",
        "--build-arg", f"DD_GIT_REPOSITORY_URL={REPO}",
        "-f", LOCAL_DOCKERFILE,
        "-t", IMAGE,
        tmp
    ]

    run(build_cmd, env=env)

    print("Built image:", IMAGE)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
