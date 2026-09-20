---
name: bilibili-recipe-extractor
description: >-
  Extracts recipes, ingredients, and cooking steps from Bilibili video tutorials and creator spaces
  using Cookie authentication, Wbi dynamic signing, and direct subtitle/metadata extraction without video download or ASR.
---

# B 站食谱提取与 Cooklang 生成规范 (Bilibili Recipe Extractor)

本技能定义了从 B 站视频教程或 UP 主个人空间高效提取食谱的标准化工作流。
核心优势：**基于 B 站官方 Wbi 鉴权直接拉取结构化字幕与元数据，秒级响应，无需下载音视频或本地运行 ASR 转录。**

---

## 一、 鉴权与字幕获取核心机制

### 1. Cookie 与 Wbi 动态签名
B 站核心接口（个人空间投稿 `/x/space/wbi/arc/search`、视频字幕 `/x/player/wbi/v2`）均启用了 **Wbi 防爬风控**：
- **Cookie 路径**：优先读取本地 Netscape 格式文件 `/home/deck/Downloads/www.bilibili.com_cookies.txt`。
- **密钥生成**：
  1. 请求 `https://api.bilibili.com/x/web-interface/nav` 获取 `wbi_img.img_url` 与 `sub_url`；
  2. 提取文件名去除后缀拼接为 64 位原始秘钥；
  3. 使用预设的 64 位索引置换表（`MIXIN_KEY_ENC_TAB`）重排并截取前 32 位生成加盐 `mixin_key`。
- **签名生成**：请求参数按 Key 字典序排序，拼接时间戳 `wts` 和 `mixin_key` 计算 MD5 得到 `w_rid`。

> [!WARNING]
> 若使用未签名的 `/x/player/v2` 接口，B 站风控会返回虚假示例字幕链接（例如诺贝尔奖演讲）。**必须使用经过 Wbi 签名的 `/x/player/wbi/v2` 接口**，才能获取视频真实的字幕文本。

---

## 二、 核心提取工作流

### 工作流 A：单个视频提取详细食谱（含步骤）

当用户提供单个 B 站做菜视频链接或 BVID（如 `https://www.bilibili.com/video/BV1iFQEY7ED7`）时：

1. **直接提取视频字幕与元数据**：
   运行技能内置脚本：
   ```bash
   python3 .agents/skills/bilibili-recipe-extractor/scripts/fetch_video_recipe.py <BVID_或_URL>
   ```
   或在 Python 中调用 `fetch_video_details(bvid)`，获取视频标题、时长及完整的台词文本。

2. **配方与步骤提炼**：
   从字幕台词中精确定位：
   - **食材与用量**：主料（如 500g 虾仁）、辅料（葱、姜水）、调味料（盐、糖、胡椒、淀粉、蛋清）的精准配比。
   - **关键操作细节**：原料处理（吸干水分、刀背拍切）、投料顺序、搅打上劲手法、计时器（摔打次数、水开火候、煮制用时）。

3. **用户饮食偏好合规检查**：
   - **忌口处理**：若用户注明不吃猪肉，视频中如提及猪肥肉、猪油、猪肉馅等，应予以**剔除或替换为牛肉/禽类/纯食材**。
   - **宝宝餐调整**：若保存至 `babyfood/`，盐、糖适度减量，避免重辣与添加剂。

4. **生成标准 Cooklang (.cook) 文件**：
   包含完整的 YAML Frontmatter 与结构化步骤段落：
   ```cooklang
   ---
   title: 菜品名称
   tags:
     - 宝宝餐（或 减肥餐/家常菜）
     - 分类（肉菜/主食/素菜/海鲜）
     - 口味（咸鲜/酸甜）
   servings: 2
   prep_time: 20 minutes
   cook_time: 10 minutes
   source: https://www.bilibili.com/video/BVxxxxxx
   ---

   @主料{数量%单位} 处理方法描述文本...

   加入 @调味料{数量%单位}，搅拌上劲 ~{2%分钟}...
   ```

---

### 工作流 B：UP 主空间批量提取（用于菜单与采购生成）

当需要从 UP 主空间批量抓取食谱库（如减脂餐、一日三餐合集）：

1. **批量抓取脚本**：
   项目内置了通用脚本 [src/menu/extract_diet.py](file:///home/deck/Projects/menu/src/menu/extract_diet.py)，已在 `pyproject.toml` 注册：
   ```bash
   uv run extract-diet --mid 313924270 --dest diet
   ```
2. **智能推断与字幕联动**：
   脚本通过 Wbi 自动拉取视频真实台词字幕文本，并交由 OpenRouter 大语言模型（默认免费模型 `qwen/qwen3.8-27b:free`，支持备用模型自动降级与本地词库保底）进行精准提取：
   - 优先依据视频原台词中讲解的克数与配比提炼食材；
   - 提取 2-4 步精炼的烹饪操作步骤写入 `.cook` 食谱文件；
   - 本地自动缓存提取结果，避免重复请求。
   ```bash
   # 自动抓取字幕并进行 LLM 精准提取（默认行为）：
   uv run extract-diet --mid 313924270 --dest diet

   # 仅根据标题提取（不拉取字幕）：
   uv run extract-diet --no-subtitles

   # 禁用 LLM 回退到纯本地规则：
   uv run extract-diet --no-llm
   ```

---

## 三、 脚本与工具索引

- **字幕提取工具**：
  `.agents/skills/bilibili-recipe-extractor/scripts/fetch_video_recipe.py`
  - 参数：`BV号` 或 `URL`
  - 可选参数：`--json` 输出完整结构化 JSON；`--cookie` 自定义 cookie 路径。
- **命令行快速提取字幕（备选方案）**：
  ```bash
  yt-dlp --cookies /home/deck/Downloads/www.bilibili.com_cookies.txt \
         --write-sub --sub-lang "ai-zh,zh-CN" --skip-download \
         -o "/tmp/bili_sub" "https://www.bilibili.com/video/<BVID>"
  ```
