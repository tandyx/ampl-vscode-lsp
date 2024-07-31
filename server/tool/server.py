"""Implementation of tool support over LSP."""

import json
import os
import pathlib
import re
import sys
import typing as t

import ampl_utils
import utils

utils.update_sys_path(
    os.fspath(pathlib.Path(__file__).parent.parent / "libs"),
    os.getenv("LS_IMPORT_STRATEGY", "useBundled"),
)

import lsprotocol.types as lsp
from ampl_lsp import AMPLServer

RUNNER = pathlib.Path(__file__).parent / "lsp_runner.py"

TOOL_ARGS = []  # default arguments always passed to your tool.

LSP_SERVER = AMPLServer(
    module="ampl-lsp", name="ampl language server", tool_args=TOOL_ARGS, version="0.1.0"
)


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


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
def did_close(params: lsp.DidCloseTextDocumentParams) -> None:
    """LSP handler for textDocument/didClose request."""
    document = LSP_SERVER.workspace.get_document(params.text_document.uri)
    # Publishing empty diagnostics to clear the entries for this file.
    LSP_SERVER.publish_diagnostics(document.uri, [])


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: AMPLServer, params: lsp.DidOpenTextDocumentParams):
    """Parse each document when it is opened"""
    doc = ls.workspace.get_text_document(params.text_document.uri)
    ls.parse_document(doc)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: AMPLServer, params: lsp.DidOpenTextDocumentParams):
    """Parse each document when it is changed"""
    doc = ls.workspace.get_text_document(params.text_document.uri)
    ls.parse_document(doc)


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


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_HOVER)
def hover(params: lsp.TextDocumentPositionParams) -> lsp.Hover | None:
    """LSP handler for textDocument/hover request."""
    document = LSP_SERVER.workspace.get_document(params.text_document.uri)
    current_line = document.lines[params.position.line].strip()
    if not current_line.endswith("hello."):
        return None
    return lsp.Hover(
        contents=[
            lsp.MarkedString(
                language="markdown",
                value="This is a hover message for `hello`.",
            )
        ]
    )


# @LSP_SERVER.feature(lsp.TEXT_DOCUMENT_TYPE_DEFINITION)
# def goto_type_definition(ls: AMPLServer, params: lsp.TypeDefinitionParams):
#     """Jump to an object's type definition."""
#     doc = ls.workspace.get_text_document(params.text_document.uri)
#     index = ls.index_.get(doc.uri)
#     if index is None:
#         return

#     try:
#         line = doc.lines[params.position.line]
#     except IndexError:
#         line = ""

#     word = doc.word_at_position(params.position)

#     # for match in ampl_utils.AMPLArgument.regex.finditer(line):
#     #     if match.group("name") == word:
#     #         if (range_ := index["types"].get(match.group("type"), None)) is not None:
#             return lsp.Location(uri=doc.uri, range=range_)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DEFINITION)
def goto_definition(ls: AMPLServer, params: lsp.DefinitionParams):
    """Jump to an object's definition."""
    doc = ls.workspace.get_text_document(params.text_document.uri)
    index = ls.index_.get(doc.uri)
    if index is None:
        return

    word = doc.word_at_position(params.position)

    # Is word a type?
    if (range_ := index["variable"].get(word, None)) is not None:
        return lsp.Location(uri=doc.uri, range=range_)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DECLARATION)
def goto_declaration(ls: AMPLServer, params: lsp.DeclarationParams):
    """Jump to an object's declaration."""
    doc = ls.workspace.get_text_document(params.text_document.uri)
    index = ls.index_.get(doc.uri)
    if index is None:
        return

    try:
        line = doc.lines[params.position.line]
    except IndexError:
        line = ""

    word = doc.word_at_position(params.position)

    for match in ampl_utils.Argument.regex.finditer(line):
        if match.group("name") == word:
            linum = params.position.line
            return lsp.Location(
                uri=doc.uri,
                range=lsp.Range(
                    start=lsp.Position(line=linum, character=match.start()),
                    end=lsp.Position(line=linum, character=match.end()),
                ),
            )


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_IMPLEMENTATION)
def goto_implementation(ls: AMPLServer, params: lsp.ImplementationParams):
    """Jump to an object's implementation."""
    doc = ls.workspace.get_text_document(params.text_document.uri)
    index = ls.index_.get(doc.uri)
    if index is None:
        return

    word = doc.word_at_position(params.position)

    # Is word a function?
    if (range_ := index["function"].get(word, None)) is not None:
        return lsp.Location(uri=doc.uri, range=range_)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_REFERENCES)
def find_references(ls: AMPLServer, params: lsp.ReferenceParams):
    """Find references of an object."""
    doc = ls.workspace.get_text_document(params.text_document.uri)
    index = ls.index_.get(doc.uri)
    if index is None:
        return

    word = doc.word_at_position(params.position)
    is_object = any([word in index[name] for name in index])
    if not is_object:
        return

    references = []
    for linum, line in enumerate(doc.lines):
        for match in re.finditer(f"\\b{word}\\b", line):
            references.append(
                lsp.Location(
                    uri=doc.uri,
                    range=lsp.Range(
                        start=lsp.Position(line=linum, character=match.start()),
                        end=lsp.Position(line=linum, character=match.end()),
                    ),
                )
            )

    return references


# *****************************************************
# Start the LSP_SERVER.
# *****************************************************
if __name__ == "__main__":
    LSP_SERVER.start_io()
