"""Browser-side TTS via the Web Speech API.

We can't play audio from the server thread, so instead we emit a tiny
JS snippet via ``streamlit.components.v1.html``. Streamlit re-runs the
script frequently (with autorefresh enabled) so this fires reliably.

The caller is responsible for not re-speaking the same message — pass a
unique ``key`` (e.g. the rep number) so the component's HTML changes only
when there's something new to say.
"""
from __future__ import annotations

import html

import streamlit.components.v1 as components


def speak(message: str, *, key: str | int, rate: float = 1.05, volume: float = 1.0) -> None:
    """Queue a TTS utterance in the user's browser.

    Args:
        message: text to speak.
        key: unique identifier — change it to trigger a new utterance.
        rate: speech rate (1.0 = normal).
        volume: 0.0 to 1.0.
    """
    safe = html.escape(message).replace("\n", " ")
    # Each components.html call mounts a fresh iframe, so an iframe-scoped
    # guard (window._gymguruLastKey) never dedupes across Streamlit reruns.
    # Use the *parent* page's sessionStorage instead so the same utterance
    # key won't be re-spoken on autorefresh ticks.
    components.html(
        f"""
        <script>
            try {{
                const k = "gymguru-voice-{key}";
                const store = (window.parent && window.parent.sessionStorage)
                              || window.sessionStorage;
                const last = store.getItem("gymguru-voice-last");
                if (last !== k) {{
                    store.setItem("gymguru-voice-last", k);
                    const synth = (window.parent && window.parent.speechSynthesis)
                                  || window.speechSynthesis;
                    const u = new SpeechSynthesisUtterance({safe!r});
                    u.rate = {rate};
                    u.volume = {volume};
                    synth.cancel();
                    synth.speak(u);
                }}
            }} catch (e) {{ /* ignore */ }}
        </script>
        """,
        height=0,
    )
