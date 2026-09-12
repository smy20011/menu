---
name: toddler-menu-cooklang
description: >-
  Standard workflow and formatting guidelines for generating toddler and children recipes
  in Cooklang (.cook) format from preschool menus. Focuses on required ingredients rather than cooking steps.
---

# 儿童/幼儿食谱 Cooklang 生成规范

本技能定义了将幼儿园/家庭儿童餐单转化为标准化 Cooklang (`.cook`) 食谱的规范与最佳实践。
核心原则：**只保留所需材料列表，省略具体做法与步骤文本**。

---

## 1. YAML Frontmatter 规范

每个食谱文件顶部必须包含 YAML Frontmatter（三破折号 `---` 包裹）：

```yaml
---
title: 菜品名称
tags:
  - 宝宝餐
  - 菜品类型
  - 口味
servings: 2
prep_time: 15 minutes
cook_time: 10 minutes
source: 来源说明（例如 2026 September Menu）
---
```

### 字段详解：
- **`title`**：**纯中文菜名**，不添加英文翻译。
- **`tags`**：
  - **必须包含**：`宝宝餐`（便于提取和分类筛选）。
  - **菜品类型（仅限以下四类之一）**：`主食`、`零食`、`肉菜`、`素菜`。
  - **口味**：`酸甜`、`咸鲜`、`清淡`、`微甜`、`咖喱` 等。
- **`servings`**：**纯数字**（默认写 `2`，代表 2 份幼儿份量，方便 Cooklang 工具自动缩放倍数）。
- **`prep_time`** & **`cook_time`**：用时估算。
- **`source`**：来源餐单说明。

---

## 2. 正文材料清单规范（不写做法）

- **只保留食材标注**：正文不写具体烹饪操作句子，直接逐行罗列食材及份量。
- 语法：`@食材{数量%单位}`，例如：
  ```cooklang
  @牛里脊肉{100%g}
  @玉米淀粉{1%茶匙}
  @酱油{0.5%茶匙}
  @水{2%大勺}
  @熟番茄{1%个}
  @鸡蛋{2%个}
  @食用油{1.5%茶匙}
  @水{50%ml}
  @白糖{0.5%茶匙}
  @食用盐{0.5%g}
  ```
- **食材通用化**：
  - 水一律标注为 `@水`。
  - 酱油统一标注为普通 `@酱油`。
- **存货扣减配置**：油、盐、糖、酱油等常备调料在 `config/pantry.conf` 中标记为 `"unlim"`，由 `cook` CLI 自动扣减。

---

## 3. 标准示例

```cooklang
---
title: 茄汁滑蛋牛肉
tags:
  - 宝宝餐
  - 肉菜
  - 酸甜
servings: 2
prep_time: 15 minutes
cook_time: 10 minutes
source: 2026 September Menu
---

@牛里脊肉{100%g}
@玉米淀粉{1%茶匙}
@酱油{0.5%茶匙}
@水{2%大勺}
@熟番茄{1%个}
@鸡蛋{2%个}
@食用油{1.5%茶匙}
@水{50%ml}
@白糖{0.5%茶匙}
@食用盐{0.5%g}
```
