---
name: parallel-imagegen
description: >-
  Run multiple built-in Codex image_gen calls concurrently by assigning each
  output to an independent codex exec process, with up to 12 active workers,
  isolated retries, and thread-evidence verification. Use for two or more
  independent raster generation or editing outputs, even when prompts,
  references, subjects, or styles differ. Do not use for one output,
  unresolved sequential dependencies, or an explicitly selected Images API /
  imagegen CLI workflow. 通过为每个输出启动独立 Codex 进程，并发生成或编辑两个
  及以上互不依赖的位图；支持最多 12 个 Worker、失败隔离重试和线程证据验证。
  不用于单张输出、尚未解决的前后依赖，或用户明确选择 Images API / imagegen CLI
  的场景。
---

# 并行图片生成

本 Skill 只解决一个问题：让多个独立的内置 `image_gen` 调用真正从不同 `codex exec` 进程并发运行。图片该如何生成或编辑，继续由 `imagegen` Skill 决定。

## 执行约束

- 每个请求输出对应一个独立 Codex 进程；每个进程只调用一次 `image_gen`。
- 1–12 个任务同时启动；超过 12 个时维持最多 12 个活动 Worker 滚动补位。
- 禁止在同一个执行器中用 `Promise.all`、`Promise.allSettled` 或类似方式并发调用多个 `imagegen`。这不属于独立进程并发。
- 同一清单中的任务必须能够独立完成。若某任务依赖另一任务的结果，先完成并验证前者，再单独启动下一批。
- 使用内置 `image_gen`，不要在 Worker 中切换到 API、SDK 或 `imagegen` CLI。

`imagegen` CLI 的 `generate-batch` 是另一套实现：它通过 Python SDK 直接并发调用 OpenAI Images API，需要 `OPENAI_API_KEY`。如果用户明确选择 CLI/API，就改用 `imagegen` 的对应流程，不使用本调度器。

## 准备任务

将用户请求拆成独立任务。提示词可以完全不同，也可以有重复内容；不要主动假设它们需要共享风格、主题或视觉系统。

仅当多项任务确实重复相同内容时，才使用可选的 `shared_prompt` 或 `shared_references` 减少重复。每项任务仍可拥有自己的提示词和参考图。

本地参考图必须使用真实存在的绝对路径。这是因为子进程不继承父任务的对话附件或当前目录上下文；每个 Worker 需要自行用 `view_image` 读取本地输入，再把路径传给 `image_gen`。`role` 使用自由文本描述图片用途，不限定分类。

## 任务清单

```json
{
  "shared_prompt": "可选：确实适用于所有任务的重复要求",
  "shared_references": [
    {"path": "/absolute/common.png", "role": "可选的共享参考说明"}
  ],
  "jobs": [
    {
      "id": "job-01",
      "intent": "generate",
      "prompt": "这个输出的完整要求",
      "references": [],
      "output_name": "job-01.png"
    },
    {
      "id": "job-02",
      "intent": "edit",
      "prompt": "如何修改输入图片，以及需要保持什么",
      "references": [
        {"path": "/absolute/input.png", "role": "需要编辑的输入图片"}
      ],
      "output_name": "job-02.png"
    }
  ]
}
```

- `intent` 只接受 `generate` 或 `edit`。
- `edit` 至少需要一张输入图片。
- `shared_prompt` 和 `shared_references` 均为可选；不要为了使用它们而改写用户需求。
- `output_name` 只控制复制后的首选文件名，不要求模型生成特定格式。

## 启动

macOS、Linux、WSL：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/parallel-imagegen"
python3 "$SKILL_DIR/scripts/dispatch.py" \
  --manifest /absolute/path/jobs.json \
  --workdir /absolute/task-root \
  --run-dir /absolute/task-root/tmp/parallel-imagegen/run-name \
  --copy-images-to /absolute/output-directory \
  --concurrency 12 \
  --retries 2
```

Windows PowerShell：

```powershell
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$SkillDir = Join-Path $CodexHome "skills\parallel-imagegen"
python "$SkillDir\scripts\dispatch.py" `
  --manifest "C:\absolute\path\jobs.json" `
  --workdir "C:\absolute\task-root" `
  --run-dir "C:\absolute\task-root\tmp\parallel-imagegen\run-name" `
  --copy-images-to "C:\absolute\output-directory" `
  --concurrency 12 `
  --retries 2
```

要求：Python 3.9+、已认证的 `codex` CLI，以及可用的内置图片生成功能。调度器只使用 Python 标准库。

## 等待、失败与中断

- 调度器健康运行时，只轮询它的会话，间隔不超过 60 秒。
- 运行中不要扫描目录、进程、半成品或日志。
- 退出后立即读取 `summary.json`；仅在失败或超时时检查对应日志。
- 调度器只在新的进程中重试失败任务，并逐轮降低重试并发；已验证任务不会重跑。
- 中断调度器时，同时终止活动 Worker。没有成功摘要证据的文件视为未验证。

## 验证与交付

以 `summary.json` 为准：

1. `job_count` 必须等于请求输出数；只有 `failed: 0` 才能声明全部成功。
2. `successful_threads_distinct` 必须为 `true`，每个成功输出必须来自独立线程。
3. 每个任务必须通过 `telemetry` 或 `final-json-thread-output` 验证，且最终 `image_path` 存在并非空。
4. `max_active_workers` 只证明客户端 Worker 有重叠，不代表服务端提供了相同数量的生成槽位。

展示所有成功输出；如果有失败，准确报告部分成功。视觉验收、编辑正确性、透明图、蒙版和其他图片语义仍按 `imagegen` Skill 处理，不在本调度器中重复定义。
