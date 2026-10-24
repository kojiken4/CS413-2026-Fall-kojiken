"""Access the unchanged Assignment 5 AST without using its evaluator.

Other solution modules should use ``from .source_ast import ast`` so they all
share the same source classes. The supplied module also defines an interpreter;
loading those definitions does not call it or adopt its language semantics.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import ModuleType


_MODULE_NAME = "_cs413_assign06_lambda1_vp"
_SOURCE_PATH = Path(__file__).resolve().parents[2] / "05" / "lambda1_vp.py"


def _load_source_ast() -> ModuleType:
    if sys.version_info < (3, 12):
        raise RuntimeError("Assignment 6 requires Python 3.12 or later")

    if _MODULE_NAME in sys.modules:
        return sys.modules[_MODULE_NAME]

    spec = spec_from_file_location(_MODULE_NAME, _SOURCE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load the supplied source AST: {_SOURCE_PATH}")

    module = module_from_spec(spec)
    # Dataclasses resolve annotations through the defining module's registry entry.
    sys.modules[_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        # Do not leave an incomplete module available after a failed import.
        sys.modules.pop(_MODULE_NAME, None)
        raise
    return module


ast = _load_source_ast()
