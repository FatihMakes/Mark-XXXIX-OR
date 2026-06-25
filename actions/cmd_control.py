# actions/cmd_control.py
import subprocess
import sys

def cmd_control(parameters: dict, player=None) -> str:
    """
    Executes a shell command on the Windows system and returns output.
    """
    command = parameters.get("command")
    if not command:
        return "Sir, no command was provided to execute."

    if player:
        try:
            player.write_log(f"[CMD] Running: {command}")
        except Exception:
            pass

    print(f"[CMD] Running command: {command}")

    try:
        # Run command with 60s timeout, capturing output
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60
        )
        output = result.stdout.strip()
        error = result.stderr.strip()

        parts = []
        if output:
            parts.append(output)
        if error:
            parts.append(f"Stderr:\n{error}")

        response = "\n".join(parts) if parts else "Executed successfully with no output."
        
        # Limit size to prevent bloating the token window
        if len(response) > 3000:
            response = response[:3000] + "\n... (output truncated)"
        return response

    except subprocess.TimeoutExpired:
        return "Command execution timed out after 60 seconds."
    except Exception as e:
        return f"Failed to execute command: {e}"
