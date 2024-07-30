"""random helper functions that are used in multiple places in the project."""

import os
import sys
import typing as t


def update_sys_path(
    path_to_add: str, strategy: t.Literal["useBundled", "fromEnvironment"]
) -> None:
    """add given path to `sys.path`. update sys.path before importing any bundled libraries.

    args:
        - `path_to_add (str)`: the path to add to `sys.path`.
        - `strategy (str)`: the strategy to use when adding the path to `sys.path`.
    """
    if path_to_add in sys.path or not os.path.isdir(path_to_add):
        return
    if strategy == "useBundled":
        sys.path.insert(0, path_to_add)
        return
    if strategy == "fromEnvironment":
        sys.path.append(path_to_add)
