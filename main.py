from collections import namedtuple
import os
import re
import subprocess
import sys

Config = namedtuple(
    "Config",
    [
        "fail_on_error",
        "quiet_mode",
        "check_mode",
        "print_diff_mode",
        "main_branch",
        "only_changed_files",
        "additional_args",
    ],
)


def get_head_commit():
    process = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=sys.stderr.buffer,
        universal_newlines=True,
    )
    if process.returncode != 0:
        raise Exception(f"unexpected non-zero return code from git: {repr(process)}")
    return process.stdout


def get_merge_base(main_branch, head_commit):
    process = subprocess.run(
        ["git", "merge-base", f"origin/{main_branch}", head_commit],
        stdout=subprocess.PIPE,
        stderr=sys.stderr.buffer,
        universal_newlines=True,
    )
    return process.stdout


def deepen_shallow_commit(main_branch, head_commit):
    while get_merge_base(main_branch, head_commit) == "":
        process = subprocess.run(
            ["git", "fetch", "-q" "--deepen=10", "origin", main_branch, head_commit],
            stdout=sys.stderr.buffer,
            stderr=sys.stderr.buffer,
            universal_newlines=True,
        )
        if process.returncode != 0:
            raise Exception(f"unhandled git fetch error: {repr(process)}")


def get_changed_files(main_branch):
    head_commit = get_head_commit()
    deepen_shallow_commit(main_branch, head_commit)
    merge_base = get_merge_base(main_branch, head_commit)
    process = subprocess.run(
        [
            "git",
            "diff",
            "--diff-filter=d",
            "--name-only",
            f"{merge_base}..{head_commit}",
        ],
        stdout=subprocess.PIPE,
        stderr=sys.stderr.buffer,
        universal_newlines=True,
    )
    changed_python_files = []
    for f in process.stdout.splitlines():
        if f.endswith(".py"):
            changed_python_files.append(f)
    return changed_python_files


def invoke_black_on_changed_files(args, changed_python_files):
    if not changed_python_files:
        return 0, ""
    with open("/tmp/changed_python_files.txt", "w") as f:
        f.writelines(changed_python_files)

    cmd = ["cat", "/tmp/changed_python_files.txt", "|", "xargs", "black"] + args
    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    all_output = str(process.stdout or "") + str(process.stderr or "")
    return process.returncode, all_output


def invoke_black_on_all_files(args):
    process = subprocess.run(
        ["black"] + args + ["."],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    all_output = str(process.stdout or "") + str(process.stderr or "")
    return process.returncode, all_output


def main(config):
    invocation_args = []
    if config.print_diff_mode:
        invocation_args.append("--diff")
    if config.check_mode:
        invocation_args.append("--check")
    if config.quiet_mode:
        invocation_args.append("--quiet")

    is_formatting = False
    action_msg_mode = "Formatting"
    if not config.print_diff_mode and not config.check_mode:
        is_formatting = True
        action_msg_mode = "Checking"

    if config.only_changed_files:
        action_msg_mode += " (changed files only)"
    else:
        action_msg_mode += " (all files)"

    if config.additional_args:
        invocation_args.expand(config.additional_args.split(" "))

    print(f"[action-black] {action_msg_mode} python code using the black formatter...")
    if config.only_changed_files:
        changed_python_files = get_changed_files(config.main_branch)
        retcode, stdout = invoke_black_on_changed_files(
            invocation_args, changed_python_files
        )
    else:
        retcode, stdout = invoke_black_on_all_files(invocation_args)
    stdout = str(stdout) or ""

    if not config.quiet_mode:
        for line in stdout.split("\n"):
            print(f"[action-black][process:black] {line}")

    is_error = False
    if not is_formatting:
        # just check status code
        print("::set-output name=is_formatted::false")
        if retcode == 1:
            is_error = True
        elif retcode == 123:
            is_error = True
            print(
                f"[action-black] ERROR: (non-formatting) Black found a syntax error when checking the files (error code: {retcode})."
            )
        else:
            print(
                f"[action-black] ERROR: (non-formatting) Something went wrong while trying to run the black formatter (error code: {retcode})."
            )
            os.exit(1)
    else:
        # Check if black formatted files
        matcher = re.compile(r"\s?[0-9]+\sfiles?\sreformatted(\.|,)\s?")
        if matcher.search(stdout):
            print("[action-black] INFO: found formatted changes!")
            print("::set-output name=is_formatted::true")
        else:
            print("[action-black] INFO: no formatted changes found.")
            print("::set-output name=is_formatted::false")

        # Check if an error was encountered
        if retcode == 0:
            pass
        elif retcode == 123:
            is_error = True
            print(
                f"[action-black] ERROR: (formatting) Black found a syntax error when checking the files (error code: {retcode})."
            )
        else:
            print(
                f"[action-black] ERROR: (formatting) Something went wrong while trying to run the black formatter (error code: {retcode})."
            )
            os.exit(1)

    if config.fail_on_error and is_error:
        os.exit(1)


def env_bool(variable_name, default_value):
    return str(
        os.getenv(f"INPUT_{variable_name.upper()}", default=default_value)
    ).lower() in ["true", "t", "1"]


def env(variable_name, default_value):
    return os.getenv(f"INPUT_{variable_name.upper()}", default=default_value)


if __name__ == "__main__":
    config = Config(
        fail_on_error=env_bool("fail_on_error", False),
        quiet_mode=env_bool("quiet_mode", False),
        check_mode=env_bool("check_mode", False),
        print_diff_mode=env_bool("print_diff_mode", True),
        main_branch=env("main_branch", "main"),
        only_changed_files=env_bool("only_changed_files", False),
        additional_args=env("additional_args", ""),
    )
    print(f"[action-black] configuration: {config}")

    main(config)
