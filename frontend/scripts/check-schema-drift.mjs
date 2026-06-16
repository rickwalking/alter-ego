#!/usr/bin/env node
/**
 * OpenAPI <-> Zod schema-drift check (AE-0141).
 *
 * Compares a curated set of the frontend's domain Zod response/request schemas
 * (src/schemas/*.ts) against the committed backend OpenAPI artifact
 * (docs/architecture/openapi.json, produced by
 * backend/scripts/export_openapi.py). It reports DRIFT:
 *
 *   - fields the frontend validates that the API schema no longer declares
 *     (over-validation / removed backend field),
 *   - required backend fields the frontend schema omits
 *     (under-validation / new backend field the UI ignores),
 *   - nullability mismatches (backend nullable vs frontend non-nullable and
 *     vice-versa),
 *   - mapped OpenAPI component schemas that no longer exist.
 *
 * ADVISORY-FIRST: this script ALWAYS exits 0 (unless it cannot run at all, e.g.
 * the artifact is missing). It prints a human-readable report so it can be wired
 * into CI without blocking on PRE-EXISTING drift. Flipping it to BLOCKING is a
 * follow-up once the reported drift is 0 — see
 * docs/frontend/phase-7-baseline.md.
 *
 * Scope note: dependency-free static analysis. The Zod side is parsed from the
 * `z.object({...})` literal of each mapped schema (the schemas in src/schemas
 * are flat object literals, by convention). The OpenAPI side reads the JSON
 * `components.schemas` block. This intentionally avoids a bundler/AST toolchain
 * to stay aligned with the other Phase 7 gate scripts (url-inventory, feature
 * boundaries), which are also plain static scans.
 *
 * Usage:
 *   node scripts/check-schema-drift.mjs            # print advisory report (exit 0)
 *   node scripts/check-schema-drift.mjs --strict   # exit 1 if drift found (future blocking)
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const FRONTEND_ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..");
const REPO_ROOT = join(FRONTEND_ROOT, "..");
const OPENAPI_PATH = join(REPO_ROOT, "docs/architecture/openapi.json");
const SCHEMAS_DIR = join(FRONTEND_ROOT, "src/schemas");

/**
 * Curated mapping: frontend Zod export -> backend OpenAPI component schema.
 *
 * Each entry pins one Zod object schema (by its exported const name and source
 * file) to the OpenAPI component it is meant to mirror. Only flat-object
 * response/request DTOs are mapped; design-system (neon-*) prop schemas and
 * `.refine()`-wrapped composites are intentionally excluded because they are
 * not 1:1 API DTOs.
 *
 * @type {{ zod: string, file: string, openapi: string, kind: "response" | "request" }[]}
 */
const SCHEMA_MAP = [
  // --- conversation / chat ---
  { zod: "messageSourceSchema", file: "chat.ts", openapi: "MessageSource", kind: "response" },
  { zod: "messageSchema", file: "chat.ts", openapi: "MessageResponse", kind: "response" },
  { zod: "conversationSchema", file: "chat.ts", openapi: "ConversationResponse", kind: "response" },
  { zod: "conversationListResponseSchema", file: "chat.ts", openapi: "ConversationListResponse", kind: "response" },
  { zod: "messageListResponseSchema", file: "chat.ts", openapi: "MessageListResponse", kind: "response" },
  { zod: "chatRequestSchema", file: "chat.ts", openapi: "ChatRequest", kind: "request" },
  { zod: "chatResponseSchema", file: "chat.ts", openapi: "ChatResponse", kind: "response" },
  // --- knowledge ---
  { zod: "documentSchema", file: "knowledge.ts", openapi: "DocumentResponse", kind: "response" },
  { zod: "documentListResponseSchema", file: "knowledge.ts", openapi: "DocumentListResponse", kind: "response" },
  { zod: "createDocumentRequestSchema", file: "knowledge.ts", openapi: "DocumentCreate", kind: "request" },
  { zod: "documentUploadResponseSchema", file: "knowledge.ts", openapi: "DocumentUploadResponse", kind: "response" },
  // --- carousel ---
  { zod: "carouselDesignColorsSchema", file: "carousel.ts", openapi: "CarouselDesignColors", kind: "response" },
  { zod: "carouselDesignTypographySchema", file: "carousel.ts", openapi: "CarouselDesignTypography", kind: "response" },
  { zod: "carouselBlogImageMapEntrySchema", file: "carousel.ts", openapi: "CarouselBlogImageMapEntry", kind: "response" },
  { zod: "carouselDesignImagesSchema", file: "carousel.ts", openapi: "CarouselDesignImages", kind: "response" },
  { zod: "carouselDesignLayoutSchema", file: "carousel.ts", openapi: "CarouselDesignLayout", kind: "response" },
  { zod: "carouselDesignResponseSchema", file: "carousel.ts", openapi: "CarouselDesignResponse", kind: "response" },
  { zod: "carouselBlogI18nResponseSchema", file: "carousel.ts", openapi: "CarouselBlogI18nResponse", kind: "response" },
  { zod: "carouselProjectResponseSchema", file: "carousel.ts", openapi: "CarouselProjectResponse", kind: "response" },
  { zod: "carouselProjectListResponseSchema", file: "carousel.ts", openapi: "CarouselProjectListResponse", kind: "response" },
  { zod: "carouselSlideResponseSchema", file: "carousel.ts", openapi: "CarouselSlideResponse", kind: "response" },
];

/** Marks a Zod field whose type we do not statically resolve (opaque). */
const OPAQUE = "<opaque>";

/**
 * Slice the `{ ... }` body of the FIRST `z.object(` after the named export.
 *
 * @param {string} source full TS file text
 * @param {string} constName e.g. "documentSchema"
 * @returns {string | null} the brace body (without the outer braces) or null
 */
function extractZodObjectBody(source, constName) {
  const declRe = new RegExp(`export\\s+const\\s+${constName}\\b`);
  const declMatch = declRe.exec(source);
  if (!declMatch) {
    return null;
  }
  const objIdx = source.indexOf("z.object(", declMatch.index);
  if (objIdx === -1) {
    return null;
  }
  const braceStart = source.indexOf("{", objIdx);
  if (braceStart === -1) {
    return null;
  }
  let depth = 0;
  for (let i = braceStart; i < source.length; i += 1) {
    const ch = source[i];
    if (ch === "{") {
      depth += 1;
    } else if (ch === "}") {
      depth -= 1;
      if (depth === 0) {
        return source.slice(braceStart + 1, i);
      }
    }
  }
  return null;
}

/**
 * Split an object-literal body into top-level `key: value` field entries,
 * respecting nesting and ignoring commas inside nested braces/parens/brackets.
 *
 * @param {string} body
 * @returns {{ name: string, expr: string }[]}
 */
function splitTopLevelFields(body) {
  /** @type {{ name: string, expr: string }[]} */
  const fields = [];
  let depth = 0;
  let current = "";
  for (const ch of body) {
    if (ch === "{" || ch === "(" || ch === "[") {
      depth += 1;
    } else if (ch === "}" || ch === ")" || ch === "]") {
      depth -= 1;
    }
    if (ch === "," && depth === 0) {
      pushField(fields, current);
      current = "";
      continue;
    }
    current += ch;
  }
  pushField(fields, current);
  return fields;
}

/**
 * @param {{ name: string, expr: string }[]} fields
 * @param {string} raw
 */
function pushField(fields, raw) {
  const trimmed = raw.trim();
  if (!trimmed) {
    return;
  }
  const colon = trimmed.indexOf(":");
  if (colon === -1) {
    return;
  }
  const name = trimmed.slice(0, colon).trim().replace(/['"]/g, "");
  const expr = trimmed.slice(colon + 1).trim();
  if (name) {
    fields.push({ name, expr });
  }
}

/**
 * Reduce a Zod field expression to a coarse `{ type, nullable, optional }`.
 * Types are normalized to the OpenAPI vocabulary (string/number/boolean/array/
 * object) where statically determinable; anything dynamic maps to OPAQUE.
 *
 * @param {string} expr e.g. `z.string().nullable().optional()`
 * @returns {{ type: string, nullable: boolean, optional: boolean }}
 */
function classifyZodExpr(expr) {
  const nullable = /\.nullable\(\)/.test(expr);
  const optional = /\.optional\(\)/.test(expr);
  let type = OPAQUE;
  if (/^z\.string\b/.test(expr) || /^z\.enum\b/.test(expr)) {
    type = "string";
  } else if (/^z\.number\b/.test(expr)) {
    type = "number";
  } else if (/^z\.boolean\b/.test(expr)) {
    type = "boolean";
  } else if (/^z\.array\b/.test(expr)) {
    type = "array";
  } else if (/^z\.object\b/.test(expr) || /^z\.record\b/.test(expr)) {
    type = "object";
  }
  // z.unknown() / nested schema refs / composites stay OPAQUE (no type assertion).
  return { type, nullable, optional };
}

/**
 * Parse one mapped Zod schema into a field map.
 *
 * @param {string} file e.g. "chat.ts"
 * @param {string} constName
 * @returns {Record<string, { type: string, nullable: boolean, optional: boolean }> | null}
 */
function parseZodSchema(file, constName) {
  const source = readFileSync(join(SCHEMAS_DIR, file), "utf8");
  const body = extractZodObjectBody(source, constName);
  if (body === null) {
    return null;
  }
  /** @type {Record<string, { type: string, nullable: boolean, optional: boolean }>} */
  const out = {};
  for (const { name, expr } of splitTopLevelFields(body)) {
    out[name] = classifyZodExpr(expr);
  }
  return out;
}

/**
 * Reduce an OpenAPI property schema to `{ type, nullable }` in the same
 * vocabulary as classifyZodExpr. Handles the FastAPI/Pydantic `anyOf [T, null]`
 * nullable encoding and `$ref` (treated as object/OPAQUE).
 *
 * @param {Record<string, unknown>} prop
 * @returns {{ type: string, nullable: boolean }}
 */
function classifyOpenApiProp(prop) {
  if (prop.$ref) {
    return { type: "object", nullable: false };
  }
  if (Array.isArray(prop.anyOf)) {
    const variants = /** @type {Record<string, unknown>[]} */ (prop.anyOf);
    const nullable = variants.some((v) => v.type === "null");
    const main = variants.find((v) => v.type !== "null") ?? {};
    const inner = classifyOpenApiProp(main);
    return { type: inner.type, nullable: nullable || inner.nullable };
  }
  const nullable = prop.nullable === true;
  const rawType = typeof prop.type === "string" ? prop.type : OPAQUE;
  const type = rawType === "integer" ? "number" : rawType;
  return { type, nullable };
}

/**
 * @param {Record<string, unknown>} component an OpenAPI component schema
 * @returns {{ props: Record<string, { type: string, nullable: boolean }>, required: Set<string> }}
 */
function parseOpenApiComponent(component) {
  /** @type {Record<string, { type: string, nullable: boolean }>} */
  const props = {};
  const rawProps = /** @type {Record<string, Record<string, unknown>>} */ (
    component.properties ?? {}
  );
  for (const [name, prop] of Object.entries(rawProps)) {
    props[name] = classifyOpenApiProp(prop);
  }
  const required = new Set(
    Array.isArray(component.required)
      ? /** @type {string[]} */ (component.required)
      : [],
  );
  return { props, required };
}

/**
 * Compare one mapped schema and return its drift findings.
 *
 * @param {(typeof SCHEMA_MAP)[number]} entry
 * @param {Record<string, Record<string, unknown>>} openApiSchemas
 * @returns {string[]}
 */
function compareEntry(entry, openApiSchemas) {
  /** @type {string[]} */
  const findings = [];

  const component = openApiSchemas[entry.openapi];
  if (!component) {
    findings.push(`MISSING-COMPONENT: OpenAPI has no schema "${entry.openapi}" (mapping is stale or the backend renamed/removed it).`);
    return findings;
  }

  const zodFields = parseZodSchema(entry.file, entry.zod);
  if (zodFields === null) {
    findings.push(`UNPARSEABLE-ZOD: could not extract a z.object literal for "${entry.zod}" in ${entry.file}.`);
    return findings;
  }

  const { props: apiProps, required } = parseOpenApiComponent(component);
  const zodNames = new Set(Object.keys(zodFields));
  const apiNames = new Set(Object.keys(apiProps));

  // Fields the frontend validates that the API no longer declares.
  for (const name of zodNames) {
    if (!apiNames.has(name)) {
      findings.push(`EXTRA-FRONTEND-FIELD: "${name}" is validated by the frontend but absent from the API schema.`);
    }
  }

  // Required API fields the frontend schema omits entirely.
  for (const name of apiNames) {
    if (!zodNames.has(name)) {
      const tag = required.has(name) ? "MISSING-REQUIRED-FIELD" : "UNMODELED-OPTIONAL-FIELD";
      findings.push(`${tag}: API field "${name}" is not present in the frontend schema.`);
    }
  }

  // Type / nullability mismatches on shared fields.
  for (const name of zodNames) {
    const api = apiProps[name];
    if (!api) {
      continue;
    }
    const zod = zodFields[name];
    const known = zod.type !== OPAQUE && api.type !== OPAQUE;
    if (known && zod.type !== api.type) {
      findings.push(`TYPE-MISMATCH: "${name}" is ${zod.type} (frontend) vs ${api.type} (API).`);
    }
    const apiOptional = !required.has(name);
    const apiAcceptsAbsent = api.nullable || apiOptional;
    const zodAcceptsAbsent = zod.nullable || zod.optional;
    if (apiAcceptsAbsent && !zodAcceptsAbsent) {
      findings.push(`NULLABILITY-MISMATCH: "${name}" can be null/absent in the API but the frontend requires a present, non-null value.`);
    }
  }

  return findings.length ? findings : ["clean"];
}

function main() {
  const strict = process.argv.includes("--strict");

  let openApiDoc;
  try {
    openApiDoc = JSON.parse(readFileSync(OPENAPI_PATH, "utf8"));
  } catch {
    process.stderr.write(
      `Cannot read OpenAPI artifact at ${OPENAPI_PATH}.\n` +
        "Generate it with `uv run python backend/scripts/export_openapi.py`.\n",
    );
    process.exit(strict ? 1 : 0);
  }

  const openApiSchemas = openApiDoc?.components?.schemas ?? {};

  let totalDrift = 0;
  const lines = [];
  for (const entry of SCHEMA_MAP) {
    const findings = compareEntry(entry, openApiSchemas);
    const isClean = findings.length === 1 && findings[0] === "clean";
    const label = `${entry.zod} -> ${entry.openapi}`;
    if (isClean) {
      lines.push(`  OK   ${label}`);
      continue;
    }
    totalDrift += findings.length;
    lines.push(`  DRIFT ${label}`);
    for (const f of findings) {
      lines.push(`        - ${f}`);
    }
  }

  process.stdout.write("\nOpenAPI <-> Zod schema-drift report (AE-0141)\n");
  process.stdout.write(`  artifact: ${OPENAPI_PATH}\n`);
  process.stdout.write(`  mapped schemas: ${SCHEMA_MAP.length}\n\n`);
  process.stdout.write(`${lines.join("\n")}\n\n`);

  if (totalDrift === 0) {
    process.stdout.write("No drift across mapped schemas.\n");
    process.exit(0);
  }

  process.stdout.write(
    `${totalDrift} drift finding(s) across mapped schemas.\n`,
  );
  if (strict) {
    process.stderr.write(
      "\nSTRICT mode: failing on drift. Reconcile the Zod schemas with the API,\n" +
        "then regenerate the artifact (export_openapi.py) if the backend changed.\n",
    );
    process.exit(1);
  }
  process.stdout.write(
    "ADVISORY mode: not blocking on pre-existing drift. Flip to --strict in CI\n" +
      "once the findings above reach 0 (see docs/frontend/phase-7-baseline.md).\n",
  );
  process.exit(0);
}

main();
