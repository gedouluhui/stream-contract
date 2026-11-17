# StreamContract

**A network chunk is not an SSE event. Test what your client assumes.**

Offline byte-boundary tests for streaming clients, with an **explicit expected result** and a replayable failing partition. No model calls, API keys, proxies or runtime dependencies.

```python
from streamcontract import audit, parse_sse, replay_chunks

wire = 'data: snow: 雪\r\n\r\n'.encode()
expected = [{"event": "message", "data": "snow: 雪", "id": ""}]
report = audit(wire, parse_sse, expected)
print(report["status"], report["exhaustive_single_cuts"])
# pass True
```

Replace `parse_sse` with your own adapter: a callable accepting an iterable of byte chunks and returning a finite JSON-compatible result. Supply an oracle from the specification or a hand-checked fixture, **not the client's own baseline output**. An always-empty client fails; being consistently wrong is not a pass.

## Install and run

From a checkout, in your own environment:

```sh
python -m pip install .
python -m streamcontract demo --json demo-report.json
python -m streamcontract check response.sse --json check-report.json
```

The demo runs a correct collector and an intentionally broken per-chunk UTF-8 decoder against the same synthetic stream. It exits successfully only if the first passes and the negative control fails. The negative control is not presented as a bug in a real SDK.

`check` validates a recorded stream using the narrow Chat text profile; it does **not** test your application's client. Use the Python `audit` API for that.

Existing outputs are protected; use `--force` deliberately. `check` exits 0 for a completed supported profile, 1 for incomplete/invalid/unsupported data, and 2 for input/output or CLI errors.

## Reproduce a failure

```python
failure = report["first_failure"]
if failure is not None:
    chunks = replay_chunks(wire, failure["chunk_sizes"])
    # Feed chunks to the same client adapter.
```

The report includes the exact chunk sizes, expected result, actual result or exception class, number of tested cases and whether all **single cuts** were exercised. It stops at the first failure.

Whole-stream and one-byte chunks are tested first, followed by single cuts and deterministic irregular partitions within the case budget. This is **not** exhaustive testing of the exponentially many possible partitions. Empty chunks, timing, backpressure, reconnects and socket cancellation are not modeled. A pass covers only the supplied fixture and tested partitions.

## What is supported?

- **SSE framing:** incremental UTF-8 replacement decoding, one initial BOM, CR/LF/CRLF, comments, multi-line data, empty data, persistent IDs and discarded incomplete trailing events, following [WHATWG event-stream interpretation](https://html.spec.whatwg.org/multipage/server-sent-events.html#event-stream-interpretation).
- **Chat text profile:** indexed text choices, role-only deltas, finish markers and optional empty-choices usage chunks. Missing `[DONE]` or unfinished choices is incomplete. Tool calls, refusals/other non-text deltas, named SSE events and Responses API streams are explicitly unsupported.
- **Independent oracle:** typed JSON comparison distinguishes `true` from `1` and rejects NaN/Infinity or non-JSON results. A local callable is trusted executable code, **not sandboxed**.

The text collector intentionally checks a small behavior contract, not every OpenAI schema field. It ignores unrelated top-level fields. Completion means the supported choices finished and the profile's end marker was observed, not that the connection was healthy or the model answer correct. SSE framing, vendor schema, model-output validity and transport failure are different questions.

Limits: parser 1 MiB total input and 65,536 characters per line/event by default; audit 65,536 input bytes and 512 cases by default (configurable 2..2,048). Result normalization is limited to 20,000 visited JSON nodes, depth 64 and 1 MiB of encoded JSON; oversized expected results are rejected and oversized client results become named failing cases. Inputs and adapters must terminate. Reports may contain input/output text; use synthetic fixtures before sharing them.

## A real, offline SDK comparison

If the OpenAI Python SDK is already installed:

```sh
python scripts/check_openai_decoder.py
```

This uses the SDK's **internal** `SSEDecoder.iter_bytes` interface and prints the exact version. In a local check of **openai 2.36.0**, a Unicode/CRLF fixture passed; the same valid SSE stream with a leading UTF-8 BOM returned no event instead of the expected event. The latter failed even as one whole chunk: it is a **framing compatibility difference**, not a boundary-dependent failure, not a claim about the live OpenAI service, and not an assertion about later SDK versions. The script does not require that the difference persist; a fixed SDK can pass both fixtures.

No API request, OpenAI client initialization or credential lookup is performed by the comparison. The reference events are explicit literals; no success conclusion is borrowed from another decoder.

## Development

```sh
python scripts/verify.py
python -m build --no-isolation
```

Tests cover known SSE cases at every single cut, byte-at-a-time Unicode, incomplete endings, wrong types, budgets, multiple choices, unsupported tools, always-empty clients, replay, CLI exit codes and overwrite protection. Python 3.10+ syntax; local execution verified on Python 3.12.3. Optional SDK comparison is separate from the dependency-free suite.

For full provider API acceptance, use established tools such as [Open Responses acceptance tests](https://www.openresponses.org/compliance). For routing/translation use the appropriate gateway or SDK. StreamContract focuses on a small, explainable client fixture and counterexample, not replacing those projects.

Contributions: provide a minimal public/synthetic wire fixture, independent expected semantics, client/version and reproducible command. Add a failing test first. Do not include real API keys, private prompts or user logs. Be respectful and keep discussion grounded in evidence.

## 中文简介

离线测试流式客户端是否错误依赖字节分块边界，输出可重放的失败切分。必须提供独立期望值，不能用“各次都一样”自证正确；首版只处理 SSE 和有限的 Chat 文本协议，不调用模型、不执行工具调用。

## License

MIT. Original code developed with AI assistance, backed by explicit counterexamples and review. Linked specifications/SDKs are references; no third-party implementation is bundled. No adoption, performance or full-protocol compliance claim is made.
