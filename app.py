#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouTube 字幕翻译工具 - Streamlit Web 应用
提供友好的 Web 界面，让用户无需命令行即可使用翻译功能
"""

import streamlit as st
import os
import sys
import tempfile
import time

# 添加项目路径到系统路径
sys.path.insert(0, os.path.dirname(__file__))

# 从 Streamlit Secrets 加载环境变量
if hasattr(st, 'secrets'):
    # 加载 YouTube Cookies（用于 yt-dlp 字幕提取）
    if 'YT_COOKIES' in st.secrets:
        os.environ['YT_COOKIES'] = st.secrets['YT_COOKIES']

from yt_translator.extractor import extract_transcript_with_fallback, parse_video_id
from yt_translator.translator import SubtitleTranslator
from yt_translator.html_report import HtmlReportGenerator
from file_share import create_shareable_link


def setup_page():
    """配置页面基本设置"""
    st.set_page_config(
        page_title="YouTube 字幕提取工具",
        page_icon="▶️",
        layout="wide",
        initial_sidebar_state="collapsed",
        menu_items=None  # 隐藏所有菜单
    )
    
    # 隐藏侧边栏导航，自定义输入框背景色
    st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
        /* 主内容区输入框背景色 */
        section.main .stTextInput > div > div > input {
            background-color: #F1F2F6 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # 标题区域 - 使用原生组件
    st.markdown("")  # 顶部间距
    st.markdown("")
    st.title("YouTube 字幕提取工具")
    st.caption("提取字幕 ｜ 翻译段落 ｜ 总结全文")
    st.divider()


def sidebar_config():
    """侧边栏配置"""
    st.sidebar.header("配置选项")
    
    # 目标语言
    language_options = {
        "简体中文": "zh-CN",
        "繁体中文": "zh-TW",
        "日语": "ja",
        "韩语": "ko",
        "法语": "fr",
        "德语": "de",
        "西班牙语": "es",
        "俄语": "ru"
    }
    target_lang_name = st.sidebar.selectbox(
        "目标语言",
        list(language_options.keys())
    )
    target_lang = language_options[target_lang_name]
    
    # 翻译引擎
    provider = st.sidebar.selectbox(
        "翻译引擎",
        ["google", "deepseek"],
        index=1
    )
    
    # DeepSeek 配置
    deepseek_api_key = None
    deepseek_base_url = "https://api.deepseek.com"
    deepseek_model = "deepseek-chat"
    deepseek_temperature = 0.2
    
    if provider == "deepseek":
        deepseek_api_key = st.sidebar.text_input(
            "DeepSeek API Key",
            type="password"
        )
        
        with st.sidebar.expander("DeepSeek 高级设置"):
            deepseek_base_url = st.text_input(
                "API 地址",
                value="https://api.deepseek.com"
            )
            deepseek_model = st.text_input(
                "模型名称",
                value="deepseek-chat"
            )
            deepseek_temperature = st.slider(
                "温度参数",
                min_value=0.0,
                max_value=1.0,
                value=0.2,
                step=0.1
            )
    
    # 其他配置
    with st.sidebar.expander("其他配置"):
        source_langs = st.text_input(
            "源语言优先级",
            value="en,en-US,en-GB,auto"
        )
        
        batch_size = st.number_input(
            "批处理大小",
            min_value=1,
            max_value=200,
            value=100
        )
        
        max_retries = st.number_input(
            "最大重试次数",
            min_value=0,
            max_value=10,
            value=3
        )
        
        concurrent_workers = st.number_input(
            "并发线程数",
            min_value=1,
            max_value=10,
            value=4
        )
        
        yt_browser = st.selectbox(
            "浏览器 Cookie",
            ["不使用", "chrome", "firefox", "safari", "edge"],
            index=1
        )
    
    # 显示会话使用统计 - 始终显示
    st.sidebar.markdown("")  # 间距替代divider
    processing_count = st.session_state.get('processing_count', 0)
    max_processing = 10  # 统一为 10 个
    usage_percent = (processing_count / max_processing) * 100
    st.sidebar.progress(usage_percent / 100, text=f"会话使用: {processing_count}/{max_processing}")
    
    return {
        "url": None,
        "provider": provider,
        "deepseek_api_key": deepseek_api_key,
        "deepseek_base_url": deepseek_base_url,
        "deepseek_model": deepseek_model,
        "deepseek_temperature": deepseek_temperature,
        "target_lang": target_lang,
        "source_langs": [s.strip() for s in source_langs.split(",") if s.strip()],
        "batch_size": batch_size,
        "max_retries": max_retries,
        "concurrent_workers": concurrent_workers,
        "yt_browser": None if yt_browser == "不使用" else yt_browser
    }


def validate_config(config):
    """验证配置"""
    errors = []
    
    if not config["url"]:
        errors.append("❌ 请输入 YouTube 视频链接")
    elif not parse_video_id(config["url"]):
        errors.append("❌ 无效的 YouTube 视频链接")
    
    if config["provider"] == "deepseek" and not config["deepseek_api_key"]:
        errors.append("❌ 使用 DeepSeek 时必须提供 API Key")
    
    return errors


def process_video(config, progress_container=None):
    """处理视频翻译"""
    # 设置环境变量
    if config["provider"] == "deepseek":
        os.environ["DEEPSEEK_API_KEY"] = config["deepseek_api_key"]
        os.environ["DEEPSEEK_BASE_URL"] = config["deepseek_base_url"]
        os.environ["DEEPSEEK_MODEL"] = config["deepseek_model"]
        os.environ["DEEPSEEK_TEMPERATURE"] = str(config["deepseek_temperature"])
    
    if config["yt_browser"]:
        os.environ["YT_DLP_BROWSER"] = config["yt_browser"]
    
    # 解析视频 ID
    video_id = parse_video_id(config["url"])
    
    # 使用临时目录，会话结束后自动删除
    with tempfile.TemporaryDirectory() as tmpdir:
        video_outdir = tmpdir
        
        # 记录开始时间
        start_time = time.time()
        
        # 创建进度显示 - 使用原生组件
        if progress_container:
            # 清空容器并创建进度元素
            with progress_container.container():
                progress_bar = st.progress(0)
                status_text = st.empty()
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        # 步骤 1: 提取字幕
        status_text.markdown("""
        <div style="display: flex; align-items: center; padding: 12px;">
            <div style="
                width: 16px;
                height: 16px;
                border: 2px solid #999;
                border-top-color: transparent;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                margin-right: 8px;
            "></div>
            <span style="color: #666;">正在连接 YouTube...</span>
        </div>
        <style>
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        </style>
        """, unsafe_allow_html=True)
        progress_bar.progress(10)
        
        try:
            transcript_items, detected_lang, title, source_name, chapters = extract_transcript_with_fallback(
                config["url"],
                preferred_langs=config["source_langs"],
                workdir=video_outdir
            )
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                st.error(f"❌ 提取字幕超时（视频可能过长）。错误信息：{error_msg}")
            else:
                st.error(f"❌ 提取字幕失败：{error_msg}")
            st.info("💡 提示：对于超长视频（>20分钟），可能需要更长时间。请稍后重试或尝试较短视频。")
            return None
        
        if not transcript_items:
            st.error("❌ 未能获取到任何字幕，请检查视频是否有字幕。")
            st.info("💡 可能的原因：\n1. 视频确实没有字幕\n2. 视频过长导致超时（Streamlit Cloud 限制）\n3. Cookie 已过期，需要重新配置")
            return None
        
        status_text.success(f"✅ 提取字幕完成！检测到语言：{detected_lang}")
        progress_bar.progress(30)
        
        # 步骤 2: 翻译字幕
        status_text.markdown(f"""
        <div style="display: flex; align-items: center; padding: 12px;">
            <div style="
                width: 16px;
                height: 16px;
                border: 2px solid #999;
                border-top-color: transparent;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                margin-right: 8px;
            "></div>
            <span style="color: #666;">正在使用 {config['provider'].upper()} 翻译字幕...</span>
        </div>
        <style>
            @keyframes spin {{
                to {{ transform: rotate(360deg); }}
            }}
        </style>
        """, unsafe_allow_html=True)
        progress_bar.progress(40)
        
        translator = SubtitleTranslator(
            target_language=config["target_lang"],
            provider=config["provider"],
            batch_size=config["batch_size"],
            max_retries=config["max_retries"],
            concurrent_workers=config["concurrent_workers"]
        )
        
        items_en = [{
            'start': it['start'],
            'duration': it['duration'],
            'text': it['text'],
            'translated_text': ''
        } for it in transcript_items]
        
        progress_bar.progress(50)
        
        # 翻译全文并分段
        full_text = "\n".join([it.get('text', '').strip() for it in transcript_items if it.get('text')])
        cn_paragraphs = translator.translate_full_and_split(full_text)
        
        status_text.success(f"✅ 翻译完成！生成了 {len(cn_paragraphs)} 个段落")
        progress_bar.progress(70)
        
        # 生成总结
        status_text.markdown("""
        <div style="display: flex; align-items: center; padding: 12px;">
            <div style="
                width: 16px;
                height: 16px;
                border: 2px solid #999;
                border-top-color: transparent;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                margin-right: 8px;
            "></div>
            <span style="color: #666;">正在生成内容总结...</span>
        </div>
        <style>
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        </style>
        """, unsafe_allow_html=True)
        summary = translator.generate_summary(full_text)
        
        progress_bar.progress(80)
        
        # 翻译标题
        status_text.markdown("""
        <div style="display: flex; align-items: center; padding: 12px;">
            <div style="
                width: 16px;
                height: 16px;
                border: 2px solid #999;
                border-top-color: transparent;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                margin-right: 8px;
            "></div>
            <span style="color: #666;">正在翻译视频标题...</span>
        </div>
        <style>
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        </style>
        """, unsafe_allow_html=True)
        title_cn = translator.translate_title(title or '')
        
        # 翻译章节
        if chapters:
            status_text.markdown("""
            <div style="display: flex; align-items: center; padding: 12px;">
                <div style="
                    width: 16px;
                    height: 16px;
                    border: 2px solid #999;
                    border-top-color: transparent;
                    border-radius: 50%;
                    animation: spin 0.8s linear infinite;
                    margin-right: 8px;
                "></div>
                <span style="color: #666;">正在翻译章节标题...</span>
            </div>
            <style>
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            </style>
            """, unsafe_allow_html=True)
            chapters = translator.translate_chapters(chapters)
        
        progress_bar.progress(85)
        
        # 分配时间轴
        if transcript_items:
            total_start = float(transcript_items[0]['start'])
            total_end = float(transcript_items[-1]['start']) + float(transcript_items[-1]['duration'])
        else:
            total_start = 0.0
            total_end = 0.0
        
        total_duration = max(0.0, total_end - total_start)
        total_chars = sum(max(1, len(p)) for p in cn_paragraphs) or 1
        min_seg = 1.8
        
        items_cn = []
        acc = total_start
        for i, p in enumerate(cn_paragraphs):
            frac = max(1, len(p)) / total_chars
            seg = total_duration * frac if total_duration > 0 else min_seg
            seg = max(seg, min_seg)
            end = acc + seg
            if i == len(cn_paragraphs) - 1:
                end = total_end or (acc + seg)
            items_cn.append({
                'start': round(acc, 3),
                'duration': round(max(0.1, end - acc), 3),
                'text': '',
                'translated_text': p
            })
            acc = end
        
        progress_bar.progress(90)
        
        # 步骤 3: 生成 HTML 报告
        status_text.markdown("""
        <div style="display: flex; align-items: center; padding: 12px;">
            <div style="
                width: 16px;
                height: 16px;
                border: 2px solid #999;
                border-top-color: transparent;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                margin-right: 8px;
            "></div>
            <span style="color: #666;">正在生成 HTML 报告...</span>
        </div>
        <style>
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        </style>
        """, unsafe_allow_html=True)
        
        html_generator = HtmlReportGenerator()
        html_path = os.path.join(video_outdir, 'report.html')
        
        html_generator.generate(
            output_path=html_path,
            video_id=video_id,
            title=title,
            title_cn=title_cn,
            items_en=items_en,
            items_cn=items_cn,
            chapters=chapters,
            summary=summary,
            source_language=detected_lang,
            target_language=config["target_lang"]
        )
        
        status_text.success("✅ 处理完成！")
        progress_bar.progress(100)
        
        # 计算处理时长
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 读取生成的 HTML
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return {
            'video_id': video_id,
            'title': title,
            'title_cn': title_cn,
            'html_content': html_content,  # 返回 HTML 内容
            'summary': summary,
            'full_text': full_text,  # 返回原文全文
            'stats': {
                'source_language': detected_lang,
                'target_language': config["target_lang"],
                'subtitle_count': len(transcript_items),
                'paragraph_count': len(cn_paragraphs),
                'source': source_name,
                'processing_time': processing_time,
                'full_text_length': len(full_text)  # 原文字符数
            }
        }


def main():
    """主函数"""
    setup_page()
    
    # 初始化会话状态
    if 'history' not in st.session_state:
        st.session_state.history = []
    
    # 获取侧边栏配置
    config = sidebar_config()
    
    # 初始化会话状态
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'session_start_time' not in st.session_state:
        st.session_state.session_start_time = time.time()
    if 'processing_count' not in st.session_state:
        st.session_state.processing_count = 0
    
    # 配置限制参数（统一为10，保持逻辑一致）
    MAX_HISTORY = 10                    # 历史记录最多保留 10 个
    MAX_PROCESSING_PER_SESSION = 10     # 单次会话最多处理 10 个视频
    SESSION_TIMEOUT_HOURS = 24          # 会话超时时间 24 小时
    
    # 添加间距
    st.markdown("")
    st.markdown("")
    
    # 输入区域 - 缩短1/4宽度，保持左侧对齐
    main_col, right_space = st.columns([3, 1])
    
    with main_col:
        input_col, button_col = st.columns([4, 1])
        
        with input_col:
            url = st.text_input(
                "YouTube视频链接",
                placeholder="请输入 YouTube 视频链接，例如: https://www.youtube.com/watch?v=...",
                key="main_url_input",
                label_visibility="collapsed"
            )
        
        with button_col:
            process_button = st.button("开始处理", use_container_width=True, type="primary")
    
    config["url"] = url
    
    # 创建固定的进度显示区域
    progress_container = st.empty()
    
    # 显示历史记录
    if st.session_state.history:
        # 注入CSS来缩小列间距
        st.markdown("""
        <style>
        /* 缩小历史记录区域的列间距 */
        div[data-testid="column"]:has(button[kind="secondary"]) {
            padding-left: 0.25rem !important;
            padding-right: 0.25rem !important;
        }
        /* 特别针对下载按钮和预览按钮的列 */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2),
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) {
            padding-left: 0.25rem !important;
            padding-right: 0.25rem !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        for i, item in enumerate(st.session_state.history):
            # 兼容性处理：旧记录可能没有html_content
            if 'html_content' not in item:
                continue  # 跳过旧记录
            
            # 使用columns布局 (调整间距使按钮更紧凑，gap控制间距)
            col1, col2, col3 = st.columns([6, 0.6, 0.6], gap="small")
            
            with col1:
                # HTML卡片
                total_length = item.get('total_length', '--')
                
                st.markdown(f"""
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 16px;
                    padding: 0 20px;
                    background: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                    margin-bottom: 12px;
                    height: 40px;
                ">
                    <div style="font-size: 15px; color: #333; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0;">{item['title']}</div>
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 6px;
                        color: #4caf50;
                        font-size: 13px;
                        white-space: nowrap;
                    ">
                        <div style="
                            width: 8px;
                            height: 8px;
                            background: #4caf50;
                            border-radius: 50%;
                        "></div>
                        已完成
                    </div>
                    <div style="color: #999; font-size: 13px; white-space: nowrap;">总长度：{total_length}</div>
                    <div style="color: #999; font-size: 13px; white-space: nowrap;">耗时：{item['processing_time']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # 下载按钮
                st.download_button(
                    label="下载",
                    data=item['html_content'],
                    file_name=f"{item['video_id']}_report.html",
                    mime="text/html",
                    key=f"download_{i}"
                )
            
            with col3:
                # 创建一个容器用于动态显示内容
                preview_container = st.empty()
                
                # 检查是否已有预览链接
                if 'preview_url' in item and item['preview_url']:
                    # 已有链接，直接显示"打开链接"
                    with preview_container:
                        st.markdown(f"""
                        <a href="{item['preview_url']}" target="_blank" style="
                            color: #0084ff;
                            text-decoration: none;
                            font-size: 13px;
                            white-space: nowrap;
                            display: inline-block;
                            padding: 8px 12px;
                        ">打开链接</a>
                        """, unsafe_allow_html=True)
                else:
                    # 未生成链接，显示预览按钮
                    with preview_container:
                        if st.button("预览", key=f"online_{i}"):
                            # 立即清空容器，显示loading
                            preview_container.empty()
                            
                            # 在同一位置显示loading
                            with preview_container:
                                st.markdown("""
                                <div style="display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px;">
                                    <div style="
                                        width: 16px;
                                        height: 16px;
                                        border: 2px solid #f3f3f3;
                                        border-top: 2px solid #999;
                                        border-radius: 50%;
                                        animation: spin 1s linear infinite;
                                    "></div>
                                    <style>
                                    @keyframes spin {
                                        0% { transform: rotate(0deg); }
                                        100% { transform: rotate(360deg); }
                                    }
                                    </style>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # 创建新的 Gist
                            result = create_shareable_link(item['html_content'], item['video_id'])
                            
                            # 清空loading
                            preview_container.empty()
                            
                            if result['success']:
                                # 保存到 history_item
                                item['preview_url'] = result['url']
                                item['gist_id'] = result['gist_id']
                                
                                # 在同一位置显示"打开链接"
                                with preview_container:
                                    st.markdown(f"""
                                    <a href="{result['url']}" target="_blank" style="
                                        color: #0084ff;
                                        text-decoration: none;
                                        font-size: 13px;
                                        white-space: nowrap;
                                        display: inline-block;
                                        padding: 8px 12px;
                                    ">打开链接</a>
                                    """, unsafe_allow_html=True)
                                
                                # 触发重新渲染
                                st.rerun()
                            else:
                                # 失败后重新显示预览按钮
                                with preview_container:
                                    st.error(result['message'])
                                    if st.button("重试预览", key=f"retry_{i}"):
                                        st.rerun()
    
    # 处理视频
    if process_button:
        session_age_hours = (time.time() - st.session_state.session_start_time) / 3600
        
        if session_age_hours > SESSION_TIMEOUT_HOURS:
            st.warning(f"⏰ 会话已超时（{SESSION_TIMEOUT_HOURS}小时），请刷新页面重新开始")
        elif st.session_state.processing_count >= MAX_PROCESSING_PER_SESSION:
            st.error(f"🚫 已达到单个会话处理上限（{MAX_PROCESSING_PER_SESSION} 个视频）")
            st.info("💡 **原因**: 为了保护服务器资源，限制单次会话处理数量")
            st.info("🔄 **解决方法**: 请刷新页面开始新的会话，或下载已处理的内容")
        else:
            errors = validate_config(config)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                try:
                    result = process_video(config, progress_container)
                    
                    # 清空进度显示
                    progress_container.empty()
                    
                    if result:
                        # 增加处理计数
                        st.session_state.processing_count += 1
                        
                        # 格式化处理时长
                        processing_time = result['stats'].get('processing_time', 0)
                        if processing_time < 60:
                            time_str = f"{processing_time:.1f}秒"
                        else:
                            minutes = int(processing_time // 60)
                            seconds = int(processing_time % 60)
                            time_str = f"{minutes}分{seconds}秒"
                        
                        # 获取原文总字符数
                        total_chars = result['stats'].get('full_text_length', 0)
                        
                        # 添加到历史记录
                        history_item = {
                            'index': len(st.session_state.history),
                            'video_id': result['video_id'],
                            'title': result['title'],  # 使用原始标题
                            'title_cn': result['title_cn'],  # 保留翻译标题备用
                            'processing_time': time_str,
                            'total_length': f"{total_chars}字",  # 总长度（原文字符数）
                            'html_content': result['html_content'],  # 存储HTML内容
                            'timestamp': time.time(),
                            'preview_url': None,  # 初始为空，点击预览后才生成
                            'gist_id': None  # 初始为空，点击预览后才生成
                        }
                        st.session_state.history.insert(0, history_item)
                        
                        # 更新索引
                        for i, item in enumerate(st.session_state.history):
                            item['index'] = i
                        
                        # 只保留最近的记录
                        if len(st.session_state.history) > MAX_HISTORY:
                            st.session_state.history = st.session_state.history[:MAX_HISTORY]
                        
                        st.success("✅ 处理完成！")
                        st.rerun()
                        
                except Exception as e:
                    # 清空进度显示
                    progress_container.empty()
                    st.error(f"❌ 处理失败：{str(e)}")
                    st.exception(e)


if __name__ == "__main__":
    main()

