"""启动器可编辑的模型配置元数据（对话模型 / 语音合成 / 语音识别）。

字段名与 ``src/open_llm_vtuber/config_manager/`` 下的 pydantic 模型保持一致，
界面只暴露常用项，其余仍可在 conf.yaml 中手动编辑。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Field:
    """一个可编辑的配置项。"""

    key: str
    label: str
    kind: str = "text"  # text | secret | int | float | bool | choice | json | path | multiline
    hint: str = ""
    choices: tuple[str, ...] = ()
    placeholder: str = ""
    default: Any = None
    wide: bool = False


@dataclass(frozen=True)
class Provider:
    """一个可选的引擎（对应 conf.yaml 中的一个子节点）。"""

    key: str
    name: str
    fields: tuple[Field, ...] = ()
    note: str = ""
    url_field: str = ""
    secret_field: str = ""
    path_field: str = ""

    def field(self, key: str) -> Field | None:
        for item in self.fields:
            if item.key == key:
                return item
        return None


@dataclass(frozen=True)
class Section:
    """一组引擎：LLM / TTS / ASR。"""

    key: str
    title: str
    icon: str
    selector_path: str
    base_path: str
    providers: tuple[Provider, ...]
    note: str = ""

    def provider(self, key: str) -> Provider | None:
        for item in self.providers:
            if item.key == key:
                return item
        return None

    def names(self) -> list[str]:
        return [f"{item.name}（{item.key}）" for item in self.providers]

    def key_of_label(self, label: str) -> str:
        for item in self.providers:
            if f"{item.name}（{item.key}）" == label:
                return item.key
        return self.providers[0].key


# ---------------------------------------------------------------------------
# 字段简写
# ---------------------------------------------------------------------------
_API_KEY = Field(
    "llm_api_key",
    "API Key",
    "secret",
    hint="在模型服务商控制台创建，仅保存在本地 conf.yaml 中",
    placeholder="sk-...",
)
_TEMPERATURE = Field(
    "temperature", "温度 Temperature", "float", hint="0 ~ 2，数值越低回答越稳定", default=1.0
)
_BASE_URL = Field(
    "base_url", "接口地址 Base URL", "text", hint="一般以 /v1 结尾", placeholder="https://..."
)
_INTERRUPT = Field(
    "interrupt_method",
    "打断方式",
    "choice",
    choices=("user", "api"),
    hint="user：收到新输入立刻打断；api：等待模型返回中断信号",
)
_ORGANIZATION = Field("organization_id", "组织 ID Organization", "text", hint="可留空")
_PROJECT = Field("project_id", "项目 ID Project", "text", hint="可留空")

_MODEL = Field("model", "模型名称", "text", placeholder="例如 deepseek-chat")

_LLM_COMMON = (_MODEL, _TEMPERATURE)


def _openai_like(
    name: str,
    key: str,
    *,
    note: str = "",
    model_default: str = "",
    with_base_url: bool = False,
) -> Provider:
    model = _MODEL if not model_default else Field(
        "model", "模型名称", "text", default=model_default, placeholder=model_default
    )
    fields: list[Field] = []
    if with_base_url:
        fields.append(_BASE_URL)
    fields.append(_API_KEY)
    fields.append(model)
    fields.append(_TEMPERATURE)
    return Provider(key=key, name=name, fields=tuple(fields), note=note, secret_field="llm_api_key")


# ---------------------------------------------------------------------------
# 对话模型（LLM）
# ---------------------------------------------------------------------------
LLM_PROVIDERS: tuple[Provider, ...] = (
    Provider(
        key="deepseek_llm",
        name="DeepSeek",
        note="官方 https://api.deepseek.com/v1，性价比高，中文表现好",
        secret_field="llm_api_key",
        fields=(
            _API_KEY,
            Field("model", "模型名称", "text", default="deepseek-chat", placeholder="deepseek-chat"),
            _TEMPERATURE,
            Field(
                "extra_body",
                "扩展参数 extra_body",
                "json",
                hint='JSON 对象，例如 {"effort": "low"}；不需要可留空',
            ),
        ),
    ),
    Provider(
        key="openai_llm",
        name="OpenAI",
        note="官方接口 https://api.openai.com/v1",
        secret_field="llm_api_key",
        fields=(
            _API_KEY,
            Field("model", "模型名称", "text", default="gpt-4o-mini", placeholder="gpt-4o-mini"),
            _TEMPERATURE,
        ),
    ),
    Provider(
        key="openai_compatible_llm",
        name="OpenAI 兼容接口",
        note="任何兼容 /chat/completions 的服务（如中转站、vLLM、One-API）",
        secret_field="llm_api_key",
        fields=(_BASE_URL, _API_KEY, _MODEL, _TEMPERATURE, _INTERRUPT, _ORGANIZATION, _PROJECT),
    ),
    Provider(
        key="stateless_llm_with_template",
        name="本地模板模型",
        note="本地推理服务（vLLM / llama.cpp server 等），需自行填写聊天模板",
        secret_field="llm_api_key",
        fields=(
            _BASE_URL,
            _API_KEY,
            _MODEL,
            Field(
                "template",
                "对话模板",
                "choice",
                choices=("CHATML", "CHATML_2", "LLAMA_2", "LLAMA_3", "OPENAI", "HISTORY"),
                default="CHATML",
            ),
            _TEMPERATURE,
            _INTERRUPT,
            _ORGANIZATION,
            _PROJECT,
        ),
    ),
    Provider(
        key="ollama_llm",
        name="Ollama（本地）",
        note="默认地址 http://localhost:11434/v1，需先 ollama serve",
        url_field="base_url",
        fields=(
            Field("base_url", "接口地址", "text", default="http://localhost:11434/v1"),
            Field("model", "模型名称", "text", placeholder="qwen2.5:latest"),
            _TEMPERATURE,
            Field("keep_alive", "保持加载（分钟）", "int", hint="-1 表示常驻内存"),
            Field("unload_at_exit", "退出时卸载模型", "bool", default=True),
        ),
    ),
    Provider(
        key="lmstudio_llm",
        name="LM Studio（本地）",
        note="在 LM Studio 中开启本地服务器，默认 http://localhost:1234/v1",
        url_field="base_url",
        fields=(
            Field("base_url", "接口地址", "text", default="http://localhost:1234/v1"),
            Field("model", "模型名称", "text"),
            _TEMPERATURE,
        ),
    ),
    Provider(
        key="claude_llm",
        name="Claude",
        note="官方接口 https://api.anthropic.com",
        secret_field="llm_api_key",
        fields=(
            _BASE_URL,
            _API_KEY,
            Field("model", "模型名称", "text", placeholder="claude-3-haiku-20240307"),
        ),
    ),
    _openai_like("Gemini", "gemini_llm", model_default="gemini-1.5-flash"),
    _openai_like("智谱 GLM", "zhipu_llm", model_default="glm-4-flash"),
    _openai_like("Mistral", "mistral_llm"),
    _openai_like("Groq", "groq_llm"),
    Provider(
        key="llama_cpp_llm",
        name="llama.cpp（本地 GGUF）",
        note="直接加载本地 GGUF 模型文件，无需额外服务",
        path_field="model_path",
        fields=(
            Field("model_path", "模型文件路径", "path", hint="指向 .gguf 文件"),
            Field("verbose", "输出详细日志", "bool"),
        ),
    ),
)

LLM_SECTION = Section(
    key="llm",
    title="对话模型",
    icon="code",
    selector_path=(
        "character_config.agent_config.agent_settings.basic_memory_agent.llm_provider"
    ),
    base_path="character_config.agent_config.llm_configs",
    providers=LLM_PROVIDERS,
    note="对话模型决定角色的思考与回复质量；保存后需重启服务生效。",
)

# ---------------------------------------------------------------------------
# 语音合成（TTS）
# ---------------------------------------------------------------------------
TTS_PROVIDERS: tuple[Provider, ...] = (
    Provider(
        key="fish_speech_tts",
        name="Fish Speech / IndexTTS（本地）",
        note=(
            "本地推理服务，需先启动 API：\n"
            "cd I:\\practise\\github__clone\\index-tts && .venv\\Scripts\\python.exe api_server_vtuber.py"
        ),
        url_field="api_url",
        fields=(
            Field(
                "api_url",
                "服务地址",
                "text",
                default="http://127.0.0.1:8080/v1/tts",
                hint="本地 IndexTTS2 / Fish Speech 的 TTS 接口",
            ),
            Field("api_key", "API Key", "secret", hint="本地服务一般留空"),
            Field("reference_id", "参考音色 ID", "text", hint="服务端已保存的音色标识"),
            Field("reference_audio", "参考音频路径", "text"),
            Field("reference_text", "参考音频文本", "text"),
            Field("streaming", "流式合成", "bool", default=True),
            Field("chunk_length", "分块长度", "int", default=200),
            Field("max_new_tokens", "单句最大 token", "int", default=1024),
            Field("top_p", "top_p", "float", default=0.8),
            Field("repetition_penalty", "重复惩罚", "float", default=1.1),
            Field("temperature", "温度", "float", default=0.8),
            Field("normalize", "文本正则化", "bool", default=True),
            Field("seed", "随机种子", "int", hint="留空表示随机"),
            Field("timeout", "超时（秒）", "int", default=120),
            Field("warmup", "启动预热", "bool", default=True),
            Field("use_memory_cache", "音色内存缓存", "bool", default=True),
        ),
    ),
    Provider(
        key="edge_tts",
        name="Edge TTS（免费在线）",
        note="微软 Edge 在线语音，无需 Key，需联网",
        fields=(
            Field(
                "voice",
                "音色",
                "choice",
                choices=(
                    "zh-CN-XiaoxiaoNeural",
                    "zh-CN-XiaoyiNeural",
                    "zh-CN-YunxiNeural",
                    "zh-CN-YunyangNeural",
                    "zh-CN-liaoning-XiaobeiNeural",
                    "zh-TW-HsiaoChenNeural",
                    "ja-JP-NanamiNeural",
                    "en-US-AriaNeural",
                ),
                default="zh-CN-XiaoxiaoNeural",
            ),
        ),
    ),
    Provider(
        key="fish_api_tts",
        name="Fish Audio（云端）",
        note="官方云服务 https://api.fish.audio，需要 API Key",
        url_field="base_url",
        secret_field="api_key",
        fields=(
            Field("api_key", "API Key", "secret"),
            Field("reference_id", "参考音色 ID", "text"),
            Field(
                "latency",
                "延迟模式",
                "choice",
                choices=("normal", "balanced", "low"),
                default="balanced",
            ),
            Field("base_url", "接口地址", "text", default="https://api.fish.audio"),
        ),
    ),
    Provider(
        key="gpt_sovits_tts",
        name="GPT-SoVITS（本地）",
        note="本地 api_v2 服务，默认 http://127.0.0.1:9880",
        url_field="api_url",
        fields=(
            Field("api_url", "接口地址", "text", default="http://127.0.0.1:9880"),
            Field("text_lang", "文本语言", "choice", choices=("zh", "en", "ja", "auto"), default="zh"),
            Field("ref_audio_path", "参考音频路径", "text"),
            Field("prompt_lang", "参考音频语言", "choice", choices=("zh", "en", "ja"), default="zh"),
            Field("prompt_text", "参考音频文本", "text"),
            Field("text_split_method", "分句方式", "text", default="cut5"),
            Field("batch_size", "批大小", "int", default=1),
            Field("media_type", "音频格式", "choice", choices=("wav", "ogg", "aac", "raw"), default="wav"),
            Field("streaming_mode", "流式模式", "int", default=0),
        ),
    ),
    Provider(
        key="cosyvoice_tts",
        name="CosyVoice（本地）",
        note="本地 Gradio 服务，默认 http://127.0.0.1:50000/",
        url_field="client_url",
        fields=(
            Field("client_url", "服务地址", "text", default="http://127.0.0.1:50000/"),
            Field("api_name", "接口名", "text", default="/generate_audio"),
            Field("mode_checkbox_group", "推理模式", "text", default="预训练音色"),
            Field("sft_dropdown", "音色", "text"),
            Field("prompt_text", "提示文本", "text"),
            Field("prompt_wav_upload_url", "上传音频路径", "text"),
            Field("prompt_wav_record_url", "录制音频路径", "text"),
            Field("instruct_text", "指令文本", "text"),
            Field("seed", "随机种子", "int"),
        ),
    ),
    Provider(
        key="cosyvoice2_tts",
        name="CosyVoice 2（本地）",
        note="CosyVoice2 本地服务，支持流式输出",
        url_field="client_url",
        fields=(
            Field("client_url", "服务地址", "text", default="http://127.0.0.1:50000/"),
            Field("api_name", "接口名", "text", default="/generate_audio"),
            Field("mode_checkbox_group", "推理模式", "text", default="预训练音色"),
            Field("sft_dropdown", "音色", "text"),
            Field("prompt_text", "提示文本", "text"),
            Field("prompt_wav_upload_url", "上传音频路径", "text"),
            Field("prompt_wav_record_url", "录制音频路径", "text"),
            Field("instruct_text", "指令文本", "text"),
            Field("seed", "随机种子", "int"),
            Field("stream", "流式输出", "bool"),
            Field("speed", "语速", "float", default=1.0),
        ),
    ),
    Provider(
        key="spark_tts",
        name="Spark TTS（本地）",
        note="本地服务，默认 http://127.0.0.1:6006/",
        url_field="api_url",
        fields=(
            Field("api_url", "服务地址", "text", default="http://127.0.0.1:6006/"),
            Field("api_name", "接口名", "text", default="voice_clone"),
            Field("prompt_wav_upload", "参考音频路径", "text"),
            Field("gender", "音色性别", "choice", choices=("female", "male"), default="female"),
            Field("pitch", "音调", "int", default=3),
            Field("speed", "语速", "int", default=3),
        ),
    ),
    Provider(
        key="x_tts",
        name="XTTS v2（本地）",
        note="基于参考音频克隆音色，首次运行会下载模型",
        url_field="api_url",
        fields=(
            Field("api_url", "服务地址", "text", default="http://127.0.0.1:8020/tts_to_audio"),
            Field("speaker_wav", "参考音频路径", "path"),
            Field("language", "语言", "choice", choices=("zh-cn", "en", "ja", "auto"), default="zh-cn"),
        ),
    ),
    Provider(
        key="melo_tts",
        name="MeloTTS（本地）",
        note="轻量本地合成，无需额外服务",
        fields=(
            Field("speaker", "音色", "text", default="ZH"),
            Field("language", "语言", "choice", choices=("ZH", "EN", "JP", "ES", "FR", "KR"), default="ZH"),
            Field("device", "设备", "choice", choices=("auto", "cpu", "cuda", "mps"), default="auto"),
            Field("speed", "语速", "float", default=1.0),
        ),
    ),
    Provider(
        key="piper_tts",
        name="Piper（本地）",
        note="需下载 onnx 语音模型文件",
        path_field="model_path",
        fields=(
            Field("model_path", "模型文件", "path", hint=".onnx 文件"),
            Field("speaker_id", "说话人 ID", "int"),
            Field("length_scale", "语速（length_scale）", "float", default=1.0),
            Field("noise_scale", "噪声强度", "float", default=0.667),
            Field("noise_w", "噪声宽度", "float", default=0.8),
            Field("volume", "音量", "float", default=1.0),
            Field("normalize_audio", "音量归一化", "bool", default=True),
            Field("use_cuda", "使用 CUDA", "bool"),
        ),
    ),
    Provider(
        key="coqui_tts",
        name="Coqui TTS（本地）",
        note="首次使用会从网上下载模型",
        fields=(
            Field("model_name", "模型名称", "text", default="tts_models/multilingual/multi-dataset/xtts_v2"),
            Field("speaker_wav", "参考音频路径", "path"),
            Field("language", "语言", "text", default="zh-cn"),
            Field("device", "设备", "text", default="cuda"),
        ),
    ),
    Provider(
        key="sherpa_onnx_tts",
        name="sherpa-onnx（本地离线）",
        note="完全离线的本地合成，需要下载 onnx 模型",
        path_field="vits_model",
        fields=(
            Field("vits_model", "VITS 模型", "path"),
            Field("vits_lexicon", "词典文件", "path"),
            Field("vits_tokens", "tokens 文件", "path"),
            Field("vits_data_dir", "数据目录", "path"),
            Field("vits_dict_dir", "字典目录", "path"),
            Field("tts_rule_fsts", "规则 FST", "text"),
            Field("max_num_sentences", "单批最大句数", "int", default=1),
            Field("sid", "说话人 ID", "int"),
            Field("provider", "推理后端", "choice", choices=("cpu", "cuda", "coreml"), default="cpu"),
            Field("num_threads", "线程数", "int", default=1),
            Field("speed", "语速", "float", default=1.0),
            Field("debug", "调试日志", "bool"),
        ),
    ),
    Provider(
        key="openai_tts",
        name="OpenAI 兼容 TTS",
        note="任何兼容 /audio/speech 的服务，如 Kokoro-FastAPI",
        url_field="base_url",
        secret_field="api_key",
        fields=(
            Field("model", "模型名称", "text", default="kokoro"),
            Field("voice", "音色", "text"),
            Field("api_key", "API Key", "secret"),
            Field("base_url", "接口地址", "text", default="http://localhost:8880/v1"),
            Field("file_extension", "音频格式", "choice", choices=("mp3", "wav", "opus", "aac", "flac"), default="mp3"),
        ),
    ),
    Provider(
        key="siliconflow_tts",
        name="SiliconFlow（云端）",
        note="硅基流动语音合成，需要 API Key",
        url_field="api_url",
        secret_field="api_key",
        fields=(
            Field("api_url", "接口地址", "text", default="https://api.siliconflow.cn/v1/audio/speech"),
            Field("api_key", "API Key", "secret"),
            Field("default_model", "模型", "text", default="FunAudioLLM/CosyVoice2-0.5B"),
            Field("default_voice", "音色", "text", default="FunAudioLLM/CosyVoice2-0.5B:alex"),
            Field("sample_rate", "采样率", "int", default=32000),
            Field("response_format", "音频格式", "choice", choices=("mp3", "wav", "opus", "pcm"), default="mp3"),
            Field("stream", "流式输出", "bool", default=True),
            Field("speed", "语速", "float", default=1.0),
            Field("gain", "增益", "float", default=0.0),
        ),
    ),
    Provider(
        key="minimax_tts",
        name="MiniMax（云端）",
        note="需要 Group ID 与 API Key",
        secret_field="api_key",
        fields=(
            Field("group_id", "Group ID", "text"),
            Field("api_key", "API Key", "secret"),
            Field("model", "模型", "text", default="speech-02-turbo"),
            Field("voice_id", "音色 ID", "text", default="female-shaonv"),
            Field("pronunciation_dict", "发音词典", "json", hint="JSON 对象，可留空"),
        ),
    ),
    Provider(
        key="elevenlabs_tts",
        name="ElevenLabs（云端）",
        note="音质出色，需要 API Key 与 Voice ID",
        secret_field="api_key",
        fields=(
            Field("api_key", "API Key", "secret"),
            Field("voice_id", "音色 ID", "text"),
            Field("model_id", "模型", "text", default="eleven_multilingual_v2"),
            Field("output_format", "输出格式", "text", default="pcm_16000"),
            Field("stability", "稳定度", "float", default=0.5),
            Field("similarity_boost", "相似度增强", "float", default=0.5),
            Field("style", "风格强度", "float", default=0.0),
            Field("use_speaker_boost", "说话人增强", "bool", default=True),
        ),
    ),
    Provider(
        key="cartesia_tts",
        name="Cartesia（云端）",
        note="低延迟云合成，需要 API Key 与 Voice ID",
        secret_field="api_key",
        fields=(
            Field("api_key", "API Key", "secret"),
            Field("voice_id", "音色 ID", "text"),
            Field("model_id", "模型", "text", default="sonic-2"),
            Field("output_format", "输出格式", "json", hint='例如 {"container":"raw","sample_rate":44100}'),
            Field("language", "语言", "text", default="zh"),
            Field("emotion", "情绪", "text"),
            Field("volume", "音量", "float", default=1.0),
            Field("speed", "语速", "float", default=1.0),
        ),
    ),
    Provider(
        key="azure_tts",
        name="Azure TTS（云端）",
        note="微软 Azure 语音服务，需要 Key 与区域",
        secret_field="api_key",
        fields=(
            Field("api_key", "API Key", "secret"),
            Field("region", "区域", "text", placeholder="eastasia"),
            Field("voice", "音色", "text", default="zh-CN-XiaoxiaoNeural"),
            Field("pitch", "音调", "text", default="+0Hz"),
            Field("rate", "语速", "text", default="+0%"),
        ),
    ),
    Provider(
        key="bark_tts",
        name="Bark（本地）",
        note="本地模型，合成较慢",
        fields=(Field("voice", "音色", "text", default="v2/zh_speaker_1"),),
    ),
    Provider(
        key="pyttsx3_tts",
        name="系统语音（pyttsx3）",
        note="直接调用 Windows 内置语音，无需任何配置",
        fields=(),
    ),
)

TTS_SECTION = Section(
    key="tts",
    title="语音合成",
    icon="terminal",
    selector_path="character_config.tts_config.tts_model",
    base_path="character_config.tts_config",
    providers=TTS_PROVIDERS,
    note="语音合成决定角色的声音；本地引擎需要先把对应服务跑起来。",
)

# ---------------------------------------------------------------------------
# 语音识别（ASR）
# ---------------------------------------------------------------------------
ASR_PROVIDERS: tuple[Provider, ...] = (
    Provider(
        key="sherpa_onnx_asr",
        name="sherpa-onnx（本地离线）",
        note="默认使用，首次启动会自动下载模型",
        path_field="sense_voice",
        fields=(
            Field(
                "model_type",
                "模型类型",
                "choice",
                choices=("auto", "sense_voice", "paraformer", "transducer", "whisper", "nemo_ctc", "zipformer"),
                default="auto",
            ),
            Field("sense_voice", "SenseVoice 模型目录", "path"),
            Field("tokens", "tokens 文件", "path"),
            Field("num_threads", "线程数", "int", default=1),
            Field("use_itn", "启用标点与逆文本化", "bool", default=True),
            Field("provider", "推理后端", "choice", choices=("cpu", "cuda", "coreml"), default="cpu"),
        ),
    ),
    Provider(
        key="faster_whisper",
        name="faster-whisper（本地）",
        note="本地 Whisper 推理，可用 CUDA 加速",
        path_field="model_path",
        fields=(
            Field("model_path", "模型路径或名称", "text", placeholder="large-v3"),
            Field("download_root", "下载目录", "text"),
            Field("language", "语言", "text", default="auto"),
            Field("device", "设备", "choice", choices=("auto", "cpu", "cuda"), default="auto"),
            Field("compute_type", "计算精度", "choice", choices=("default", "float16", "int8", "int8_float16"), default="default"),
            Field("prompt", "提示词", "text"),
        ),
    ),
    Provider(
        key="whisper_cpp",
        name="whisper.cpp（本地）",
        note="CPU 推理，适合没有显卡的机器",
        fields=(
            Field("model_name", "模型名称", "text", default="ggml-small.bin"),
            Field("model_dir", "模型目录", "path"),
            Field("print_realtime", "实时打印", "bool"),
            Field("print_progress", "打印进度", "bool"),
            Field("language", "语言", "text", default="auto"),
            Field("prompt", "提示词", "text"),
        ),
    ),
    Provider(
        key="whisper",
        name="OpenAI Whisper（本地）",
        note="原版 Whisper，速度较慢",
        fields=(
            Field("name", "模型大小", "choice", choices=("tiny", "base", "small", "medium", "large"), default="small"),
            Field("download_root", "下载目录", "text"),
            Field("device", "设备", "choice", choices=("cpu", "cuda"), default="cpu"),
            Field("prompt", "提示词", "text"),
        ),
    ),
    Provider(
        key="fun_asr",
        name="FunASR（本地）",
        note="阿里达摩院语音识别，中文效果好",
        fields=(
            Field("model_name", "模型名称", "text", default="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"),
            Field("vad_model", "VAD 模型", "text", default="fsmn-vad"),
            Field("punc_model", "标点模型", "text", default="ct-punc"),
            Field("device", "设备", "choice", choices=("cpu", "cuda"), default="cpu"),
            Field("disable_update", "禁止检查更新", "bool", default=True),
            Field("ncpu", "CPU 线程数", "int", default=4),
            Field("hub", "模型源", "choice", choices=("ms", "modelscope", "hf"), default="ms"),
            Field("use_itn", "启用标点与逆文本化", "bool", default=True),
            Field("language", "语言", "text", default="zh"),
        ),
    ),
    Provider(
        key="azure_asr",
        name="Azure 语音识别（云端）",
        note="微软 Azure 语音服务，需要 Key 与区域",
        secret_field="api_key",
        fields=(
            Field("api_key", "API Key", "secret"),
            Field("region", "区域", "text", placeholder="eastasia"),
            Field("languages", "识别语言", "json", hint='例如 ["zh-CN"]'),
        ),
    ),
    Provider(
        key="groq_whisper_asr",
        name="Groq Whisper（云端）",
        note="Groq 提供的超快 Whisper 接口，需要 API Key",
        secret_field="api_key",
        fields=(
            Field("api_key", "API Key", "secret"),
            Field("model", "模型", "text", default="whisper-large-v3-turbo"),
            Field("lang", "语言", "text", default="zh"),
        ),
    ),
)

ASR_SECTION = Section(
    key="asr",
    title="语音识别",
    icon="scan",
    selector_path="character_config.asr_config.asr_model",
    base_path="character_config.asr_config",
    providers=ASR_PROVIDERS,
    note="语音识别负责把你的声音转成文字；切换后同样需要重启服务。",
)

SECTIONS: tuple[Section, ...] = (LLM_SECTION, TTS_SECTION, ASR_SECTION)


def section(key: str) -> Section | None:
    for item in SECTIONS:
        if item.key == key:
            return item
    return None


__all__ = [
    "ASR_PROVIDERS",
    "ASR_SECTION",
    "Field",
    "LLM_PROVIDERS",
    "LLM_SECTION",
    "Provider",
    "SECTIONS",
    "Section",
    "TTS_PROVIDERS",
    "TTS_SECTION",
    "section",
]
