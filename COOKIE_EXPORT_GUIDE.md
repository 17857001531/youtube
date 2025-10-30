# 📌 YouTube Cookie 导出指南

## 🎯 目的
解决 Streamlit Cloud 部署后无法提取 YouTube 字幕的问题（IP 被限制）。

---

## 📋 前置要求

✅ **Chrome 浏览器**（推荐）  
✅ **已登录 YouTube**（免费账号即可）

---

## 🚀 导出步骤

### **方式1：使用浏览器扩展（推荐）**

#### 1️⃣ **安装 Cookie 导出扩展**

**Chrome 商店搜索并安装以下任一扩展：**
- **Get cookies.txt LOCALLY** (推荐)
- **cookies.txt**
- **EditThisCookie**

#### 2️⃣ **访问 YouTube 并导出**

1. 打开 Chrome，访问 [https://www.youtube.com](https://www.youtube.com)
2. 确认右上角已登录你的账号 ✅
3. 点击浏览器扩展图标（通常在地址栏右侧）
4. 点击 **"Export"** 或 **"Download"** 按钮
5. 保存文件为 `youtube_cookies.txt`

#### 3️⃣ **复制 Cookie 内容**

1. 用文本编辑器打开 `youtube_cookies.txt`
2. **全选并复制**所有内容（Ctrl+A → Ctrl+C）

---

### **方式2：使用 Chrome 开发者工具（高级）**

<details>
<summary>点击展开详细步骤</summary>

#### 1️⃣ **打开开发者工具**

1. 访问 [https://www.youtube.com](https://www.youtube.com)
2. 按 `F12` 或 `Ctrl+Shift+I`（Mac: `Cmd+Option+I`）
3. 切换到 **"Application"** 标签页

#### 2️⃣ **查找 Cookie**

1. 左侧展开 **"Storage"** → **"Cookies"**
2. 点击 `https://www.youtube.com`
3. 你会看到所有 YouTube Cookie

#### 3️⃣ **手动复制（不推荐，工作量大）**

这种方式需要手动转换格式，**不推荐**。请使用方式1的浏览器扩展。

</details>

---

## 📝 配置 Cookie 到 Secrets

### **本地开发（.streamlit/secrets.toml）**

1. 打开 `.streamlit/secrets.toml` 文件
2. 找到 `YT_COOKIES` 配置项
3. 将复制的 Cookie 内容粘贴到三引号之间：

```toml
YT_COOKIES = """
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	1735948800	CONSENT	YES+cb.20210328-17-p0.en+FX+111
.youtube.com	TRUE	/	FALSE	1767484800	PREF	f4=4000000&tz=Asia.Shanghai
.youtube.com	TRUE	/	TRUE	1735948800	VISITOR_INFO1_LIVE	abcdefghijk
# ... 更多 Cookie 行 ...
"""
```

### **Streamlit Cloud 部署**

1. 访问 [https://share.streamlit.io/](https://share.streamlit.io/)
2. 找到你的应用 → 点击 **⋮** → **Settings**
3. 找到 **"Secrets"** 部分
4. 添加配置：

```toml
GITHUB_TOKEN = "你的GitHub Token"

YT_COOKIES = """
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	1735948800	CONSENT	YES+cb.20210328-17-p0.en+FX+111
.youtube.com	TRUE	/	FALSE	1767484800	PREF	f4=4000000&tz=Asia.Shanghai
# ... 粘贴你的完整 Cookie 内容 ...
"""
```

5. 点击 **"Save changes"**
6. 应用会自动重新部署 ⏳

---

## ⚠️ 注意事项

### **1. Cookie 有效期**
- YouTube Cookie 通常有效期：**几个月到一年**
- 过期后需要重新导出配置
- 如果字幕提取再次失败，首先检查 Cookie 是否过期

### **2. 安全性**
- Cookie 包含你的登录凭证，**不要分享给他人**
- 不要将 `.streamlit/secrets.toml` 提交到 Git
- `.gitignore` 已配置忽略此文件 ✅

### **3. 多行格式**
- 必须使用**三引号** `"""` 包裹 Cookie 内容
- 保持原始格式，包括所有换行和制表符
- 不要删除 Cookie 文件的头部注释行（`# Netscape HTTP Cookie File`）

---

## ✅ 验证配置

### **本地测试**

1. 重启 Streamlit 服务
2. 测试视频链接：`https://www.youtube.com/watch?v=-oy55UWlbdw`
3. 点击 **"开始处理"**
4. 预期结果：**✅ 成功提取字幕！**

### **Cloud 测试**

1. 在 Streamlit Cloud 保存 Secrets 后
2. 等待应用重新部署完成（2-3分钟）
3. 访问你的应用 URL
4. 测试相同视频链接
5. 预期结果：**✅ 成功提取字幕！**

---

## 🆘 常见问题

### **Q1: Cookie 导出后字幕提取还是失败？**
**A:** 检查以下几点：
- Cookie 内容是否完整（包含头部注释）
- 是否使用三引号包裹
- 格式是否保持原样（制表符、换行等）
- Chrome 是否已登录 YouTube

### **Q2: Cookie 过期了怎么办？**
**A:** 重新执行导出步骤，更新 Secrets 配置即可。

### **Q3: 可以使用无痕模式导出吗？**
**A:** 不行！必须在正常模式下登录 YouTube 后导出。

### **Q4: 需要 YouTube Premium 吗？**
**A:** 不需要！免费账号的 Cookie 即可。

---

## 📞 支持

如果遇到问题，请：
1. 检查 Cookie 格式是否正确
2. 检查 Chrome 是否登录 YouTube
3. 尝试重新导出 Cookie
4. 查看应用日志中的详细错误信息

---

**导出完成后，记得配置到 Secrets 并重新部署！** 🚀

