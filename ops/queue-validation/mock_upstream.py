"""Stand-in for every outbound service during the queue validation.

The validation droplet holds no production credential and cannot reach any real
provider, so the stack talks to this one process instead:

* ``POST /v1/chat/completions``: an OpenAI-compatible chat endpoint (the GLM base
  URL). Tool calls and JSON-schema responses get a value synthesized from the
  schema; plain prompts get a canned answer chosen by keywords. Every request is
  answered after ``MOCK_LATENCY_SECONDS`` so phases take realistic time.
* ``POST /grok``: the GrokBot image webhook. It answers 202 and, after
  ``MOCK_IMAGE_SECONDS``, posts a generated PNG to the job's callback URL.
* ``GET /article/<n>``: an HTML page used as a topic source.

Every request is appended to ``MOCK_LOG`` (JSON lines: path, model, a prompt
digest, the answer kind) so the validation report can count calls.

Standard library only. Run: ``python mock_upstream.py`` (``MOCK_PORT``, default 8080).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import struct
import threading
import time
import urllib.request
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("MOCK_PORT", "8080"))
LATENCY = float(os.environ.get("MOCK_LATENCY_SECONDS", "3"))
IMAGE_SECONDS = float(os.environ.get("MOCK_IMAGE_SECONDS", "5"))
LOG_PATH = os.environ.get("MOCK_LOG", "/tmp/mock-upstream.jsonl")
IMAGE_SIDE = 1024
LOCK = threading.Lock()

LOREM = (
    "Agentes de IA estão mudando como equipes pequenas entregam software; "
    "o ponto é medir resultado, não promessa."
)
ARTICLE = (
    "<html><head><title>Field notes {n}</title></head><body><article>"
    "<h1>Field notes {n}</h1>"
    + "<p>{text}</p>" * 12
    + "</article></body></html>"
)


def log(entry: dict[str, object]) -> None:
    """Append one JSON line to the call log."""
    entry["at"] = time.time()
    with LOCK, open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def synthesize(schema: dict[str, object], depth: int = 0) -> object:
    """A value that satisfies ``schema`` (enough for the app's parsers)."""
    if depth > 8:
        return None
    for key in ("anyOf", "oneOf", "allOf"):
        options = schema.get(key)
        if isinstance(options, list) and options:
            usable = [o for o in options if isinstance(o, dict) and o.get("type") != "null"]
            return synthesize((usable or options)[0], depth + 1)
    if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]:
        return schema["enum"][0]
    if "const" in schema:
        return schema["const"]
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = next((k for k in kind if k != "null"), "string")
    if kind == "object" or "properties" in schema:
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            return {}
        return {
            name: synthesize(sub, depth + 1)
            for name, sub in properties.items()
            if isinstance(sub, dict)
        }
    if kind == "array":
        items = schema.get("items")
        count = max(int(schema.get("minItems", 0) or 0), 7 if depth <= 1 else 3)
        maximum = schema.get("maxItems")
        if isinstance(maximum, int):
            count = min(count, maximum)
        return [synthesize(items if isinstance(items, dict) else {}, depth + 1) for _ in range(count)]
    if kind == "integer":
        return int(schema.get("minimum", 0) or 0) + 8 if "maximum" not in schema else int(schema["maximum"])
    if kind == "number":
        return float(schema.get("maximum", 90) or 90)
    if kind == "boolean":
        return True
    return LOREM[: int(schema.get("maxLength", len(LOREM)) or len(LOREM))]


HOOK = "O que agentes de IA mudam no seu time"
NEWS_POINTS = (
    ("newspaper", "Lançamento novo", "Um modelo aberto chegou com custo menor.",
     "New release", "An open model arrived at a lower cost."),
    ("chart-column", "Custo menor", "O preço por tarefa caiu pela metade.",
     "Lower cost", "The price per task fell by half."),
    ("target", "Foco em código", "O alvo principal é revisão de código.",
     "Code focus", "The main target is code review."),
)
ACTIONS = (
    ("target", "Comece pequeno", "Escolha um fluxo e meça o tempo ganho.",
     "Start small", "Pick one flow and measure the time saved."),
    ("shield-check", "Revise sempre", "Mantenha uma pessoa aprovando cada mudança.",
     "Always review", "Keep a person approving every change."),
    ("chart-column", "Meça custos", "Acompanhe o gasto mensal desde o primeiro dia.",
     "Track costs", "Watch monthly spend from day one."),
)
IMPACT = {
    3: ("Revisão de código fica mais rápida",
        "Agentes revisam pull requests inteiros e apontam falhas antes do merge, poupando horas da equipe.",
        "Code review gets faster",
        "Agents review whole pull requests and flag bugs before the merge, saving the team hours."),
    4: ("Testes passam a ser escritos antes",
        "Ferramentas geram casos de teste a partir das histórias, o que reduz retrabalho no fim do ciclo.",
        "Tests get written earlier",
        "Tools generate test cases from user stories, which cuts rework at the end of each cycle."),
    5: ("Custos de infraestrutura pedem atenção",
        "Rodar modelos grandes consome orçamento, então vale medir o gasto mensal antes de escalar.",
        "Infrastructure costs need attention",
        "Running large models eats budget, so measure monthly spend before you scale."),
}
OUTLINE_ROLES = ("hook", "news", "impact", "impact", "impact", "verdict", "cta")
OUTLINE_TITLES = (
    HOOK, "O que aconteceu nesta semana", IMPACT[3][0], IMPACT[4][0], IMPACT[5][0],
    "O veredito para equipes pequenas", "Siga para mais análises",
)


def _items(rows: tuple[tuple[str, str, str, str, str], ...], lang: str) -> list[dict[str, str]]:
    if lang == "pt":
        return [{"icon_name": r[0], "title": r[1], "body": r[2]} for r in rows]
    return [{"icon_name": r[0], "title": r[3], "body": r[4]} for r in rows]


def slide_locales(index: int, role: str, hook: str, scene: str) -> dict[str, object]:
    """PT and EN copy for one slide that passes the presentation rules."""
    if role == "hook":
        pt = {"heading": hook, "subtitle": "Um panorama curto com dados reais e limites claros."}
        en = {"heading": "What AI agents change for your team",
              "subtitle": "A short overview with real numbers and clear limits."}
    elif role == "news":
        pt = {"heading": "O que aconteceu nesta semana", "summary_points": _items(NEWS_POINTS, "pt")}
        en = {"heading": "What happened this week", "summary_points": _items(NEWS_POINTS, "en")}
    elif role == "verdict":
        pt = {"heading": "O veredito para equipes pequenas", "body": "Vale testar com metas claras.",
              "actions": _items(ACTIONS, "pt")}
        en = {"heading": "The verdict for small teams", "body": "Worth testing with clear goals.",
              "actions": _items(ACTIONS, "en")}
    elif role == "cta":
        pt = {"heading": "Siga para mais análises", "body": "Salve este post e compartilhe com seu time."}
        en = {"heading": "Follow for more analysis", "body": "Save this post and share it with your team."}
    else:
        heading_pt, body_pt, heading_en, body_en = IMPACT.get(index, IMPACT[3])
        pt = {"heading": heading_pt, "body": body_pt, "features": []}
        en = {"heading": heading_en, "body": body_en, "features": []}
    return {"pt": pt, "en": en,
            "image_prompt": f"A developer at a neon terminal watching code streams, scene {scene}"}


def draft(prompt: str) -> str:
    """One slide draft whose text is the nested PT/EN blob."""
    index = int(_match(r"Slide index:\s*(\d+)", prompt) or 1)
    role = (_match(r"Slide role:\s*([a-z_]+)", prompt) or "impact").lower()
    hook = _match(r'The heading is the hook, EXACTLY: "([^"]+)"', prompt) or HOOK
    return json.dumps({
        "draft_text": json.dumps(
            slide_locales(index, role, hook, hashlib.sha256(prompt.encode()).hexdigest()[:10]),
            ensure_ascii=False,
        ),
        "confidence_score": 0.9,
        "sources_used": [],
        "icon_name": "brain",
        "long_form_notes": "Contexto adicional sobre o tema com exemplos práticos e números.",
    }, ensure_ascii=False)


def translation(prompt: str) -> str:
    """English copy with the same item counts as the PT input."""
    raw = prompt.split("Input slides (PT):", 1)[-1]
    start, end = raw.find("["), raw.rfind("]")
    try:
        slides = json.loads(raw[start:end + 1]) if start >= 0 else []
    except ValueError:
        slides = []
    out = []
    for slide in slides if isinstance(slides, list) else []:
        index = int(slide.get("slide_index", len(out) + 1)) if isinstance(slide, dict) else len(out) + 1
        item: dict[str, object] = {"slide_index": index, "heading": f"Slide {index} in English",
                                   "body": f"English copy for slide {index}.",
                                   "long_form_notes": "More context with practical examples."}
        for key in ("tldr_strip", "features", "summary_points", "actions"):
            value = slide.get(key) if isinstance(slide, dict) else None
            if isinstance(value, list):
                item[key] = [{"title": f"Point {n + 1}", "body": f"Detail number {n + 1}."} for n in range(len(value))]
            elif isinstance(value, str):
                item[key] = "Short summary."
        out.append(item)
    return json.dumps({"slides_en": out})


def _match(pattern: str, text: str) -> str | None:
    found = re.search(pattern, text)
    return found.group(1) if found else None


SCORE = {"tone_match": 90, "sentence_structure_match": 90, "opinion_strength": 90,
         "originality": 90, "human_authenticity": 90, "overall": 90, "suggestions": []}


def canned(prompt: str) -> str:
    """The answer for one of the pipeline's prompts, recognised by its opening."""
    if prompt.startswith("Extract key points"):
        return json.dumps({"key_points": ["Agentes reduzem tarefas repetitivas.",
                                          "Equipes medem ganho de tempo real."],
                           "summary": "Agentes de IA cortam trabalho repetitivo em equipes pequenas."},
                          ensure_ascii=False)
    if 'Planeje um carrossel do Instagram "Radar IA"' in prompt:
        tag = hashlib.sha256(prompt.encode()).hexdigest()[:8]
        return json.dumps([{"slide_index": i + 1, "role": r, "title": t,
                            "key_points": [f"Ponto principal da pauta {tag}."]}
                           for i, (r, t) in enumerate(zip(OUTLINE_ROLES, OUTLINE_TITLES))],
                          ensure_ascii=False)
    if prompt.startswith("Você escreve o slide 1"):
        return json.dumps({"candidates": [{"formula": "impacto_pra_voce", "text": HOOK}]}, ensure_ascii=False)
    if "Draft carousel slide copy for slide" in prompt:
        return draft(prompt)
    if "Score this content on how well it matches the persona above." in prompt:
        return json.dumps(SCORE)
    if prompt.startswith("You are writing as ") and "CONTENT TO REWRITE:\n" in prompt:
        return prompt.split("CONTENT TO REWRITE:\n", 1)[1]
    if prompt.startswith("You are the quality reviewer"):
        ids = re.findall(r"- id: ([^ |]+) \|", prompt)
        return json.dumps({"criteria": [{"id": i, "score": 90, "feedback": "Bom."} for i in ids],
                           "feedback": "Bom."})
    if prompt.startswith("Translate carousel slide copy from Portuguese to English."):
        return translation(prompt)
    if prompt.startswith("Escreva a legenda"):
        return "Agentes de IA já mudam a rotina de times pequenos. Salve para consultar depois."
    if prompt.startswith("You are writing a LinkedIn post"):
        return "AI agents are changing how small teams ship software. Measure results first."
    return LOREM


def _prompt(body: dict[str, object]) -> str:
    """The first message's text: a JSON-repair turn is answered like the original."""
    messages = [m for m in body.get("messages") or [] if isinstance(m, dict)]
    return str(messages[0].get("content", "")) if messages else ""


def chat_answer(body: dict[str, object]) -> tuple[dict[str, object], str]:
    """The completion message and a label of what was answered."""
    prompt = _prompt(body)
    tools = body.get("tools")
    if isinstance(tools, list) and tools:
        function = tools[0].get("function", {})
        arguments = synthesize(function.get("parameters", {}))
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_mock",
                    "type": "function",
                    "function": {
                        "name": function.get("name", "tool"),
                        "arguments": json.dumps(arguments),
                    },
                }
            ],
        }
        return message, f"tool:{function.get('name')}"
    response_format = body.get("response_format")
    if isinstance(response_format, dict) and response_format.get("type") == "json_schema":
        schema = response_format.get("json_schema", {}).get("schema", {})
        return {"role": "assistant", "content": json.dumps(synthesize(schema))}, "schema"
    return {"role": "assistant", "content": canned(prompt)}, "canned"


def png(side: int) -> bytes:
    """A solid-colour PNG of ``side`` x ``side`` pixels."""
    row = b"\x00" + bytes((40, 90, 160)) * side
    raw = zlib.compress(row * side)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", side, side, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


def deliver_image(job: dict[str, object]) -> None:
    """Post the generated image to the job's callback, like the Grok Bot."""
    time.sleep(IMAGE_SECONDS)
    body = json.dumps(
        {"created": int(time.time()), "data": [{"b64_json": base64.b64encode(png(IMAGE_SIDE)).decode()}]}
    ).encode()
    request = urllib.request.Request(
        str(job["callback_url"]),
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Image-Bridge-Token": str(job["callback_token"]),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            log({"path": "callback", "status": response.status, "job": job.get("job_id")})
    except Exception as exc:
        log({"path": "callback", "error": type(exc).__name__, "job": job.get("job_id")})


class Handler(BaseHTTPRequestHandler):
    """Routes the three surfaces."""

    def log_message(self, *_args: object) -> None:
        """Quiet: the JSON-lines log is the record."""

    def _json(self, status: int, payload: dict[str, object]) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _stream(self, message: dict[str, object], model: str) -> None:
        """The same answer as server-sent chunks, ending with ``[DONE]``."""
        delta: dict[str, object] = {"role": "assistant"}
        if message.get("tool_calls"):
            calls = message["tool_calls"]
            delta["tool_calls"] = [dict(call, index=index) for index, call in enumerate(calls)]
        else:
            delta["content"] = message.get("content") or ""
        chunks = [
            {"index": 0, "delta": delta, "finish_reason": None},
            {"index": 0, "delta": {}, "finish_reason": "stop"},
        ]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for choice in chunks:
            event = {
                "id": "chatcmpl-mock",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [choice],
            }
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def do_GET(self) -> None:
        """Article pages and a health probe."""
        if self.path.startswith("/article/"):
            number = self.path.rsplit("/", 1)[-1]
            data = ARTICLE.format(n=number, text=LOREM).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            log({"path": "article", "n": number})
            return
        self._json(200, {"ok": True})

    def do_POST(self) -> None:
        """Chat completions and the image webhook."""
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path.endswith("/grok"):
            threading.Thread(target=deliver_image, args=(body,), daemon=True).start()
            log({"path": "grok", "job": body.get("job_id")})
            self._json(202, {"accepted": True})
            return
        if self.path.endswith("/chat/completions"):
            time.sleep(LATENCY)
            message, kind = chat_answer(body)
            digest = hashlib.sha256(json.dumps(body.get("messages", [])).encode()).hexdigest()[:12]
            log(
                {
                    "path": "chat",
                    "model": body.get("model"),
                    "kind": kind,
                    "digest": digest,
                    "head": _prompt(body)[:160],
                }
            )
            if body.get("stream"):
                self._stream(message, str(body.get("model", "mock")))
                return
            self._json(
                200,
                {
                    "id": "chatcmpl-mock",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": body.get("model", "mock"),
                    "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
                },
            )
            return
        self._json(404, {"error": {"message": "unknown path"}})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
