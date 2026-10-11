import json
import subprocess
from pathlib import Path


def _inside_workspace(workspace, relative_path):
    root = Path(workspace).resolve()
    target = (root / relative_path).resolve()
    if target != root and root not in target.parents:
        raise ValueError("Path must stay inside the workspace.")
    return target


def definitions(enabled):
    schemas = {
        "read_file": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False},
        "write_file": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False},
        "run_command": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"], "additionalProperties": False},
    }
    descriptions = {
        "read_file": "Read a UTF-8 text file inside the workspace. Paths are relative to the workspace.",
        "write_file": "Write a UTF-8 text file inside the workspace. The user will be asked to approve first.",
        "run_command": "Run a command in the workspace. The user will be asked to approve first.",
    }
    return [{"type": "function", "function": {"name": name, "description": descriptions[name], "parameters": schemas[name]}} for name in enabled]


def execute(name, arguments, workspace, confirm):
    args = json.loads(arguments) if isinstance(arguments, str) else arguments
    if name == "read_file":
        return _inside_workspace(workspace, args["path"]).read_text(encoding="utf-8")[:20000]
    if name == "write_file":
        path = _inside_workspace(workspace, args["path"])
        if not confirm(f"Write {args['path']} ({len(args['content'])} characters)?"):
            return "User declined the write."
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"], encoding="utf-8")
        return f"Wrote {args['path']}."
    if name == "run_command":
        command = args["command"]
        if not confirm(f"Run command in {Path(workspace).resolve()}:\n{command}"):
            return "User declined the command."
        result = subprocess.run(command, cwd=workspace, shell=True, text=True, capture_output=True, timeout=30)
        return f"exit code: {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"[:20000]
    raise ValueError(f"Unknown tool: {name}")
