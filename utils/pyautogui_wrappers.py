import time
import functools
import pyautogui

from utils.config import load_settings

_settings = load_settings()
DEFAULT_RETRIES = int(_settings.get("pyautogui_retries", 3))
DEFAULT_DELAY = 0.12


def retry_action(retries: int = DEFAULT_RETRIES, delay: float = DEFAULT_DELAY, backoff: float = 2.0):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            d = delay
            last_exc = None
            for attempt in range(1, retries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if attempt == retries:
                        raise
                    time.sleep(d)
                    d *= backoff
            raise last_exc
        return wrapper
    return deco


@retry_action()
def safe_click(x=None, y=None, button: str = "left", clicks: int = 1):
    if x is not None and y is not None:
        pyautogui.click(x, y, button=button, clicks=clicks)
        return f"Clicked ({x},{y})"
    pyautogui.click(button=button, clicks=clicks)
    return "Clicked"


@retry_action()
def safe_type(text: str, interval: float = 0.03):
    pyautogui.typewrite(text, interval=interval)
    return f"Typed: {text[:60]}"
