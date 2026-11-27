from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_generator() -> ModuleType:
    path = (
        Path(__file__).resolve().parents[3] / ".circleci" / "scripts" / "generate_lambda_matrix.py"
    )
    spec = importlib.util.spec_from_file_location("generate_lambda_matrix", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_catalog_commands_override_checkout_python_version() -> None:
    """Test that catalog commands use the Python version installed in the job image."""
    job = _load_generator().build_catalog_job("us-west-2")

    commands = [
        step["run"]["command"] for step in job["steps"] if isinstance(step, dict) and "run" in step
    ]

    assert commands[0] == (
        'PYENV_VERSION="$PYTHON_VERSION" pyenv exec python -m pip install --quiet boto3'
    )
    assert (
        'PYENV_VERSION="$PYTHON_VERSION" pyenv exec python '
        ".circleci/scripts/lambda_layer_catalog.py" in commands[1]
    )
    assert (
        'PYENV_VERSION="$PYTHON_VERSION" .circleci/scripts/publish-lambda-layer-catalog.sh'
        in commands[2]
    )
