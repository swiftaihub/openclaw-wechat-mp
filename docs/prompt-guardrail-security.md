# Prompt & Guardrail Security Architecture

## 项目结构建议

```text
.
|-- app/
|   |-- main.py
|   |-- wechat.py
|   |-- llm_core.py
|   |-- ollama_client.py
|   |-- prompt_runtime.py      # 动态加载 prompt/guardrail 配置
|   `-- guardrail.py           # 输入/输出约束与后处理
|-- config/
|   |-- prompt.example.yaml    # 公开模板（无敏感内容）
|   `-- prompt.private.yaml    # 本地私有文件（git ignore）
|-- docs/
|   `-- prompt-guardrail-security.md
|-- tests/
|   |-- test_prompt_runtime.py
|   `-- test_guardrail.py
|-- .gitignore
|-- .dockerignore
|-- docker-compose.yml
`-- README.md
```

## Prompt/Config 分离策略

- 代码中不保存业务敏感 prompt 内容，只保存加载器和模板渲染逻辑。
- 使用 `config/prompt.private.yaml` 作为私有配置，文件不进入 Git。
- 仓库仅保留 `config/prompt.example.yaml` 作为结构模板。
- 运行时优先读取 `PROMPT_CONFIG_PATH`，未设置时按顺序查找：
  1. `config/prompt.private.yaml`
  2. `config/prompt.example.yaml`
- 推荐将生产环境私有配置挂载到只读路径（如 `/run/secrets/` 或 `/srv/config/`）。

## Guardrail 设计建议

- Guardrail 作为独立模块，避免散落在业务代码中。
- 建议至少包含四类能力：
  1. 输入拦截：命中禁止意图时直接返回安全答复。
  2. 输出拦截：模型输出触发高风险模式时阻断返回。
  3. 输出脱敏：对密钥/手机号/证件号等模式进行替换。
  4. 输出裁剪：限制字数，避免超长回复。
- Guardrail 配置由 YAML 驱动，规则可迭代，不需要改应用代码。

## 运行时加载/注入机制

- `app/prompt_runtime.py` 在启动期加载配置并校验 schema。
- `app/llm_core.py` 请求流程：
  1. `check_input` 处理用户输入。
  2. 读取 profile 的 `system_prompt` 和 `user_prompt_template`。
  3. 注入动态变量（如 `user_id`、`channel`、`user_text`）。
  4. 调用 `ollama_client` 发起模型请求。
  5. `sanitize_output` 进行输出拦截、脱敏、裁剪。
- 模块职责边界：
  - `ollama_client.py` 只负责模型 API 调用。
  - `prompt_runtime.py` 只负责配置与模板。
  - `guardrail.py` 只负责策略执行。

## CI/CD 与版本控制保护策略

- `.gitignore` 必须包含：
  - `config/*.private.yaml`
  - `config/private/`
- `.dockerignore` 必须包含：
  - `.env`
  - `config/*.private.yaml`
  - `cloudflared/credentials.json`
- CI 检查建议：
  1. Secret Scan：扫描 prompt/private/secrets 误提交。
  2. Policy Check：阻止提交 `*.private.yaml`、`.env`、凭据文件。
  3. Unit Test：校验配置加载与 guardrail 行为。
- 分支策略建议：
  - 私有 prompt 仅存在本地、私有配置中心或 Secret Manager。
  - 公共分支只允许模板和规则结构变更。

## 示例代码片段（无敏感 prompt）

```python
# app/llm_core.py (simplified)
runtime = get_prompt_runtime()
guardrail = GuardrailEngine(runtime.guardrail_settings)

input_result = guardrail.check_input(user_text)
if input_result.blocked:
    return input_result.text

system_prompt = runtime.system_prompt("wechat")
user_prompt = runtime.render_user_prompt(
    profile="wechat",
    user_text=input_result.text,
    user_id=user_id,
    context={"channel": "wechat_mp"},
)

raw = await ollama_chat(system_prompt=system_prompt, user_prompt=user_prompt)
return guardrail.sanitize_output(raw)
```

```yaml
# config/prompt.example.yaml (simplified)
default_profile: wechat
profiles:
  wechat:
    system_prompt: |
      <SYSTEM_PROMPT_PLACEHOLDER>
    user_prompt_template: |
      [User Message]
      {user_text}
guardrail:
  blocked_input_patterns:
    - "(?i)<INPUT_BLOCK_PATTERN>"
```
