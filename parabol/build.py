import subprocess
import tempfile
import shutil
import os
import json
import sys

REPO = "[https://github.com/ParabolInc/parabol.git](https://github.com/ParabolInc/parabol.git)"
ENV_PATH = "./.env"
IMAGE = "parabol:local"
LOCAL_DOCKERFILE = os.path.abspath("setup.dockerfile")
CACHE_DIR = os.path.abspath(".docker-cache")

def run(cmd, env=None, allow_fail=False):
    print(">", " ".join(cmd))
    r = subprocess.run(cmd, env=env)
    if not allow_fail and r.returncode != 0:
        sys.exit(r.returncode)

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

def ensure_buildx():
    r = subprocess.run(["docker", "buildx", "version"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL)

    if r.returncode != 0:
        print("buildx not available in docker")
        sys.exit(1)

    result = subprocess.check_output(["docker", "buildx", "ls"], text=True)

    if "*" in result:
        print("buildx builder already active")
        return

    print("creating buildx builder...")
    run(["docker", "buildx", "create", "--use"])

tmp = tempfile.mkdtemp(prefix="parabol-build-", dir=os.path.expanduser("~"))
print("tmp:", tmp)

try:
    os.makedirs(CACHE_DIR, exist_ok=True)

    ensure_buildx()

    # clone repo
    run(["git", "clone", "--depth", "1", REPO, tmp])

    # copy .env.example -> local .env
    env_example = os.path.join(tmp, ".env.example")
    shutil.copyfile(env_example, ENV_PATH)

    # modify env
    replace_line(ENV_PATH, "# IS_ENTERPRISE", "IS_ENTERPRISE=true")
    replace_line(ENV_PATH, "HOST=", "HOST='10.127.80.126'")
    replace_line(ENV_PATH, "PROTO=", "PROTO='http'")
    replace_line(ENV_PATH, "PORT=", "PORT='80'")
    replace_line(ENV_PATH, "CDN_BASE_URL=", "CDN_BASE_URL='//10.127.80.126/parabol'")

    shutil.copyfile(ENV_PATH, os.path.join(tmp, ".env"))

    # read node version (optional)
    with open(os.path.join(tmp, "package.json")) as f:
        pkg = json.load(f)
    node_version = pkg["engines"]["node"].lstrip("^")
    print("node version:", node_version)

    sha = subprocess.check_output(
        ["git", "-C", tmp, "rev-parse", "HEAD"],
        text=True
    ).strip()

    env = os.environ.copy()
    env["DOCKER_BUILDKIT"] = "1"

    run([
        "docker", "buildx", "build",
        "--progress=plain",
        "--cache-from", f"type=local,src={CACHE_DIR}",
        "--cache-to", f"type=local,dest={CACHE_DIR},mode=max",
        "--build-arg", f"PUBLIC_URL=/parabol",
        "--build-arg", f"CDN_BASE_URL=//10.127.80.126/parabol",
        "--build-arg", f"DD_GIT_COMMIT_SHA={sha}",
        "--build-arg", f"DD_GIT_REPOSITORY_URL={REPO}",
        "-f", LOCAL_DOCKERFILE,
        "-t", IMAGE,
        tmp
    ], env=env)

    print("Built image:", IMAGE)

finally:
    shutil.rmtree(tmp, ignore_errors=True)
