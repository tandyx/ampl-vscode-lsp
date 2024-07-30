# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""Implementation of tool support over LSP."""
from __future__ import annotations

import json
import os
import pathlib
import sys
import typing as t


import utils
import ampl_lsp


# Ensure that we can import LSP libraries, and other bundled libraries.


# **********************************************************
# Imports needed for the language server goes below this.
# **********************************************************
# pylint: disable=wrong-import-position,import-error
import lsprotocol.types as lsp

RUNNER = pathlib.Path(__file__).parent / "lsp_runner.py"

TOOL_ARGS = []  # default arguments always passed to your tool.

LSP_SERVER = ampl_lsp.AMPLServer(
    module="ampl-lsp", name="ampl language server", tool_args=TOOL_ARGS, version="0.1.0"
)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
def did_close(params: lsp.DidCloseTextDocumentParams) -> None:
    """LSP handler for textDocument/didClose request."""
    document = LSP_SERVER.workspace.get_document(params.text_document.uri)
    # Publishing empty diagnostics to clear the entries for this file.
    LSP_SERVER.publish_diagnostics(document.uri, [])


# **********************************************************
# Required Language Server Initialization and Exit handlers.
# **********************************************************
@LSP_SERVER.feature(lsp.INITIALIZE)
def initialize(params: lsp.InitializeParams) -> None:
    """LSP handler for initialize request."""
    LSP_SERVER.log(f"CWD Server: {os.getcwd()}")

    paths = "\r\n   ".join(sys.path)
    LSP_SERVER.log(f"sys.path used to run Server:\r\n   {paths}")

    LSP_SERVER.GLOBAL_SETTINGS.update(
        **params.initialization_options.get("globalSettings", {})
    )
    settings = params.initialization_options["settings"]
    LSP_SERVER.update_workspace_settings(settings)
    LSP_SERVER.log(
        f"Settings used to run Server:\r\n{json.dumps(settings, indent=4, ensure_ascii=False)}\r\n"
    )
    LSP_SERVER.log(
        f"Global settings:\r\n{json.dumps(LSP_SERVER.GLOBAL_SETTINGS, indent=4, ensure_ascii=False)}\r\n"
    )


@LSP_SERVER.feature(lsp.EXIT)
def on_exit(_params: t.Optional[t.Any] = None) -> None:
    """Handle clean up on exit."""
    utils.shutdown_json_rpc()


@LSP_SERVER.feature(lsp.SHUTDOWN)
def on_shutdown(_params: t.Optional[t.Any] = None) -> None:
    """Handle clean up on shutdown."""
    utils.shutdown_json_rpc()


@LSP_SERVER.feature(
    lsp.TEXT_DOCUMENT_COMPLETION,
    lsp.CompletionOptions(trigger_characters=["."]),
)
def completions(params: lsp.CompletionParams) -> lsp.CompletionList:
    """LSP handler for textDocument/completion request."""
    document = LSP_SERVER.workspace.get_document(params.text_document.uri)
    current_line = document.lines[params.position.line].strip()
    if not current_line.endswith("hello."):
        return []
    return [
        lsp.CompletionItem(label="world"),
        lsp.CompletionItem(label="friend"),
    ]


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DEFINITION)
def definition(params: lsp.TextDocumentPositionParams) -> lsp.Location | None:
    """LSP handler for textDocument/definition request."""
    document = LSP_SERVER.workspace.get_document(params.text_document.uri)
    current_line = document.lines[params.position.line].strip()


# *****************************************************
# Start the server.
# *****************************************************
if __name__ == "__main__":
    LSP_SERVER.start_io()
