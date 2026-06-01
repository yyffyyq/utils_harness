# Task 07 - Jinja2 模板文件编写

## 目标

编写 AGENTS.md 和计划文件的 Jinja2 模板，用于结构化内容的渲染输出。

## 依赖

- task-01（项目初始化）

## 交付物

- `templates/agents_md.j2` - AGENTS.md 模板
- `templates/plan.j2` - 单个任务计划文件模板
- `templates/plan_readme.j2` - 计划总览 README 模板

## 详细步骤

### 7.1 AGENTS.md 模板

文件：`templates/agents_md.j2`

```jinja2
# {{ project_name }} - {{ project_description }}

## 项目背景

{{ background }}

### 核心工作流
{% for step in workflow %}
{{ loop.index }}. {{ step }}
{% endfor %}

---

## 技术栈

| 类别 | 技术选型 | 说明 |
| ---- | -------- | ---- |
{% for tech in tech_stack %}
| {{ tech.category }} | {{ tech.name }} | {{ tech.description }} |
{% endfor %}

---

## 代码规范

{{ code_standards }}
```

### 7.2 任务计划模板

文件：`templates/plan.j2`

```jinja2
# {{ task_id }} - {{ task_title }}

## 目标

{{ description }}

## 依赖
{% for dep in dependencies %}
- {{ dep }}
{% endfor %}

## 交付物
{% for item in deliverables %}
- `{{ item }}`
{% endfor %}

## 详细步骤

{{ steps }}

## 验收标准
{% for criterion in acceptance_criteria %}
- [ ] {{ criterion }}
{% endfor %}
```

### 7.3 计划总览模板

文件：`templates/plan_readme.j2`

```jinja2
# {{ project_name }} 项目实施计划总览

{{ overview }}

## 任务清单

| 序号 | 任务文件 | 描述 | 预估复杂度 |
| ---- | -------- | ---- | ---------- |
{% for task in tasks %}
| {{ loop.index }} | [{{ task.title }}](./{{ task.filename }}) | {{ task.description }} | {{ task.complexity }} |
{% endfor %}

## 里程碑
{% for milestone in milestones %}
- **{{ milestone.name }}**：{{ milestone.description }}
{% endfor %}
```

## 验收标准

- [x] 所有模板文件位于 `templates/` 目录
- [x] 模板语法正确，Jinja2 可正常渲染
- [x] 变量命名清晰，与数据结构一致
- [x] 14 个单元测试全部通过
