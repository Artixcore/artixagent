import json
from pathlib import Path

from .agent import AgentError, SYSTEM_PROMPT, complete
from .tools import definitions, execute

HISTORY = Path.home() / ".artixagent" / "history.jsonl"
TOOL_NAMES = ("read_file", "write_file", "run_command")


def confirm(prompt):
    return input(f"{prompt}\nApprove? [y/N] ").strip().lower() in {"y", "yes"}


def main():
    workspace = Path.cwd().resolve()
    enabled = set()
    messages = [{"role": "system", "content": SYSTEM_PROMPT + f"\nWorkspace: {workspace}"}]
    print(f"ArtixAgent 0.1.0 — workspace: {workspace}\nType /help for commands.")
    while True:
        try:
            user_text = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return
        if not user_text:
            continue
        if user_text == "/exit":
            print("Goodbye.")
            return
        if user_text == "/help":
            print("/help  /tools  /reset  /exit")
            continue
        if user_text == "/reset":
            messages = messages[:1]
            print("Conversation cleared.")
            continue
        if user_text == "/tools":
            print("Enabled: " + (", ".join(sorted(enabled)) if enabled else "none"))
            print("Enter a tool name to toggle it, or press Enter to leave settings.")
            choice = input(f"Tool ({'/'.join(TOOL_NAMES)}): ").strip()
            if choice in TOOL_NAMES:
                if choice in enabled:
                    enabled.remove(choice)
                else:
                    enabled.add(choice)
                print(f"{choice}: {'enabled' if choice in enabled else 'disabled'}")
            continue
        messages.append({"role": "user", "content": user_text})
        try:
            for _ in range(8):
                reply = complete(messages, definitions(enabled))
                messages.append(reply)
                calls = reply.get("tool_calls") or []
                if not calls:
                    print(f"\nartixagent> {reply.get('content') or ''}")
                    break
                for call in calls:
                    fn = call["function"]
                    try:
                        result = execute(fn["name"], fn["arguments"], workspace, confirm)
                    except Exception as exc:
                        result = f"Tool error: {exc}"
                    messages.append({"role": "tool", "tool_call_id": call["id"], "content": str(result)})
            else:
                print("Stopped after 8 tool rounds to avoid an unbounded loop.")
            HISTORY.parent.mkdir(parents=True, exist_ok=True)
            with HISTORY.open("a", encoding="utf-8") as log:
                log.write(json.dumps({"user": user_text, "messages": messages[-6:]}, ensure_ascii=False) + "\n")
        except AgentError as exc:
            print(f"\nartixagent> {exc}")


if __name__ == "__main__":
    main()
