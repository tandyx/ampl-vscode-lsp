import * as os from "os";
import * as fs from "fs";
import * as path from "path";
import * as vscode from "vscode";

/**
 * class to represent an AMPL terminal TerminalOptions
 * @class
 * TODO: implement vscode.terminal interface
 */
export class AMPLTerminal {
  /**
   * name of the terminal
   */
  public name: string;

  /**
   * path to the AMPL executable -- either from the configuration or from the PATH environment variable
   */
  public amplPath: string =
    vscode.workspace.getConfiguration("ampl").get<string>("pathToExecutable") ||
    findPathFile("ampl.exe") ||
    findPathFile("ampl");

  /**
   * arguments to pass to the AMPL executable - comes from user settings
   */
  public executableArgs: string[] = this.amplPath
    ? vscode.workspace.getConfiguration("ampl").get<string[]>("exeArgs") || []
    : [];

  /**
   * terminal options for the AMPL terminal, constructed from the amplPath and executableArgs
   */
  public terminalOptions: vscode.TerminalOptions;

  /**
   * constructor for the AMPLTerminal
   * @param {string} name - the name of the terminal
   */
  constructor(name?: string) {
    this.name = name || "AMPL";
    this.terminalOptions = {
      name: this.name,
      shellPath: this.amplPath || vscode.env.shell,
      shellArgs: this.executableArgs,
    };
  }
}

/**
 * function to run the ampl file
 * @returns {void}
 */
export function runFile(): void {
  const terminal = getAmplConsole();
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const document = editor.document;
  document.save();
  const name: string = vscode.workspace
    .getConfiguration("ampl")
    .get<boolean>("useRelativePath")
    ? vscode.workspace.asRelativePath(document.fileName)
    : document.fileName;
  switch (path.extname(document.fileName)) {
    case ".dat":
      return terminal.sendText(`data "${name}";`);
    case ".mod":
      return terminal.sendText(`model "${name}";`);
    case ".run":
      return terminal.sendText(`include "${name}";`);
  }
}

/**
 * this function checks if the ampl console is open and returns it, if not it opens it then returns it
 * @returns {vscode.Terminal} - the ampl console
 */
export function getAmplConsole(): vscode.Terminal {
  const terminal = vscode.window.activeTerminal;
  if (!terminal || terminal.name !== "AMPL") {
    return openAMPLConsole();
  }
  return terminal;
}

/**
 * opens the ampl console
 * @returns {void}
 */
export function openAMPLConsole(): vscode.Terminal {
  const amplTerminal = new AMPLTerminal();
  const g_terminal = vscode.window.createTerminal(
    amplTerminal.name,
    amplTerminal.terminalOptions.shellPath,
    amplTerminal.terminalOptions.shellArgs
  );
  g_terminal.show(false);
  return g_terminal;
}

/**
 * looks for a file in the PATH environment variable
 * returns the full path.
 * @param {string} exeName - the name of the executable to find
 * @returns {string} the path to the executable
 */
export function findPathFile(exeName: string): string {
  const pathEnv = process.env.PATH || "";
  for (const _path of pathEnv.split(os.platform() === "win32" ? ";" : ":")) {
    const fullPath = path.join(_path, exeName);
    if (fs.existsSync(fullPath)) {
      return fullPath;
    }
  }
  return "";
}
