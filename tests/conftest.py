import sys
import types
from pathlib import Path

# Ensure repository root is on sys.path so `import src.main` works
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))


# Provide lightweight mock replacements for `telegram` and `telegram.ext`
# so tests can import `src.main` without installing the real package in this env.

telegram = types.ModuleType("telegram")

class Update:
    ALL_TYPES = None

telegram.Update = Update
sys.modules['telegram'] = telegram

ext = types.ModuleType("telegram.ext")

class Application:
    @classmethod
    def builder(cls):
        class _Builder:
            def token(self, _):
                return self

            def build(self):
                return Application()

        return _Builder()

def CommandHandler(*args, **kwargs):
    return None

def MessageHandler(*args, **kwargs):
    return None

filters = types.SimpleNamespace(TEXT=object(), COMMAND=object())
ContextTypes = types.SimpleNamespace(DEFAULT_TYPE=object())

ext.Application = Application
ext.CommandHandler = CommandHandler
ext.MessageHandler = MessageHandler
ext.filters = filters
ext.ContextTypes = ContextTypes

sys.modules['telegram.ext'] = ext
