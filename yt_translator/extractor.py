# -*- coding: utf-8 -*-

"""
字幕提取模块：
- 优先使用 youtube-transcript-api 提取字幕
- 失败时使用 yt-dlp 下载 .vtt 并解析
"""

from __future__ import annotations

import os
import re
import json
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional, Dict

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


YOUTUBE_URL_RE = re.compile(r"(?:v=|youtu.be/)([A-Za-z0-9_-]{11})")


def parse_video_id(url: str) -> Optional[str]:
    """从 URL 中解析 YouTube 视频 ID。"""
    m = YOUTUBE_URL_RE.search(url)
    return m.group(1) if m else None


def _select_transcript(video_id: str, preferred_langs: List[str]) -> Tuple[List[Dict], Optional[str]]:
    """
    使用 youtube-transcript-api 获取字幕，按优先语言选择。
    返回字幕条目和检测到的语言代码。
    """
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    # 优先选择指定语言；支持 'auto'（自动翻译字幕）
    for lang in preferred_langs:
        try:
            if lang == 'auto':
                # 自动翻译到英文再用英文稿（后续翻译为目标语言）
                t = transcript_list.find_transcript(["en"]).translate('en')
                items = t.fetch()
                return items, 'en'
            t = transcript_list.find_transcript([lang])
            items = t.fetch()
            return items, t.language_code
        except (NoTranscriptFound, TranscriptsDisabled):
            continue
    # 尝试任何可用字幕
    try:
        t = transcript_list.find_manually_created_transcript([tr.language_code for tr in transcript_list])
        items = t.fetch()
        return items, t.language_code
    except Exception:
        pass
    # 退回第一个可用
    for t in transcript_list:
        try:
            return t.fetch(), t.language_code
        except Exception:
            continue
    raise NoTranscriptFound('No transcript available')


def _vtt_time_to_seconds(ts: str) -> float:
    """将 VTT 时间戳转换为秒。形如 '00:01:02.345'"""
    h, m, s = ts.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


def _parse_vtt(vtt_text: str) -> List[Dict]:
    """解析 WebVTT 内容为字幕条目列表。"""
    items: List[Dict] = []
    lines = vtt_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if '-->' in line:
            try:
                start_s, end_s = [p.strip().split(' ')[0] for p in line.split('-->')]
                start = _vtt_time_to_seconds(start_s)
                end = _vtt_time_to_seconds(end_s)
                text_lines: List[str] = []
                i += 1
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1
                text = ' '.join(text_lines)
                text = _clean_vtt_inline_markup(text)
                items.append({
                    'start': round(start, 3),
                    'duration': round(end - start, 3),
                    'text': text,
                })
            except Exception:
                i += 1
                continue
        i += 1
    return items


_RE_TAG_C = re.compile(r"</?c[^>]*>")
_RE_TAG_V = re.compile(r"<v[^>]*>")
_RE_TIME_INLINE = re.compile(r"<\d{2}:\d{2}:\d{2}\.\d{3}>")
_RE_ITALIC = re.compile(r"</?i>")
_RE_BOLD = re.compile(r"</?b>")
_RE_SPACES = re.compile(r"\s{2,}")

def _clean_vtt_inline_markup(text: str) -> str:
    """清理 VTT 行内标记，例如 <c>...</c>、<00:00:01.000>、<v Speaker> 等。"""
    t = text
    t = _RE_TAG_C.sub('', t)
    t = _RE_TAG_V.sub('', t)
    t = _RE_TIME_INLINE.sub('', t)
    t = _RE_ITALIC.sub('', t)
    t = _RE_BOLD.sub('', t)
    # 常见转义字符处理
    t = t.replace('\u200e', '').replace('\u200f', '').replace('\ufeff', '')
    t = _RE_SPACES.sub(' ', t).strip()
    return t


def _try_ytdlp_vtt(url: str, workdir: str) -> Tuple[List[Dict], Optional[str], Optional[str], List[Dict]]:
    """使用 yt-dlp 下载 vtt 字幕（优先人工字幕，退回自动字幕）并解析。返回 (items, lang, title, chapters)。"""
    Path(workdir).mkdir(parents=True, exist_ok=True)
    
    # 根据环境变量决定 Cookie 配置
    cookie_args: List[str] = []
    
    # 方式1：从 Secrets 读取 Cookie 内容（Streamlit Cloud 推荐）
    yt_cookies_content = os.getenv('YT_COOKIES')
    if yt_cookies_content:
        # 将 Cookie 内容写入临时文件
        cookies_file = os.path.join(workdir, 'cookies.txt')
        with open(cookies_file, 'w', encoding='utf-8') as f:
            f.write(yt_cookies_content)
        cookie_args = ['--cookies', cookies_file]
    # 方式2：从浏览器读取 Cookie（本地开发使用）
    else:
        browser = os.getenv('YT_DLP_BROWSER')  # 例如: 'chrome' 或 'safari'
        if browser:
            cookie_args = ['--cookies-from-browser', browser]

    attempts = [
        [
            sys.executable, '-m', 'yt_dlp', 
            '--skip-download', 
            '--write-sub', 
            '--sub-format', 'vtt', 
            '--convert-subs', 'vtt',
            # 仅限常见语言，避免 live_chat/*/all 导致噪声与过密时间轴
            '--sub-langs', 'en.*,en,zh-Hans,zh-Hant,zh-CN,zh-TW,ja,ko',
            '--write-info-json', 
            '--no-warnings',
            '--quiet',
            '--no-progress',
            '-o', os.path.join(workdir, '%(id)s.%(ext)s'),
            *cookie_args, url,
        ],
        [
            sys.executable, '-m', 'yt_dlp', 
            '--skip-download', 
            '--write-auto-sub', 
            '--sub-format', 'vtt', 
            '--convert-subs', 'vtt',
            '--write-info-json',
            '--no-warnings',
            '--quiet',
            '--no-progress',
            '-o', os.path.join(workdir, '%(id)s.%(ext)s'),
            *cookie_args, url,
        ],
    ]
    ran_ok = False
    timeout_seconds = 300  # 5分钟超时，适合长视频
    for cmd in attempts:
        try:
            result = subprocess.run(
                cmd, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                text=True
            )
            ran_ok = True
            break
        except subprocess.TimeoutExpired:
            # 超时：继续尝试下一个方法
            continue
        except subprocess.CalledProcessError as e:
            # 命令执行失败：继续尝试下一个方法
            continue
        except Exception:
            continue
    if not ran_ok:
        return [], None, None, []
    # 找到 vtt 与 info.json
    vid = parse_video_id(url) or ''
    vtt_path = None
    info_path = None
    for file in os.listdir(workdir):
        if file.endswith('.vtt') and (vid in file or not vid):
            vtt_path = os.path.join(workdir, file)
        if file.endswith('.info.json') and (vid in file or not vid):
            info_path = os.path.join(workdir, file)
    title = None
    chapters: List[Dict] = []
    if info_path and os.path.exists(info_path):
        try:
            with open(info_path, 'r', encoding='utf-8') as f:
                info = json.load(f)
                title = info.get('title')
                chapters = info.get('chapters', [])
        except Exception:
            pass
    if not vtt_path or not os.path.exists(vtt_path):
        return [], None, title, chapters
    with open(vtt_path, 'r', encoding='utf-8') as f:
        vtt_text = f.read()
    items = _parse_vtt(vtt_text)
    # 语言从文件名或 vtt 头部猜测（简化处理）
    lang = None
    m = re.search(r"\.(\w\w(?:-\w\w)?)\.vtt$", os.path.basename(vtt_path))
    if m:
        lang = m.group(1)
    return items, lang, title, chapters


def extract_transcript_with_fallback(url: str, preferred_langs: List[str], workdir: str) -> Tuple[List[Dict], Optional[str], Optional[str], str, List[Dict]]:
    """
    提取字幕，优先使用 API，失败则 ytdlp 兜底。
    返回 (items, detected_lang, title, source_name, chapters)。
    """
    video_id = parse_video_id(url)
    title: Optional[str] = None
    if not video_id:
        return [], None, title, 'unknown', []
    # 先尝试 API
    try:
        items, lang = _select_transcript(video_id, preferred_langs)
        # 获取视频标题（通过 transcript list 的 metadata 不稳定，这里不强求）
        title = None
        return items, lang, title, 'youtube-transcript-api', []
    except Exception:
        pass
    # 兜底：yt-dlp 解析 vtt
    items, lang, title, chapters = _try_ytdlp_vtt(url, workdir)
    return items, lang, title, 'yt-dlp', chapters




