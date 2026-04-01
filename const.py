"""Constants for MiniMax integration."""

import logging

DOMAIN = "minimax"
LOGGER = logging.getLogger(__package__)

DEFAULT_TITLE = "MiniMax"
DEFAULT_CONVERSATION_NAME = "MiniMax Conversation"
DEFAULT_STT_NAME = "MiniMax STT"
DEFAULT_TTS_NAME = "MiniMax TTS"

CONF_API_KEY = "api_key"
CONF_RECOMMENDED = "recommended"
CONF_PROMPT = "prompt"
CONF_CHAT_MODEL = "chat_model"
CONF_VOICE_ID = "voice_id"

RECOMMENDED_CHAT_MODEL = "MiniMax-M2.7"
RECOMMENDED_TTS_MODEL = "speech-2.8-hd"
RECOMMENDED_STT_MODEL = "MiniMax-M2.7"

ANTHROPIC_MODELS = {
    "MiniMax-M2.7",
    "MiniMax-M2.7-highspeed",
    "MiniMax-M2.5",
    "MiniMax-M2.5-highspeed",
    "MiniMax-M2.1",
    "MiniMax-M2.1-highspeed",
    "MiniMax-M2",
}

CHAT_MODELS = [
    {"label": "MiniMax-M2.7 (Recommended, Anthropic)", "value": "MiniMax-M2.7"},
    {
        "label": "MiniMax-M2.7-highspeed (Fast, Anthropic)",
        "value": "MiniMax-M2.7-highspeed",
    },
    {"label": "MiniMax-M2.5 (Anthropic)", "value": "MiniMax-M2.5"},
    {
        "label": "MiniMax-M2.5-highspeed (Fast, Anthropic)",
        "value": "MiniMax-M2.5-highspeed",
    },
    {"label": "MiniMax-M2.1 (Anthropic)", "value": "MiniMax-M2.1"},
    {
        "label": "MiniMax-M2.1-highspeed (Fast, Anthropic)",
        "value": "MiniMax-M2.1-highspeed",
    },
    {"label": "MiniMax-M2 (Anthropic)", "value": "MiniMax-M2"},
    {"label": "M2-her (Standard API)", "value": "M2-her"},
]


def is_anthropic_model(model: str) -> bool:
    """Check if model uses Anthropic API."""
    return model in ANTHROPIC_MODELS


CONF_SPEED = "speed"
CONF_VOL = "vol"
CONF_PITCH = "pitch"
DEFAULT_SPEED = 1.0
DEFAULT_VOL = 1.0
DEFAULT_PITCH = 0

CONF_CONVERSATION_TTS_ENABLED = "conversation_tts_enabled"
DEFAULT_CONVERSATION_TTS_ENABLED = True

SUPPORTED_LANGUAGES = ["en-US", "zh-CN"]

VOICE_IDS = {
    "en-US": [
        "English_expressive_narrator",
        "English_radiant_girl",
        "English_magnetic_voiced_man",
        "English_captivating_female1",
        "English_Aussie_Bloke",
        "English_Upbeat_Woman",
        "English_Trustworth_Man",
        "English_CalmWoman",
        "English_UpsetGirl",
        "English_Gentle-voiced_man",
        "English_Whispering_girl",
        "English_Diligent_Man",
        "English_Graceful_Lady",
        "English_ReservedYoungMan",
        "English_PlayfulGirl",
        "English_ManWithDeepVoice",
        "English_MaturePartner",
        "English_CheerfulGirl",
        "English_TeenageBoy",
        "English_AdultBoy",
        "English_LocalYoungMan",
        "English_CasualMan",
        "English_CountryLady",
        "English_MeditativeMan",
        "English_GentleWoman",
        "English_Narrator",
        "English_ThoughtfulMan",
        "English_Orator",
        "English_Robot",
        "English_RomanticMan",
        "English_RelaxedMan",
        "English_StoryWriter",
        "English_MelodiousWoman",
        "English_SunnyBoy",
        "English_HomeBodyDad",
        "English_CheerfulDad",
        "English_LovelyGirl",
        "English_SassyGirl",
        "English_HumorGirl",
        "English_PositiveGirl",
        "English_CalmMan",
        "English_SophisticatedLady",
        "English_ProfessionalMan",
        "English_MagneticWoman",
        "English_Professors_Wife",
        "English_ElderlyMan",
        "English_ClearYouth",
        "English_VivaciousWoman",
        "English_DynamicWoman",
        "English_MatureLady",
        "English_CheerfulMale",
        "English_CalmLady",
        "English_YouthfulMale",
        "English_LocalMan",
        "English_ThoughtfulLady",
        "English_ClearWoman",
    ],
    "zh-CN": [
        "Chinese_female_yaoyao",
        "Chinese_male_yunyang",
        "Chinese_female_xiaoyuan",
        "Chinese_female_yan_iter",
        "Chinese_female_xi_xin",
        "Chinese_female_tianxin",
        "Chinese_male_jin_yuan",
        "Chinese_male_chen_yi",
        "Chinese_female_xiaomeng",
        "Chinese_female_xiaoxue",
        "Chinese_male_xiaojun",
        "Chinese_male_xiaotian",
        "Chinese_female_xiaobian",
        "Chinese_female_yue_ling",
        "Chinese_male_xuanchen",
        "Chinese_female_xiaowei",
        "Chinese_female_qiqi",
        "Chinese_male_yikai",
        "Chinese_male_yiming",
        "Chinese_female_xiaojing",
        "Chinese_male_darong",
        "Chinese_female_mingyue",
        "Chinese_male_baijie",
        "Chinese_female_yiyi",
        "Chinese_male_dongze",
        "Chinese_female_jiayi",
        "Chinese_female_liucheng",
        "Chinese_male_baize",
        "Chinese_female_xuanzhen",
        "Chinese_male_zijun",
        "Chinese_female_daiyu",
        "Chinese_female_huanhuan",
        "Chinese_female_meiying",
        "Chinese_male_junyuan",
        "Chinese_female_xuejing",
        "Chinese_male_chengjie",
        "Chinese_female_yuchen",
        "Chinese_male_jiahui",
        "Chinese_female_chengxin",
        "Chinese_male_tengfei",
    ],
}

RECOMMENDED_CONVERSATION_OPTIONS = {
    CONF_PROMPT: "You are EVA, a friendly Danish AI home assistant. You speak Danish. Be warm, direct and practical. Respond briefly and precisely in Danish.",
    CONF_RECOMMENDED: True,
    CONF_CONVERSATION_TTS_ENABLED: DEFAULT_CONVERSATION_TTS_ENABLED,
}

RECOMMENDED_TTS_OPTIONS = {
    CONF_RECOMMENDED: True,
    CONF_VOICE_ID: "English_PlayfulGirl",
    CONF_SPEED: DEFAULT_SPEED,
    CONF_VOL: DEFAULT_VOL,
    CONF_PITCH: DEFAULT_PITCH,
}

RECOMMENDED_STT_OPTIONS = {
    CONF_RECOMMENDED: True,
    CONF_PROMPT: "Transcribe the attached audio",
}
