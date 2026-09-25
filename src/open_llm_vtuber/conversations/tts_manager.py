import asyncio
import json
import re
import uuid
from datetime import datetime
from typing import List, Optional, Dict
from loguru import logger

from ..agent.output_types import DisplayText, Actions
from ..live2d_model import Live2dModel
from ..tts.tts_interface import TTSInterface
from ..utils.stream_audio import prepare_audio_payload
from .types import WebSocketSend


class TTSTaskManager:
    """Manages TTS tasks and ensures ordered delivery to frontend while allowing parallel TTS generation"""

    def __init__(self) -> None:
        self.task_list: List[asyncio.Task] = []
        self._lock = asyncio.Lock()
        # Queue to store ordered payloads
        self._payload_queue: asyncio.Queue[Dict] = asyncio.Queue()
        # Task to handle sending payloads in order
        self._sender_task: Optional[asyncio.Task] = None
        # Counter for maintaining order
        self._sequence_counter = 0
        self._next_sequence_to_send = 0
        # Chunk counter within one sequence: a single text may produce several
        # audio payloads when the TTS engine streams (chunk keys are
        # (sequence, chunk_index); (sequence, "end") marks the last chunk)
        self._next_chunk_to_send = 0

    async def speak(
        self,
        tts_text: str,
        display_text: DisplayText,
        actions: Optional[Actions],
        live2d_model: Live2dModel,
        tts_engine: TTSInterface,
        websocket_send: WebSocketSend,
    ) -> None:
        """
        Queue a TTS task while maintaining order of delivery.

        Args:
            tts_text: Text to synthesize
            display_text: Text to display in UI
            actions: Live2D model actions
            live2d_model: Live2D model instance
            tts_engine: TTS engine instance
            websocket_send: WebSocket send function
        """
        if len(re.sub(r'[\s.,!?，。！？\'"』」）】\s]+', "", tts_text)) == 0:
            logger.debug("Empty TTS text, sending silent display payload")
            # Get current sequence number for silent payload
            current_sequence = self._sequence_counter
            self._sequence_counter += 1

            # Start sender task if not running
            if not self._sender_task or self._sender_task.done():
                self._sender_task = asyncio.create_task(
                    self._process_payload_queue(websocket_send)
                )

            await self._send_silent_payload(display_text, actions, current_sequence)
            return

        logger.debug(
            f"🏃Queuing TTS task for: '''{tts_text}''' (by {display_text.name})"
        )

        # Get current sequence number
        current_sequence = self._sequence_counter
        self._sequence_counter += 1

        # Start sender task if not running
        if not self._sender_task or self._sender_task.done():
            self._sender_task = asyncio.create_task(
                self._process_payload_queue(websocket_send)
            )

        # Create and queue the TTS task
        task = asyncio.create_task(
            self._process_tts(
                tts_text=tts_text,
                display_text=display_text,
                actions=actions,
                live2d_model=live2d_model,
                tts_engine=tts_engine,
                sequence_number=current_sequence,
            )
        )
        self.task_list.append(task)

    async def _process_payload_queue(self, websocket_send: WebSocketSend) -> None:
        """
        Process and send payloads in correct order.
        Runs continuously until all payloads are processed.

        Payloads are keyed by (sequence, chunk_index). A sequence is complete
        once its (sequence, "end") marker arrives; only then does the sender
        advance to the next sequence.
        """
        buffered_payloads: Dict = {}

        while True:
            try:
                # Get payload from queue
                payload, key = await self._payload_queue.get()
                buffered_payloads[key] = payload

                # Send payloads in order
                while True:
                    chunk_key = (self._next_sequence_to_send, self._next_chunk_to_send)
                    end_key = (self._next_sequence_to_send, "end")
                    if chunk_key in buffered_payloads:
                        next_payload = buffered_payloads.pop(chunk_key)
                        await websocket_send(json.dumps(next_payload))
                        self._next_chunk_to_send += 1
                    elif end_key in buffered_payloads:
                        buffered_payloads.pop(end_key)
                        self._next_sequence_to_send += 1
                        self._next_chunk_to_send = 0
                    else:
                        break

                self._payload_queue.task_done()

            except asyncio.CancelledError:
                break

    async def _send_silent_payload(
        self,
        display_text: DisplayText,
        actions: Optional[Actions],
        sequence_number: int,
    ) -> None:
        """Queue a silent audio payload"""
        audio_payload = prepare_audio_payload(
            audio_path=None,
            display_text=display_text,
            actions=actions,
        )
        await self._payload_queue.put((audio_payload, (sequence_number, 0)))
        await self._payload_queue.put((None, (sequence_number, "end")))

    async def _generate_audio_stream(self, tts_engine: TTSInterface, text: str):
        """Iterate the engine's blocking chunk generator without blocking the loop"""
        iterator = tts_engine.generate_audio_stream(
            text=text,
            file_name_no_ext=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}",
        )

        def _next_chunk():
            try:
                return next(iterator)
            except StopIteration:
                return None

        while True:
            chunk_path = await asyncio.to_thread(_next_chunk)
            if chunk_path is None:
                break
            yield chunk_path

    async def _process_tts(
        self,
        tts_text: str,
        display_text: DisplayText,
        actions: Optional[Actions],
        live2d_model: Live2dModel,
        tts_engine: TTSInterface,
        sequence_number: int,
    ) -> None:
        """Process TTS generation and queue the result for ordered delivery"""
        audio_file_path = None
        chunk_index = 0
        try:
            if getattr(tts_engine, "streaming", False) and hasattr(
                tts_engine, "generate_audio_stream"
            ):
                async for chunk_path in self._generate_audio_stream(
                    tts_engine, tts_text
                ):
                    # Only the first chunk carries the subtitle and actions,
                    # later chunks are pure audio to avoid duplicate subtitles
                    payload = prepare_audio_payload(
                        audio_path=chunk_path,
                        display_text=display_text
                        if chunk_index == 0
                        else DisplayText(
                            text="",
                            name=display_text.name,
                            avatar=display_text.avatar,
                        ),
                        actions=actions if chunk_index == 0 else None,
                    )
                    await self._payload_queue.put(
                        (payload, (sequence_number, chunk_index))
                    )
                    tts_engine.remove_file(chunk_path)
                    chunk_index += 1
            else:
                audio_file_path = await self._generate_audio(tts_engine, tts_text)
                payload = prepare_audio_payload(
                    audio_path=audio_file_path,
                    display_text=display_text,
                    actions=actions,
                )
                # Queue the payload with its sequence number
                await self._payload_queue.put((payload, (sequence_number, 0)))

        except Exception as e:
            logger.error(f"Error preparing audio payload: {e}")
            # Queue silent payload for error case
            payload = prepare_audio_payload(
                audio_path=None,
                display_text=display_text,
                actions=actions,
            )
            await self._payload_queue.put((payload, (sequence_number, 0)))

        finally:
            # Mark the sequence complete so the sender can advance
            await self._payload_queue.put((None, (sequence_number, "end")))
            if audio_file_path:
                tts_engine.remove_file(audio_file_path)
                logger.debug("Audio cache file cleaned.")

    async def _generate_audio(self, tts_engine: TTSInterface, text: str) -> str:
        """Generate audio file from text"""
        logger.debug(f"🏃Generating audio for '''{text}'''...")
        return await tts_engine.async_generate_audio(
            text=text,
            file_name_no_ext=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}",
        )

    def clear(self) -> None:
        """Clear all pending tasks and reset state"""
        self.task_list.clear()
        if self._sender_task:
            self._sender_task.cancel()
        self._sequence_counter = 0
        self._next_sequence_to_send = 0
        self._next_chunk_to_send = 0
        # Create a new queue to clear any pending items
        self._payload_queue = asyncio.Queue()
