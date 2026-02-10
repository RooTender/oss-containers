import subprocess
import tempfile
import shutil
import os
import json

REPO = "https://github.com/ParabolInc/parabol.git"
ENV_PATH = "./.env"
BASE_IMAGE = "parabol:base"
IMAGE = "parabol:local"
LOCAL_DOCKERFILE = os.path.abspath("setup.dockerfile")

def replace_line(path, key, replacement):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if line.startswith(key):
            lines[i] = f"{replacement}\n"

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def run(cmd, env=None):
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)

def get_tailscale_ip():
    result = subprocess.run(
        ["tailscale", "ip", "-4"],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()

print(f"Building image for: {get_tailscale_ip()}")

tmp = tempfile.mkdtemp(prefix="parabol-build-", dir=os.path.expanduser("~"))
print("tmp:", tmp)

try:
    run(["git", "clone", "--depth", "1", REPO, tmp])

    with open(os.path.join(tmp, "package.json")) as f:
        pkg = json.load(f)

    node_version = pkg["engines"]["node"].lstrip("^")
    print("node version:", node_version)

    sha = subprocess.check_output(
        ["git", "-C", tmp, "rev-parse", "HEAD"],
        text=True
    ).strip()

    run([
        "docker", "run", "--rm",
        "-v", f"{tmp}:/app",
        "-w", "/app",
        "node:22-trixie-slim",
        "bash", "-c",
        "apt-get update && apt-get install -y git && "
        "corepack enable && "
        "pnpm install --frozen-lockfile && "
        "pnpm build"
    ])

    env = os.environ.copy()
    env["DOCKER_BUILDKIT"] = "1"

    run([
        "docker", "build",
        "--build-arg", f"_NODE_VERSION={node_version}",
        "--build-arg", f"DD_GIT_COMMIT_SHA={sha}",
        "--build-arg", f"DD_GIT_REPOSITORY_URL={REPO}",
        "-f", os.path.join(tmp, "docker/images/parabol-ubi/dockerfiles/basic.dockerfile"),
        "-t", BASE_IMAGE,
        tmp
    ], env=env)

    run([
        "docker", "build",
        "-f", LOCAL_DOCKERFILE,
        "-t", IMAGE,
        tmp
    ])

    print("Built image:", IMAGE)

    cid = subprocess.check_output(
        ["docker", "create", IMAGE],
        text=True
    ).strip()

    run(["docker", "cp", f"{cid}:/home/node/parabol/.env.example", "./.env"])
    run(["docker", "rm", cid])

    replace_line(ENV_PATH, "# IS_ENTERPRISE", "IS_ENTERPRISE=true")
    replace_line(ENV_PATH, "HOST=", f"HOST='{get_tailscale_ip()}'")
    replace_line(ENV_PATH, "PROTO=", "PROTO='http'")

finally:
    shutil.rmtree(tmp, ignore_errors=True)
