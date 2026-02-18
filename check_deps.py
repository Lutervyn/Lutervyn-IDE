import sys
import os

# Add Aider path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AIDER_PATH = os.path.join(BASE_DIR, "Ai integration")
sys.path.append(AIDER_PATH)

missing = []
tried = set()

def try_import(name):
    if name in tried: return
    tried.add(name)
    try:
        __import__(name)
        print(f"OK: {name}")
    except ImportError as e:
        print(f"MISSING: {name} ({e})")
        missing.append(name)
    except Exception as e:
        print(f"ERROR: {name} ({e})")

# Core aider imports from main.py
try_import('git')
try_import('importlib_resources')
try_import('shtab')
try_import('dotenv')
try_import('prompt_toolkit')
try_import('litellm')
try_import('rich')
try_import('pydantic')
try_import('tiktoken')
try_import('tokenizers')
try_import('backoff')
try_import('diskcache')
try_import('grep_ast')
try_import('packaging')
try_import('requests')
try_import('yaml')
try_import('diff_match_patch')
try_import('watchdog')
try_import('httpx')
try_import('json5')
try_import('oslex')
try_import('scipy')
try_import('pandas')
try_import('numpy')
try_import('networkx')
try_import('pyperclip')
try_import('sounddevice')
try_import('soundfile')
try_import('configargparse')

print("\nSUMMARY OF MISSING:")
for m in missing:
    print(m)
