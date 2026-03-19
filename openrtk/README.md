# openrtk

OpenCode plugin for [RTK](https://github.com/rtk-ai/rtk) (Rust Token Killer). Reduces LLM token consumption by 60-90% on common dev commands by transparently routing them through RTK's output compression.

A lightweight OpenCode plugin that intercepts shell commands and pipes them through RTK for automatic output compression. The model sees full output while RTK handles token reduction behind the scenes — no changes needed to prompts or workflow.

## Prerequisites

Install RTK:

```bash
cargo install rtk
```

## Installation

Add to your OpenCode config (`opencode.json` or `.opencode/config.json`):

```json
{
  "plugins": ["openrtk"]
}
```

Or copy `src/index.ts` directly into `.opencode/plugins/` for local use.

## How it works

The plugin hooks into OpenCode's `tool.execute.before` event and rewrites shell commands to go through RTK before execution. This is fully transparent to the model.

```
git status       ->  rtk git status       (72% savings)
cargo test       ->  rtk cargo test       (80% savings)
docker ps        ->  rtk docker ps        (65% savings)
```

### Supported commands

| Category | Commands |
|----------|----------|
| Git | status, diff, log, add, commit, push, pull, branch, fetch, stash, show |
| GitHub CLI | pr, issue, run, api, release |
| Rust | cargo test/build/clippy/check/install/fmt |
| File ops | cat, grep, rg, ls, tree, find, diff |
| JS/TS | vitest, npm test/run, tsc, eslint, prettier, playwright, prisma |
| Containers | docker (compose/ps/images/logs/run/build/exec), kubectl (get/logs/describe/apply) |
| Network | curl, wget |
| Python | pytest, ruff, pip, uv pip |
| Go | go test/build/vet, golangci-lint |
| Packages | pnpm list/ls/outdated |

### System prompt

Copy `opencode.md` into your project or user config to teach the model about `rtk gain` and other meta commands.

## Development

```bash
bun test          # run tests
```

## License

MIT
