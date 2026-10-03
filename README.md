# skills

4 个可独立安装、按需使用的开发 skills。选择一个或任意多个即可；每个包都包含自己的入口、脚本、引用和许可证，不需要安装其他 skill。

| Skill | Version | 用途与依赖 |
|---|---|---|
| [conventional-commit-batcher](conventional-commit-batcher/SKILL.md) | 4.0.0 | 将独立变更拆成 Conventional Commits。需要 Git；脚本需 Python 3.10+，也有手工检查降级路径。 |
| [repository-quality-gate-fixer](repository-quality-gate-fixer/SKILL.md) | 0.8.0 | 审核或修复仓库/PR 质量门禁。可选探测脚本需 Python 3.10+；实际验证使用项目自己的工具链。 |
| [sonarcloud-link-inspector](sonarcloud-link-inspector/SKILL.md) | 1.1.0 | 只读解释 EU/US SonarCloud 链接。需要 Python 3.10+、requests、网络；私有数据需要环境变量中的授权 token。 |
| [dev-jev](dev-jev/SKILL.md) | 0.2.0 | 使用可用 Jev 工具进行有界语义判断。提供方可选；缺失时继续主任务。遥测需 Python 3.10+，仅使用标准库。 |

安装或加载 skill 不代表授权编辑、提交、推送或修改远端状态。多个 skills 可以按任务需要协作，不存在强制调用链。

## 安装一个或几个

需要 Node.js/npm。当前验证基线是 `skills 1.7.0`，要求 Node.js **22.20.0+**；运行 `npx skills@latest --version` 查看实际 CLI 版本。

```bash
# 查看可选 skills，不安装
npx skills@latest add cnkang/skills --list

# 交互选择 skill、agent 和安装方式；默认项目安装
npx skills@latest add cnkang/skills

# 只为当前项目安装一个 skill
npx skills@latest add cnkang/skills --skill conventional-commit-batcher -a codex

# 只为当前项目安装指定的两个 skills
npx skills@latest add cnkang/skills --skill repository-quality-gate-fixer sonarcloud-link-inspector -a codex

# 全局安装一个 skill
npx skills@latest add cnkang/skills --skill dev-jev -a codex -g
```

`-a` 选择使用的 agent，不需要安装对应的专用适配包。可用 ID 包括：`codex`、`claude-code`、`opencode`、`cursor`、`gemini-cli`、`kiro-cli`、`kimi-code-cli`、`qwen-code`、`hermes-agent`。用多个 ID 可以面向多个宿主安装。

默认安装方式使用共享副本和符号链接；需要独立复制或文件系统不支持链接时加 `--copy`。当前 CLI 对使用 `.agents/skills` 的通用宿主共享项目或用户级目录，实际位置以 CLI 输出为准；其他宿主使用对应的安装目录。安装成功只证明文件可用，宿主发现和行为还需要实际验证。

OpenCode 支持全局安装。PromptScript 是另一个 agent，只支持项目安装，不能将它的限制归到 OpenCode；其他宿主限制参见 [CLI supported agents](https://github.com/vercel-labs/skills#supported-agents)。

CLI 安装不会安装 Python 依赖、Jev 提供方或旧命令/hook。SonarCloud 的依赖在实际使用的项目虚拟环境中安装：

```bash
python3 -m pip install -r <installed-sonarcloud-skill-dir>/requirements.txt
```

## 单独使用

在支持的宿主中引用安装的 skill，例如：

```text
Use $conventional-commit-batcher to split these changes into logical commits and commit them. Do not push.
Use $repository-quality-gate-fixer to audit this PR. Do not edit, commit, or push.
Use $sonarcloud-link-inspector to explain this URL without editing code or changing remote state.
Use $dev-jev for one bounded judgment if compatible tools are available, then continue the task normally.
```

每条请求可以独立使用，不要求安装其余 skills。想先看提交计划时明确要求 plan only；需要修复、提交或推送时明确该动作。Jev 的默认 `shadow` 模式不能影响实际行动，缺少提供方也不阻塞任务。

支持 `skills use` 的 CLI 还可以临时加载一个 skill：

```bash
# 输出包含临时资源路径的提示词，不持久安装，也不启动 agent
npx skills@latest use cnkang/skills --skill sonarcloud-link-inspector

# 将生成的提示词交给支持的 agent，并启动该宿主
npx skills@latest use cnkang/skills --skill conventional-commit-batcher --agent codex
```

启动宿主需要该 agent 已安装，并遵循它自己的权限配置。`use` 不自动添加其他 skills。[CLI use 说明](https://github.com/vercel-labs/skills#use-a-skill-without-installing)

## 只更新选择的 skills

```bash
# 从安装目标项目运行：只更新一个 skill
npx skills@latest update conventional-commit-batcher -p

# 全局只更新指定的两个 skills
npx skills@latest update repository-quality-gate-fixer sonarcloud-link-inspector -g
```

在自动化中可加 `-y`。使用显式名称与 `-p`/`-g`，避免更新无关技能或猜测安装范围。无名称的 `update` 会更新所选范围内的全部 skills。

`skills@latest` 选择最新发布的 CLI；skill 内容则按已记录的来源、路径和 ref 更新。`metadata.version` 是发布说明，不是 CLI 的版本比较依据。脚本或 reference 的变化也能触发更新。固定 tag/ref 的安装仍跟随该 ref，不会自动跳到默认分支。[上游更新实现](https://github.com/vercel-labs/skills/blob/main/src/update.ts)

更新可能替换整个已安装包；先备份有意修改的内容。CLI 可能重新选择共享链接安装方式，因此使用 `--copy` 的环境应核实更新后的安装形态，必要时以原命令加 `--copy` 重新安装。包内可选适配模板更新不会更新已部署到其他目录的命令或 hook。

## 迁移与进阶安装

- 从旧 `cnkang/conventional-commit-batcher` 来源迁移：对该 skill 重新执行 `add cnkang/skills --skill conventional-commit-batcher`，保留所需的 agent 和安装范围；普通 `update` 不会改变来源。
- 手工复制的包、旧 lock 缺少路径/来源或更新无法识别时：备份自定义内容，用 `add` 重新安装对应 skill 建立来源记录。不要手工改版本字段来模拟更新。
- 提交拆分 **v4** 移除了隐藏目录中的旧入口及自动识别的包内 AGENTS/CLAUDE 文件。可选命令、专用 agent、steering 和 hook 现为模板，迁移参见 [adapter setup](conventional-commit-batcher/references/adapter-setup.md)。不要自动删除外部自定义配置。
- Jev 的旧遥测参数和日志仍可读；中立路径与 Hermes 可选配置参见 [dev-jev](dev-jev/SKILL.md)。

只有确实需要全部 skills 时使用：

```bash
npx skills@latest add cnkang/skills --skill '*' -a codex
```

保留完整 skill 文件夹；单独复制 `SKILL.md` 会遗漏脚本和引用。手工安装不获得 CLI 来源追踪能力。

## 开发、验证与发布

```bash
python3 -m venv .venv
# 激活项目虚拟环境后：
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate_skills.py
python3 -m pytest -q conventional-commit-batcher/scripts repository-quality-gate-fixer/tests sonarcloud-link-inspector/tests dev-jev/scripts/test_dev_jev.py tests
python3 scripts/test_distribution.py --cli-version 1.7.0
```

分发测试使用隔离的 HOME、配置和项目目录，验证全部 15 种非空选择组合、9 个宿主的项目/全局与链接/复制安装、临时使用及选择性更新。更新来源由本地 Git fixture 提供，不访问真实私有仓库或 token。脚本失败不等于真实宿主不可用；需区分打包缺陷和上游 CLI 行为变化。

CI 同时检查固定基线和最新 CLI。真实 agent 授权与调用行为的验收参见 [behavior scenarios](docs/behavior-scenarios.md)；结构检查不能证明模型行为。[发布与回滚](docs/releasing.md)说明默认分支更新渠道、版本、标签与迁移流程。

## License

[MIT](LICENSE)。每个独立 skill 包都包含许可证副本。
