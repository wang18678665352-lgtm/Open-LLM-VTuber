"""Local Fish-Speech TTS engine.

Talks to a self-hosted fish-speech API server (``fish-speech/tools/api_server.py``)
over plain HTTP on localhost. Compared with ``fish_api_tts`` (the cloud
api.fish.audio client), this engine is tuned for the lowest possible
time-to-first-audio on a single local GPU:

* one reused ``requests.Session`` so every sentence reuses a keep-alive
  connection instead of a fresh TCP handshake;
* the reference audio is read and base64-encoded exactly once, at init;
* ``use_memory_cache="on"`` lets the server cache the encoded reference
  tokens (VQGAN encode is skipped from the second request on);
* an optional one-shot warmup primes the reference cache so the first
  spoken sentence does not pay the encoding cost.
"""

import base64
import os
import struct
import time
from typing import Optional

import requests
from loguru import logger

from .tts_interface import TTSInterface

# Module level guard: the reference cache / model warmup only needs to happen
# once per process, not once per WebSocket connection (every connection builds
# its own TTSEngine instance).
_WARMED_UP = False


def _read_text_maybe_path(value: str) -> str:
    """Return ``value`` as text.

    If ``value`` points at an existing file, read it (guessing utf-8/gbk);
    otherwise treat it as the literal reference text.
    """
    if not value:
        return ""
    if os.path.isfile(value):
        for encoding in ("utf-8", "utf-8-sig", "gbk", "gb18030"):
            try:
                with open(value, "r", encoding=encoding) as f:
                    return f.read().strip()
            except UnicodeDecodeError:
                continue
        logger.warning(f"Could not decode reference text file: {value}")
    return value.strip()


class TTSEngine(TTSInterface):
    """Fish-Speech TTS served by a local ``tools/api_server.py``."""

    file_extension: str = "wav"

    def __init__(
        self,
        api_url: str = "http://127.0.0.1:8080/v1/tts",
        api_key: Optional[str] = None,
        reference_id: Optional[str] = None,
        reference_audio: Optional[str] = None,
        reference_text: Optional[str] = None,
        use_memory_cache: bool = True,
        chunk_length: int = 200,
        max_new_tokens: int = 1024,
        top_p: float = 0.8,
        repetition_penalty: float = 1.1,
        temperature: float = 0.8,
        normalize: bool = True,
        seed: Optional[int] = None,
        timeout: float = 120.0,
        warmup: bool = True,
        streaming: bool = False,
        **kwargs,
    ):
        self.api_url = api_url
        self.timeout = timeout
        self.warmup_enabled = warmup
        self.streaming = streaming
        # Streaming endpoint lives next to /v1/tts on the same server
        self.stream_url = api_url.rsplit("/", 1)[0] + "/tts_stream"

        self.session = requests.Session()

        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

        # Fixed generation parameters, sent with every request.
        self.params = {
            "format": "wav",
            "streaming": False,
            "chunk_length": chunk_length,
            "max_new_tokens": max_new_tokens,
            "top_p": top_p,
            "repetition_penalty": repetition_penalty,
            "temperature": temperature,
            "normalize": normalize,
            "use_memory_cache": "on" if use_memory_cache else "off",
        }
        if seed is not None:
            self.params["seed"] = seed

        # --- reference voice -------------------------------------------------
        self.reference_id = reference_id or None
        self.reference_payload = None

        if self.reference_id:
            # Server side reference (references/<id>/ under the fish-speech
            # repo): by far the smallest request body.
            logger.info(
                f"Fish-Speech TTS using server side reference_id='{self.reference_id}'"
            )
        elif reference_audio:
            if not os.path.isfile(reference_audio):
                logger.error(f"Reference audio not found: {reference_audio}")
            else:
                text = _read_text_maybe_path(reference_text or "")
                if not text:
                    logger.warning(
                        "No reference text given; voice cloning quality will suffer. "
                        "Set reference_text to the exact transcript of reference_audio."
                    )
                with open(reference_audio, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode("utf-8")
                self.reference_payload = [{"audio": audio_b64, "text": text}]
                logger.info(
                    f"Fish-Speech TTS using inline reference '{reference_audio}' "
                    f"({len(audio_b64) // 1024} KiB base64, cached by server via use_memory_cache)"
                )
        else:
            logger.warning(
                "Neither reference_id nor reference_audio configured; "
                "Fish-Speech will speak with its default voice."
            )

        logger.info(
            f"Fish-Speech TTS initialized: {self.api_url} "
            f"(chunk_length={chunk_length}, max_new_tokens={max_new_tokens}, "
            f"memory_cache={use_memory_cache})"
        )

        if self.warmup_enabled:
            self._warmup_once()

    # ------------------------------------------------------------------ helpers
    def _build_payload(self, text: str) -> dict:
        payload = {"text": text, **self.params}
        if self.reference_id:
            payload["reference_id"] = self.reference_id
        elif self.reference_payload:
            payload["references"] = self.reference_payload
        return payload

    def _check_reference_id_exists(self) -> None:
        """Warn early when the configured reference_id is not on the server.

        Without this check a typo'd id fails silently: the server would create
        an empty reference folder and speak with its default voice instead.
        """
        if not self.reference_id:
            return
        list_url = self.api_url.rsplit("/", 1)[0] + "/references/list"
        try:
            response = self.session.get(
                list_url,
                headers={"Accept": "application/json"},
                timeout=min(self.timeout, 15.0),
            )
            response.raise_for_status()
            ids = response.json().get("reference_ids", [])
        except Exception as e:
            logger.debug(f"Could not list fish-speech references: {e}")
            return

        if self.reference_id not in ids:
            logger.error(
                f"Reference voice '{self.reference_id}' does not exist on the server. "
                f"Available: {ids}. It must be a folder under fish-speech/references/ "
                f"containing sample.wav + sample.lab (see /v1/references/add). "
                f"Falling back to the server default voice."
            )
        else:
            logger.info(f"Fish-Speech reference voice '{self.reference_id}' found on server.")

    def _warmup_once(self) -> None:
        """Prime the model + reference cache once per process.

        Also acts as an early health check: if the fish-speech server is not
        reachable you get a clear error at startup instead of silence later.
        """
        global _WARMED_UP
        if _WARMED_UP:
            return
        _WARMED_UP = True
        self._check_reference_id_exists()
        try:
            started = time.perf_counter()
            response = self.session.post(
                self.api_url,
                json=self._build_payload("嗯。"),
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.info(
                f"Fish-Speech warmup done in {time.perf_counter() - started:.2f}s "
                f"({len(response.content)} bytes). Reference cache is now primed."
            )
        except Exception as e:
            logger.error(
                f"Fish-Speech warmup failed ({type(e).__name__}: {e}). "
                f"Is the local fish-speech API server running at {self.api_url}?"
            )

    # ------------------------------------------------------------------ public
    def generate_audio_stream(self, text: str, file_name_no_ext=None):
        """Yield cache file paths of wav chunks as the server streams them.

        The server sends framed chunks ([4-byte BE length][wav bytes]) as each
        internal segment finishes, so the first chunk is ready well before the
        whole sentence is synthesized. Falls back to plain generate_audio when
        streaming is disabled or the stream endpoint fails.
        """
        if not self.streaming:
            path = self.generate_audio(text, file_name_no_ext)
            if path:
                yield path
            return

        started = time.perf_counter()
        try:
            response = self.session.post(
                self.stream_url,
                json=self._build_payload(text),
                headers=self.headers,
                stream=True,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(
                f"Fish-Speech stream endpoint failed ({type(e).__name__}: {e}); "
                f"falling back to non-streaming generate_audio"
            )
            path = self.generate_audio(text, file_name_no_ext)
            if path:
                yield path
            return

        raw = response.raw
        raw.decode_content = True
        idx = 0
        first_chunk_at = None
        try:
            while True:
                header = self._read_exact(raw, 4)
                if len(header) < 4:
                    break
                (size,) = struct.unpack(">I", header)
                data = self._read_exact(raw, size)
                if len(data) < size:
                    logger.error("Fish-Speech stream truncated mid-chunk")
                    break
                if first_chunk_at is None:
                    first_chunk_at = time.perf_counter() - started
                file_name = self.generate_cache_file_name(
                    f"{file_name_no_ext}_part{idx}" if file_name_no_ext else None,
                    self.file_extension,
                )
                with open(file_name, "wb") as f:
                    f.write(data)
                idx += 1
                yield file_name
        finally:
            response.close()

        elapsed = time.perf_counter() - started
        logger.info(
            f"🔊 Fish-Speech stream: {idx} chunks in {elapsed:.2f}s "
            f"(first chunk {first_chunk_at and round(first_chunk_at, 2)}s) for '{text[:24]}'"
        )
        if idx == 0:
            logger.error("Fish-Speech stream returned no audio chunks")
            return

    @staticmethod
    def _read_exact(raw, n: int) -> bytes:
        data = b""
        while len(data) < n:
            piece = raw.read(n - len(data))
            if not piece:
                break
            data += piece
        return data

    def generate_audio(self, text: str, file_name_no_ext=None) -> str:
        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)

        started = time.perf_counter()
        try:
            response = self.session.post(
                self.api_url,
                json=self._build_payload(text),
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            audio = response.content
        except Exception as e:
            logger.critical(f"Fish-Speech TTS failed to generate audio: {e}")
            return None

        if not audio:
            logger.critical("Fish-Speech TTS returned an empty audio stream.")
            return None

        try:
            with open(file_name, "wb") as f:
                f.write(audio)
        except OSError as e:
            logger.critical(f"Failed to write TTS cache file {file_name}: {e}")
            return None

        elapsed = time.perf_counter() - started
        # 44.1kHz-ish 16bit mono wav -> rough duration from the payload size.
        duration = max(len(audio) - 44, 0) / (44100 * 2)
        logger.info(
            f"🔊 Fish-Speech: {duration:.2f}s audio in {elapsed:.2f}s "
            f"(RTF={elapsed / duration:.2f}) for '{text[:24]}'"
        )
        return file_name
