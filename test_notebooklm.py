import subprocess
import json

try:
    print("Running notebooklm...")
    result = subprocess.run(
        ["uv", "run", "notebooklm", "generate", "cinematic-video", "test prompt", "--language", "zh_Hans", "--wait", "--json"],
        capture_output=True,
        text=True
    )
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    try:
        data = json.loads(result.stdout)
        print("Parsed JSON:", json.dumps(data, indent=2))
    except Exception as e:
        print("Failed to parse JSON:", e)
except Exception as e:
    print("Error:", e)
