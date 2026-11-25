# game-audio-free

[English](README.en.md) · MIT

一个收集免费游戏音频工具的 Agent Skill，适用于 Codex 和 Claude Code。收录范围包括本地免费合成、可免费使用的素材，以及提供免费额度的云端模型。

## 复制这段话给 Agent

在 Codex 或 Claude Code 里打开你的游戏项目，把下面这段话发给它。

```text
请从 https://github.com/YakirLove/game-audio-free 把这个 Skill 安装到当前游戏项目。
然后用它做一个投币音效，保存到 assets/audio/，把 WAV 文件路径发给我试听。
```

投币音效在本地生成，无需 API 密钥。你也可以把「投币音效」换成游戏里需要的其他声音。

<details>
<summary>手动安装与终端示例</summary>

在游戏项目根目录运行以下命令，并在安装器中选择你的 Agent。基础音效需要 Python 3.10+、Node.js 18+ 和 npm。

```sh
npx skills add YakirLove/game-audio-free
```

下面用终端为抓娃娃机生成投币和抓取成功两个音效。示例使用 Codex 的项目级安装路径，Claude Code 可使用 `.claude/skills/game-audio-free/scripts`。

```sh
S=".agents/skills/game-audio-free/scripts"
python3 "$S/game_audio_free.py" synth claw.coin.insert coin
python3 "$S/game_audio_free.py" synth claw.grab.success victory
```

打开 `assets/audio/claw-coin-insert.wav` 就能听到第一枚游戏币。成功提示保存在 `claw-grab-success.wav`。这两条命令首次运行时按需获取 plinkfx，后续遇到相同请求会复用已校验的文件。

</details>

## 五类声音

| 游戏需要 | 工具 | 需要 Google 密钥？ | 使用条件 |
| --- | --- | --- | --- |
| 按钮、投币、跳跃、胜利提示 | [plinkfx](https://github.com/maximilianfeix/plinkfx) | 无需 | 本地合成 WAV，预设音效采用 CC0 |
| 脚步、齿轮、碰撞、雨声 | [sfx-sources](https://github.com/sxhzju/sfx) | 无需 | 联网检索，按素材原格式保存；压缩音频验证需要 ffmpeg |
| 独特机械声、魔法或怪物音效 | [Stable Audio 3 Small-SFX](https://github.com/Stability-AI/stable-audio-3) | 无需 | 按需安装本地 CLI、取得模型访问并下载权重；Small 支持 CPU，商用须符合[免费社区许可条件](https://stability.ai/license) |
| 探索、战斗、菜单背景音乐 | [Google Lyria RealTime](https://ai.google.dev/gemini-api/docs/realtime-music-generation) | **需要** | 云端生成器乐，按目标时长写入立体声 WAV |
| NPC 台词、新手引导、倒计时播报 | [Gemini TTS](https://ai.google.dev/gemini-api/docs/speech-generation) | **需要** | 按原文、语言、音色和情绪生成配音 WAV |

## 如何获取 Google API Key

**背景音乐和角色配音共用一把 Gemini API 密钥。** 官方获取地址为 [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)。

1. 用 Google 账号登录。如果页面已经列出默认项目的密钥，可以直接复制。
2. 如果需要新密钥，点击 **Create API key（创建 API 密钥）**，选择项目，创建后复制密钥。已有 Google Cloud 项目却找不到时，先到 **Dashboard → Projects → Import projects** 导入，再回到密钥页。仅使用免费额度时，选择免费层项目。[Google 官方操作指南](https://ai.google.dev/gemini-api/docs/api-key)
3. 在本机把密钥设为环境变量 `GEMINI_API_KEY`。macOS 或 Linux 用户可以在 Bash 或 Zsh 终端运行下面这行，粘贴密钥后按回车（输入不会显示），再从同一终端启动 Agent。Windows 用户可在系统的「用户环境变量」中新建同名变量，保存后重新打开 Agent。

```sh
read -rs GEMINI_API_KEY && export GEMINI_API_KEY
```

两个 Google 脚本通过 `uv` 按需准备 Python 3.11+ 和 SDK。Lyria RealTime 在实验期免费且有配额，政策可能调整。默认 Flash TTS 模型有免费层，启用结算的项目可能计费。配额耗尽或模型无权限时，脚本报告原因，已完成的音频仍可使用。[使用命令和模型准备](skills/game-audio-free/references/providers.md) · [Google 定价](https://ai.google.dev/gemini-api/docs/pricing) · [Lyria 实验说明](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_LyriaRealTime.ipynb)

## 在游戏里读取结果

`assets/audio/audio-manifest.json` 的 `events` 以游戏事件名为键。用 `events["claw.coin.insert"].file` 取相对于清单的文件名，用 `tool` 查看制作工具。每条命令也会打印包含绝对路径的 JSON。用 `--out-dir` 可以更换整个输出目录。

下载素材会记录 `source_url`、`source_id`、`license` 和所需的 `credit`。传入 `--loop` 会把 `loop_requested` 设为真；实际确认首尾接得上之后，才用 `confirm-loop` 把该文件的 `loop_verified` 设为真。

## 首版验证与许可

在临时游戏项目中实际生成并解码了投币、胜利提示和 Mixkit 的齿轮锁定声，也检查了重复运行时的文件复用。Lyria 和 Gemini TTS 使用模拟服务响应验证音频与错误处理。Stable Audio 验证了命令参数及缺少 CLI 的处理，真实推理需要模型访问。

本仓库编写的 Skill 和脚本采用 [MIT 许可](LICENSE)。音频素材、上游工具和模型分别遵循其发布者的条款。
