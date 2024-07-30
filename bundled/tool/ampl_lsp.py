import os
import pathlib
import typing as t
import sys
import copy
import traceback

import utils


utils.update_sys_path(
    os.fspath(pathlib.Path(__file__).parent.parent / "libs"),
    os.getenv("LS_IMPORT_STRATEGY", "useBundled"),
)

# pylint: disable=wrong-import-position,import-error
import lsprotocol.types as lsp
from pygls import server, uris, workspace


class AMPLServer(server.LanguageServer):
    """AMPL Language Server implementation."""

    WORKSPACE_SETTINGS = {}
    GLOBAL_SETTINGS = {}
    LOG_TYPE = lsp.MessageType.Log

    def __init__(self, module: str, name: str, tool_args: list[str], **kwargs):
        """initialize the server.

        args:
            - `module (str)`: the module name of the tool.
            - `name (str)`: the display name of the tool.
            - `tool_args (list[str])`: default arguments always passed to your tool.
            - `kwargs`: passed to `LanguageServer`.
        """
        super().__init__(name=name, **kwargs)
        self.module: str = module
        self.name: str = name
        self.tool_args: list[str] = tool_args

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.module!r}, {self.name!r})"

    def log(self, message: str, msg_type: lsp.MessageType = None) -> None:
        """Log message to output.

        args:
            - `message (str)`: message to log
            - `msg_type (lsp.MessageType)`: message type
        """
        self.show_message_log(message, msg_type or self.LOG_TYPE)

    def get_global_defaults(self) -> dict[str, t.Any]:
        """get global settings

        returns:
            - `dict`: global settings
        """
        _ref = self.__class__.GLOBAL_SETTINGS  # mem ref to global settings
        return {
            "path": _ref.get("path", []),
            "interpreter": _ref.get("interpreter", [sys.executable]),
            "args": _ref.get("args", []),
            "importStrategy": _ref.get("importStrategy", "useBundled"),
            "showNotifications": _ref.get("showNotifications", "off"),
        }

    def update_workspace_settings(self, settings: list[dict[str, t.Any]]) -> None:
        """Update workspace settings

        args:
            - `settings (list[dict[str, Any]])`: settings to update
        """
        if not settings:
            key = os.getcwd()
            self.__class__.WORKSPACE_SETTINGS[key] = {
                "cwd": key,
                "workspaceFS": key,
                "workspace": uris.from_fs_path(key),
                **self.get_global_defaults(),
            }
            return
        for _set in settings:
            key = uris.to_fs_path(_set["workspace"])
            self.__class__.WORKSPACE_SETTINGS[key] = {
                "cwd": key,
                **_set,
                "workspaceFS": key,
            }

    def get_document_key(self, document: workspace.Document) -> str | None:
        """gets the document key

        args:
            - `document (workspace.Document)`: document
        returns:
        """

        if self.WORKSPACE_SETTINGS:
            document_workspace = pathlib.Path(document.path)
            workspaces = {s["workspaceFS"] for s in self.WORKSPACE_SETTINGS.values()}

            # Find workspace settings for the given file.
            while document_workspace != document_workspace.parent:
                if str(document_workspace) in workspaces:
                    return str(document_workspace)
                document_workspace = document_workspace.parent
        return None

    def get_settings_by_document(
        self, document: workspace.Document | None
    ) -> dict[str, t.Any]:
        """get settings by document

        args:
            - `document (workspace.Document)`: document
            - `returns`: settings
        """
        if document is None or document.path is None:
            return list(self.WORKSPACE_SETTINGS.values())[0]

        key = self.get_document_key(document)
        if key is None:
            # This is either a non-workspace file or there is no workspace.
            key = os.fspath(pathlib.Path(document.path).parent)
            return {
                "cwd": key,
                "workspaceFS": key,
                "workspace": uris.from_fs_path(key),
                **self.get_global_defaults(),
            }

        return self.WORKSPACE_SETTINGS[str(key)]

    def get_settings_by_path(self, file_path: pathlib.Path) -> dict[str, t.Any]:
        """get settings by path

        args:
            - `file_path (pathlib.Path)`: file path
        """

        workspaces = {
            s["workspaceFS"] for s in self.__class__.WORKSPACE_SETTINGS.values()
        }

        while file_path != file_path.parent:
            str_file_path = str(file_path)
            if str_file_path in workspaces:
                return self.__class__.WORKSPACE_SETTINGS[str_file_path]
            file_path = file_path.parent

        setting_values = list(self.__class__.WORKSPACE_SETTINGS.values())
        return setting_values[0]

    def run_tool_on_document(
        self,
        document: workspace.Document,
        use_stdin: bool = False,
        extra_args: t.Optional[t.Sequence[str]] = None,
    ) -> utils.RunResult | None:
        """Runs tool on the given document.

        if use_stdin is true then contents of the document is passed to the
        tool via stdin.
        """
        if extra_args is None:
            extra_args = []
        if str(document.uri).startswith("vscode-notebook-cell"):
            return None

        # deep copy here to prevent accidentally updating global settings.
        settings = copy.deepcopy(self.get_settings_by_document(document))

        code_workspace = settings["workspaceFS"]
        cwd = settings["cwd"]

        use_path = False
        use_rpc = False
        if settings["path"]:
            # 'path' setting takes priority over everything.
            use_path = True
            argv = settings["path"]
        elif settings["interpreter"] and not utils.is_current_interpreter(
            settings["interpreter"][0]
        ):
            # If there is a different interpreter set use JSON-RPC to the subprocess
            # running under that interpreter.
            argv = [self.module]
            use_rpc = True
        else:
            # if the interpreter is same as the interpreter running this
            # process then run as module.
            argv = [self.module]

        argv += self.tool_args + settings["args"] + extra_args

        if use_stdin:
            # TODO: update these to pass the appropriate arguments to provide document contents
            # to tool via stdin.
            # For example, for pylint args for stdin looks like this:
            #     pylint --from-stdin <path>
            # Here `--from-stdin` path is used by pylint to make decisions on the file contents
            # that are being processed. Like, applying exclusion rules.
            # It should look like this when you pass it:
            #     argv += ["--from-stdin", document.path]
            # Read up on how your tool handles contents via stdin. If stdin is not supported use
            # set use_stdin to False, or provide path, what ever is appropriate for your tool.
            argv += []
        else:
            argv += [document.path]

        if use_path:
            # This mode is used when running executables.
            self.log(" ".join(argv))
            self.log(f"CWD Server: {cwd}")
            result = utils.run_path(
                argv=argv,
                use_stdin=use_stdin,
                cwd=cwd,
                source=document.source.replace("\r\n", "\n"),
            )
            if result.stderr:
                self.log(result.stderr)
        elif use_rpc:
            # This mode is used if the interpreter running this server is different from
            # the interpreter used for running this server.
            self.log(" ".join(settings["interpreter"] + ["-m"] + argv))
            self.log(f"CWD Linter: {cwd}")

            result = utils.run_over_json_rpc(
                workspace=code_workspace,
                interpreter=settings["interpreter"],
                module=self.module,
                argv=argv,
                use_stdin=use_stdin,
                cwd=cwd,
                source=document.source,
            )
            if result.exception:
                self.log(result.exception, lsp.MessageType.Error)
                result = utils.RunResult(result.stdout, result.stderr)
            elif result.stderr:
                self.log(result.stderr)
        else:
            # In this mode the tool is run as a module in the same process as the language server.
            self.log(" ".join([sys.executable, "-m"] + argv))
            self.log(f"CWD Linter: {cwd}")
            # This is needed to preserve sys.path, in cases where the tool modifies
            # sys.path and that might not work for this scenario next time around.
            with utils.substitute_attr(sys, "path", sys.path[:]):
                try:
                    # TODO: `utils.run_module` is equivalent to running `python -m <pytool-module>`.
                    # If your tool supports a programmatic API then replace the function below
                    # with code for your tool. You can also use `utils.run_api` helper, which
                    # handles changing working directories, managing io streams, etc.
                    # Also update `_run_tool` function and `utils.run_module` in `lsp_runner.py`.
                    result = utils.run_module(
                        module=self.module,
                        argv=argv,
                        use_stdin=use_stdin,
                        cwd=cwd,
                        source=document.source,
                    )
                except Exception:
                    self.log(traceback.format_exc(chain=True), lsp.MessageType.Error)
                    raise
            if result.stderr:
                self.log(result.stderr)

        self.log(f"{document.uri} :\r\n{result.stdout}")
        return result

    def run_tool(self, extra_args: t.Sequence[str]) -> utils.RunResult:
        """Runs tool."""
        # deep copy here to prevent accidentally updating global settings.
        settings = copy.deepcopy(self.get_settings_by_document(None))

        code_workspace = settings["workspaceFS"]
        cwd = settings["workspaceFS"]

        use_path = False
        use_rpc = False
        if len(settings["path"]) > 0:
            # 'path' setting takes priority over everything.
            use_path = True
            argv = settings["path"]
        elif len(settings["interpreter"]) > 0 and not utils.is_current_interpreter(
            settings["interpreter"][0]
        ):
            # If there is a different interpreter set use JSON-RPC to the subprocess
            # running under that interpreter.
            argv = [self.module]
            use_rpc = True
        else:
            # if the interpreter is same as the interpreter running this
            # process then run as module.
            argv = [self.module]

        argv += extra_args

        if use_path:
            # This mode is used when running executables.
            self.log(" ".join(argv))
            self.log(f"CWD Server: {cwd}")
            result = utils.run_path(argv=argv, use_stdin=True, cwd=cwd)
            if result.stderr:
                self.log(result.stderr)
        elif use_rpc:
            # This mode is used if the interpreter running this server is different from
            # the interpreter used for running this server.
            self.log(" ".join(settings["interpreter"] + ["-m"] + argv))
            self.log(f"CWD Linter: {cwd}")
            result = utils.run_over_json_rpc(
                workspace=code_workspace,
                interpreter=settings["interpreter"],
                module=self.module,
                argv=argv,
                use_stdin=True,
                cwd=cwd,
            )
            if result.exception:
                self.log(result.exception, lsp.MessageType.Error)
                result = utils.RunResult(result.stdout, result.stderr)
            elif result.stderr:
                self.log(result.stderr)
        else:
            # In this mode the tool is run as a module in the same process as the language server.
            self.log(" ".join([sys.executable, "-m"] + argv))
            self.log(f"CWD Linter: {cwd}")
            # This is needed to preserve sys.path, in cases where the tool modifies
            # sys.path and that might not work for this scenario next time around.
            with utils.substitute_attr(sys, "path", sys.path[:]):
                try:
                    # TODO: `utils.run_module` is equivalent to running `python -m <pytool-module>`.
                    # If your tool supports a programmatic API then replace the function below
                    # with code for your tool. You can also use `utils.run_api` helper, which
                    # handles changing working directories, managing io streams, etc.
                    result = utils.run_module(
                        module=self.module, argv=argv, use_stdin=True, cwd=cwd
                    )
                except Exception:
                    self.log(traceback.format_exc(chain=True), lsp.MessageType.Error)
                    raise
            if result.stderr:
                self.log(result.stderr)
        self.log(f"\r\n{result.stdout}\r\n")
        return result
