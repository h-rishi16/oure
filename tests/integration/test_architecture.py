import ast
import os

import pytest


def test_strict_decoupling():
    """
    Ensures no layer imports from a layer it does not own, EXCEPT core/models.py.
    The core layer itself shouldn't import from other layers.
    """
    project_root = os.path.dirname(os.path.dirname(__file__))
    oure_dir = os.path.join(project_root, "oure")

    for root, _, files in os.walk(oure_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                layer = os.path.basename(root)

                with open(file_path) as f:
                    tree = ast.parse(f.read(), filename=file_path)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        module = node.module
                        if module and module.startswith("oure."):
                            imported_layer = module.split(".")[1]

                            # Core layer cannot import anything else
                            if layer == "core" and imported_layer != "core":
                                pytest.fail(
                                    f"Core layer {file} imports from {imported_layer}"
                                )

                            # Other layers: can only import from themselves or core
                            if layer != "core" and imported_layer not in (
                                layer,
                                "core",
                            ):
                                # CLI layer can import anything as it's the entrypoint
                                if layer == "cli":
                                    continue
                                # New Architecture explicitly allows Conjunction and Uncertainty to depend on BasePropagator
                                if (
                                    layer in ("conjunction", "uncertainty", "risk")
                                    and imported_layer == "physics"
                                ):
                                    continue
                                pytest.fail(
                                    f"Layer {layer} in {file} imports from {imported_layer}"
                                )
