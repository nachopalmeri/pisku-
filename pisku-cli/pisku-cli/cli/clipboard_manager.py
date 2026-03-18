"""
Clipboard Manager — Cross-platform copy al portapapeles.
Windows: pyperclip usa win32 nativo
macOS:   pyperclip usa pbcopy
Linux:   pyperclip usa xclip/xsel (hay que tener uno instalado)
"""
from pathlib import Path


def copy_to_clipboard(text: str) -> bool:
    """
    Copia texto al clipboard. Devuelve True si tuvo éxito.
    """
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        return False
    except Exception:
        # Linux sin xclip/xsel instalado, CI environments, etc.
        return False


def copy_file_to_clipboard(path: Path) -> bool:
    """
    Lee un archivo y lo copia al clipboard.
    """
    try:
        text = path.read_text(encoding="utf-8")
        return copy_to_clipboard(text)
    except Exception:
        return False
