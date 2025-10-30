# 🚀 Streamlit Cloud 部署指南

本指南将帮助你将 YouTube 字幕翻译工具部署到 Streamlit Cloud。

---

## 📋 前置准备

### 1️⃣ **GitHub Token（必需）**
用于上传 HTML 报告到 GitHub Gist。

**获取步骤：**
1. 访问 [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. 点击 **"Generate new token"** → **"Generate new token (classic)"**
3. 设置：
   - **Note**: `youtube-translator-gist`
   - **Expiration**: `No expiration`（或选择你需要的有效期）
   - **Select scopes**: 只勾选 ✅ **`gist`**
4. 点击 **"Generate token"**
5. **复制并保存** Token（格式：`ghp_xxxxxxxxxxxx`）

### 2️⃣ **YouTube Cookies（必需）**
用于解决 Streamlit Cloud IP 被 YouTube 限制的问题。

**获取步骤：** 参考 [`COOKIE_EXPORT_GUIDE.md`](COOKIE_EXPORT_GUIDE.md)

---

## 🌐 第一步：推送代码到 GitHub

### **1. 初始化 Git 仓库（如果还没有）**

```bash
cd /Users/miracle/Desktop/youtube-translator_zhangjie_副本
git init
git add .
git commit -m "Initial commit: YouTube Translator"
```

### **2. 创建 GitHub 仓库**

1. 访问 [https://github.com/new](https://github.com/new)
2. 设置：
   - **Repository name**: `youtube-translator`（或你喜欢的名字）
   - **Description**: `YouTube 字幕翻译工具`
   - **Privacy**: **Private**（推荐，更安全）
3. 点击 **"Create repository"**

### **3. 推送代码**

```bash
git remote add origin https://github.com/你的用户名/youtube-translator.git
git branch -M main
git push -u origin main
```

---

## ☁️ 第二步：部署到 Streamlit Cloud

### **1. 访问 Streamlit Cloud**

打开 [https://share.streamlit.io/](https://share.streamlit.io/)

### **2. 创建新应用**

1. 点击 **"New app"** 按钮
2. 配置应用：
   - **Repository**: 选择你刚才创建的仓库（`youtube-translator`）
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL（可选）**:
     - 使用默认：`https://你的用户名-youtube-translator-app-abc123.streamlit.app/`
     - 自定义（如果可用）：`https://自定义名称.streamlit.app/`
       - 只能包含小写字母、数字、连字符
       - 3-63 个字符
       - 示例：`yt-translator`, `subtitle-tool`, `alo001`

### **3. 配置 Python 版本**

⚠️ **重要：必须设置为 Python 3.10**

1. 点击 **"Advanced settings"**
2. 找到 **"Python version"**
3. 从下拉框选择：**`3.10`**

### **4. 配置 Secrets（核心步骤）**

在 **"Secrets"** 部分，粘贴以下配置：

```toml
# ========================================
# 1. GitHub Token（用于 Gist 上传）
# ========================================
GITHUB_TOKEN = "你的GitHub Token（ghp_开头）"

# ========================================
# 2. YouTube Cookies（用于字幕提取）
# ========================================
# 粘贴你从 Chrome 导出的完整 Cookie 内容
YT_COOKIES = """
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	1735948800	CONSENT	YES+cb.20210328-17-p0.en+FX+111
.youtube.com	TRUE	/	FALSE	1767484800	PREF	f4=4000000&tz=Asia.Shanghai
.youtube.com	TRUE	/	TRUE	1735948800	VISITOR_INFO1_LIVE	abcdefghijk
# ... 粘贴你的完整 Cookie 内容（参考 COOKIE_EXPORT_GUIDE.md）...
"""
```

**配置说明：**
- `GITHUB_TOKEN`: 替换为你自己的 Token（如果你有新的 Token）
- `YT_COOKIES`: 
  - 必须使用**三引号** `"""` 包裹
  - 粘贴从 Chrome 导出的**完整** Cookie 内容
  - 保持原始格式（包括制表符、换行）
  - 参考：[`COOKIE_EXPORT_GUIDE.md`](COOKIE_EXPORT_GUIDE.md)

### **5. 部署应用**

1. 检查所有配置无误
2. 点击 **"Deploy!"** 按钮
3. 等待部署完成（通常 2-5 分钟）
4. 部署成功后会自动跳转到你的应用 URL

---

## ✅ 第三步：测试部署

### **1. 访问你的应用**

打开你的 Streamlit Cloud 应用 URL（例如：`https://alo001.streamlit.app/`）

### **2. 测试字幕提取**

**测试视频1（18秒短视频）：**
```
https://www.youtube.com/watch?v=jNQXAC9IVRw
```

**测试视频2（你的测试视频）：**
```
https://www.youtube.com/watch?v=-oy55UWlbdw
```

**测试步骤：**
1. 粘贴视频链接
2. 点击 **"开始处理"**
3. 等待处理完成
4. 预期结果：
   - ✅ **成功提取字幕！**
   - 显示处理进度
   - 生成历史记录卡片
   - 可以点击 **"下载"** 按钮
   - 可以点击 **"预览"** 生成在线链接

---

## 🔧 常见问题排查

### **Q1: 部署后还是报错"未能获取到任何字幕"**

**排查步骤：**

1. **检查 Python 版本**
   - Streamlit Cloud → 应用设置 → Python version
   - 确保是 **3.10**（不是 3.13）

2. **检查 Secrets 配置**
   - 找到 **⋮** → **Settings** → **Secrets**
   - 确认 `YT_COOKIES` 已配置
   - 确认 Cookie 内容完整（包含头部注释）
   - 确认使用了三引号 `"""`

3. **检查 Cookie 有效性**
   - 本地 Chrome 访问 YouTube，确认已登录
   - 重新导出 Cookie（可能已过期）
   - 更新 Secrets 中的 `YT_COOKIES`

4. **查看详细日志**
   - 处理失败后，点击 **"🔍 查看详细日志"**
   - 检查错误信息
   - 如果提示 Cookie 相关错误，重新导出

### **Q2: 找不到 Secrets 配置入口**

**解决方法：**
- 必须先完成部署（点击 "Deploy"）
- 部署后才能看到 Settings → Secrets
- 如果已部署：点击应用右侧 **⋮** → **Settings** → 拉到底部找到 **"Secrets"**

### **Q3: 预览按钮生成链接失败**

**可能原因：**
- GitHub Token 未配置或已失效
- GitHub API 限流（稍后重试）
- 网络问题

**解决方法：**
1. 检查 `GITHUB_TOKEN` 是否正确
2. 访问 [https://github.com/settings/tokens](https://github.com/settings/tokens) 确认 Token 有效
3. 如果 Token 过期，生成新的并更新 Secrets

### **Q4: Cookie 过期了怎么办？**

**症状：**
- 之前可以提取字幕，现在突然失败
- 详细日志显示 Cookie 相关错误

**解决方法：**
1. 参考 [`COOKIE_EXPORT_GUIDE.md`](COOKIE_EXPORT_GUIDE.md) 重新导出
2. 更新 Streamlit Cloud Secrets 中的 `YT_COOKIES`
3. 应用会自动重新部署

### **Q5: 私有仓库能部署吗？**

**答案：可以！** ✅

- Streamlit Cloud 完全支持私有仓库
- 用户访问的是你的应用 URL，看不到代码
- 更安全，推荐使用私有仓库

---

## 🔄 更新部署

### **方法1：推送代码自动更新（推荐）**

```bash
git add .
git commit -m "更新功能"
git push
```

- Streamlit Cloud 会自动检测代码变化
- 自动重新部署
- 无需手动操作

### **方法2：手动触发重新部署**

1. Streamlit Cloud → 你的应用 → **⋮** → **Reboot app**
2. 应用会重新启动（不会重新拉取代码）

### **方法3：更新 Secrets**

1. Streamlit Cloud → 你的应用 → **⋮** → **Settings** → **Secrets**
2. 修改配置
3. 点击 **"Save changes"**
4. 应用会自动重新部署

---

## 📊 部署后的使用情况

### **资源限制（Streamlit Cloud 免费版）**

- **RAM**: 1 GB
- **CPU**: 共享
- **存储**: 临时文件（应用重启时清空）
- **会话限制**: 本应用已设置为 10 次/会话

### **多用户支持**

✅ **完全支持多用户同时使用：**
- 每个用户有独立的会话
- 用户之间互不影响
- 所有用户共享你配置的 GitHub Token 和 Cookie

### **Gist 管理**

⚠️ **注意：**
- 每次预览都会创建一个新的 Gist
- Gist 会永久保存在你的 GitHub 账号
- 建议定期手动清理：[https://gist.github.com/](https://gist.github.com/)

---

## 🎉 部署完成！

**你的 YouTube 字幕翻译工具现在已上线！**

**分享你的应用：**
- 复制你的应用 URL（例如：`https://alo001.streamlit.app/`）
- 分享给需要的用户
- 所有人都可以直接使用，无需配置

**祝你使用愉快！** 🚀

---

## 📞 技术支持

如果遇到问题：
1. 查看详细日志（点击 "🔍 查看详细日志"）
2. 检查本指南的常见问题部分
3. 查看 [`COOKIE_EXPORT_GUIDE.md`](COOKIE_EXPORT_GUIDE.md)
4. 检查 GitHub Token 和 Cookie 配置

---

**最后更新**: 2025-10-30
