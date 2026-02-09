#!/usr/bin/env python3
import subprocess
import tempfile
import shutil
import os
import sys
import re

REPO = "https://github.com/ParabolInc/parabol.git"
ENV_PATH = "./.env"
PATCH_FILE = "patch.js"

BASE_IMAGE = "parabol:base"
UPSTREAM_DOCKERFILE = "docker/images/parabol-ubi/dockerfiles/basic.dockerfile"

IMAGE = "parabol:local"
LOCAL_DOCKERFILE = os.path.abspath("setup.dockerfile")

BUILDER_IMAGE = "parabol:builder"
BUILD_DOCKERFILE = os.path.abspath("docker/build.dockerfile")
RUNTIME_DOCKERFILE = os.path.abspath("docker/runtime.dockerfile")


def die(msg, code=1):
    print("ERROR:", msg, file=sys.stderr)
    sys.exit(code)


def run(cmd, env):
    print("> " + " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)


def out(cmd, env):
    print("> " + " ".join(cmd))
    return subprocess.check_output(cmd, env=env, text=True).strip()


def ensure_buildx(env):
    try:
        l = out(["docker", "buildx", "ls"], env)
    except subprocess.CalledProcessError:
        l = ""

    if "*" in l:
        return

    run([
        "docker", "buildx", "create",
        "--name", BUILDER_IMAGE,
        "--driver", "docker-container",
        "--use"
    ], env)

    run(["docker", "buildx", "inspect", BUILDER_IMAGE, "--bootstrap"], env)


def clone_repo(tmp, env):
    run(["git", "clone", "--depth", "1", REPO, tmp], env)


def prepare_env(tmp):
    env_example = os.path.join(tmp, ".env.example")
    if not os.path.exists(env_example):
        die(".env.example missing in repo")

    shutil.copyfile(env_example, ENV_PATH)

    replace_line(ENV_PATH, "# IS_ENTERPRISE", "IS_ENTERPRISE=true")
    replace_line(ENV_PATH, "HOST=", "HOST=10.127.80.126")
    replace_line(ENV_PATH, "PROTO=", "PROTO=http")
    replace_line(ENV_PATH, "PORT=", "PORT=80")
    replace_line(ENV_PATH, "CDN_BASE_URL=", "CDN_BASE_URL=//10.127.80.126/parabol")

    shutil.copyfile(ENV_PATH, os.path.join(tmp, ".env"))


def replace_line(path, key, replacement):
    pattern = re.compile(rf"^\s*#?\s*{re.escape(key)}=.*$")
    replaced = False
    out_lines = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if pattern.match(line):
                out_lines.append(replacement + "\n")
                replaced = True
            else:
                out_lines.append(line)

    if not replaced:
        out_lines.append(replacement + "\n")

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out_lines)


def copy_patch(tmp):
    shutil.copyfile(PATCH_FILE, os.path.join(tmp, PATCH_FILE))


def build_builder(tmp, sha, env):
    print("Building builder image...")

    run([
        "docker", "buildx", "build",
        "--build-arg", "PUBLIC_URL=/parabol",
        "--build-arg", "CDN_BASE_URL=//10.127.80.126/parabol",
        "--build-arg", f"DD_GIT_COMMIT_SHA={sha}",
        "--build-arg", f"DD_GIT_REPOSITORY_URL={REPO}",
        "-f", BUILD_DOCKERFILE,
        "-t", BUILDER_IMAGE,
        tmp
    ], env)


def build_upstream(tmp, sha, env):
    print("Building upstream base image...")

    run([
        "docker", "buildx", "build",
        "--build-arg", "_NODE_VERSION=22",
        "--build-arg", f"DD_GIT_COMMIT_SHA={sha}",
        "--build-arg", f"DD_GIT_REPOSITORY_URL={REPO}",
        "-f", os.path.join(tmp, UPSTREAM_DOCKERFILE),
        "-t", BASE_IMAGE,
        tmp
    ], env)


def build_runtime(tmp, env):
    run([
        "docker", "buildx", "build",
        "-f", RUNTIME_DOCKERFILE,
        "-t", IMAGE,
        tmp
    ], env)


def main():
    tmp = tempfile.mkdtemp(prefix="parabol-build-", dir=os.path.expanduser("~"))

    env = dict(os.environ)
    env["DOCKER_BUILDKIT"] = "1"

    try:
        ensure_buildx(env)
        clone_repo(tmp, env)
        prepare_env(tmp)
        copy_patch(tmp)

        sha = out(["git", "-C", tmp, "rev-parse", "HEAD"], env)

        build_builder(tmp, sha, env)
        build_upstream(tmp, sha, env)
        build_runtime(tmp, env)

        print("Built image:", IMAGE)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
