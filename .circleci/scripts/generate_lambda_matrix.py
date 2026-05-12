#!/usr/bin/env python3
"""Generates a CircleCI continuation config for lambda layer matrix builds.

One job is emitted per (runtime, arch) combination. x86_64 jobs run on the
default machine executor; arm64 jobs add resource_class: arm.medium.
"""
import argparse
import sys

VALID_ARCHS = {"x86_64", "arm64"}


def job_name(runtime: str, arch: str) -> str:
    runtime_slug = "py" + runtime.replace(".", "")
    return f"lambda_layer_{runtime_slug}_{arch}"


def build_job(runtime: str, arch: str, sdk_version: str, region: str, account_id: str) -> dict:
    zip_path = f"dist/lambda/albert-layer-{sdk_version}-py{runtime}-{arch}.zip"

    publish_cmd_parts = [
        ".circleci/scripts/publish-lambda-layer.sh",
        f'  --zip        "{zip_path}"',
        f'  --region     "{region}"',
        f'  --runtime    "{runtime}"',
        f'  --arch       "{arch}"',
        f'  --sdk-version "{sdk_version}"',
    ]
    if account_id:
        publish_cmd_parts.append(f'  --account-id "{account_id}"')

    publish_cmd = " \\\n".join(publish_cmd_parts)

    machine: dict = {"image": "ubuntu-2204:current"}
    job: dict = {"machine": machine}
    if arch == "arm64":
        job["resource_class"] = "arm.medium"

    job["steps"] = [
        "checkout",
        {
            "run": {
                "name": "Set AWS default region",
                "command": 'echo "export AWS_DEFAULT_REGION=${AWS_REGION}" >> $BASH_ENV',
            }
        },
        "aws-cli/setup",
        {
            "run": {
                "name": f"Build lambda layer zip (py{runtime}, {arch})",
                "command": (
                    "set -euo pipefail\n"
                    f".circleci/scripts/build-lambda-layer.sh \\\n"
                    f'  --version "{sdk_version}" \\\n'
                    f'  --runtime "{runtime}" \\\n'
                    f'  --arch    "{arch}"'
                ),
            }
        },
        {"store_artifacts": {"path": "dist/lambda", "destination": "lambda-layer"}},
        {
            "run": {
                "name": f"Publish lambda layer (py{runtime}, {arch})",
                "command": (
                    "set -euo pipefail\n"
                    f'ZIP_PATH="{zip_path}"\n'
                    'if [[ ! -f "${ZIP_PATH}" ]]; then\n'
                    '  echo "Layer zip not found at ${ZIP_PATH}" >&2; exit 1\n'
                    "fi\n"
                    f"{publish_cmd}"
                ),
            }
        },
    ]
    return job


def generate(
    runtimes: list[str],
    archs: list[str],
    sdk_version: str,
    region: str,
    account_id: str,
) -> str:
    lines: list[str] = [
        "version: 2.1",
        "",
        "# These parameters are declared so the continuation pipeline accepts",
        "# the forwarded parameters from the setup pipeline without errors.",
        "parameters:",
        "  lambda_layer:",
        "    type: boolean",
        "    default: false",
        "  lambda_sdk_version:",
        "    type: string",
        "    default: \"\"",
        "  lambda_runtimes:",
        "    type: string",
        "    default: \"3.10\"",
        "  lambda_archs:",
        "    type: string",
        "    default: \"x86_64\"",
        "  lambda_region:",
        "    type: string",
        "    default: \"us-east-1\"",
        "  lambda_account_id:",
        "    type: string",
        "    default: \"\"",
        "",
        "orbs:",
        "  aws-cli: circleci/aws-cli@4.0",
        "",
        "jobs:",
    ]

    workflow_jobs: list[str] = []

    for runtime in runtimes:
        for arch in archs:
            name = job_name(runtime, arch)
            job = build_job(runtime, arch, sdk_version, region, account_id)
            lines.append(f"  {name}:")
            lines.extend(_render_job(job))
            lines.append("")
            workflow_jobs.append(name)

    lines += [
        "workflows:",
        "  lambda_layer_publish_all:",
        "    jobs:",
    ]
    for name in workflow_jobs:
        lines.append(f"      - {name}:")
        lines.append("          context: dev")

    return "\n".join(lines) + "\n"


def _render_job(job: dict, indent: int = 4) -> list[str]:
    """Renders a job dict as indented YAML lines."""
    lines: list[str] = []
    pad = " " * indent

    for key, value in job.items():
        if isinstance(value, dict):
            lines.append(f"{pad}{key}:")
            for k, v in value.items():
                lines.append(f"{pad}  {k}: {v}")
        elif isinstance(value, str):
            lines.append(f"{pad}{key}: {value}")
        elif isinstance(value, list):
            lines.append(f"{pad}{key}:")
            for item in value:
                if isinstance(item, str):
                    lines.append(f"{pad}  - {item}")
                elif isinstance(item, dict):
                    first = True
                    for k, v in item.items():
                        if first:
                            lines.append(f"{pad}  - {k}:")
                            first = False
                        else:
                            lines.append(f"{pad}    {k}:")
                        if isinstance(v, dict):
                            for dk, dv in v.items():
                                if "\n" in str(dv):
                                    lines.append(f"{pad}      {dk}: |")
                                    for dl in str(dv).splitlines():
                                        lines.append(f"{pad}        {dl}")
                                else:
                                    lines.append(f"{pad}      {dk}: {dv}")
                        elif isinstance(v, str):
                            if "\n" in v:
                                lines.append(f"{pad}    {k}: |")
                                for vl in v.splitlines():
                                    lines.append(f"{pad}      {vl}")
                            else:
                                lines.append(f"{pad}    {k}: {v}")
        else:
            lines.append(f"{pad}{key}: {value}")

    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtimes", required=True)
    parser.add_argument("--archs", required=True)
    parser.add_argument("--sdk-version", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--account-id", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    runtimes = [r.strip() for r in args.runtimes.split(",") if r.strip()]
    archs = [a.strip() for a in args.archs.split(",") if a.strip()]

    invalid = [a for a in archs if a not in VALID_ARCHS]
    if invalid:
        print(f"Invalid arch(es): {invalid}. Must be one of {sorted(VALID_ARCHS)}.", file=sys.stderr)
        sys.exit(1)

    if not runtimes:
        print("--runtimes must not be empty.", file=sys.stderr)
        sys.exit(1)

    config = generate(runtimes, archs, args.sdk_version, args.region, args.account_id)

    with open(args.output, "w") as f:
        f.write(config)

    print(f"Generated continuation config with {len(runtimes) * len(archs)} job(s) -> {args.output}")
    for r in runtimes:
        for a in archs:
            print(f"  {job_name(r, a)}")


if __name__ == "__main__":
    main()
