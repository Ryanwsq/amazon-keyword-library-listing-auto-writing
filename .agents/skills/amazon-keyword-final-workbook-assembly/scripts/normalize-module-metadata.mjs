#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const PROCESS_DIRECTORY_NAME = "过程性文件";
const MODULE_PARTITIONS = [
  "01_第一板块_来源采集",
  "02_第二板块_品类清洗",
  "03_第三板块_分类与分析",
];
const METADATA_NAME_RE = /(manifest|handoff|verification).*\.json$/i;
const TASK_THREAD_UUID_RE = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i;
const MACHINE_PATH_RE = /(?:file:\/\/\/Users\/|\/Users\/|\/home\/|\/Volumes\/|\/private\/|\/var\/folders\/|\/tmp\/|[a-z]:\\(?:Users|Documents and Settings|Temp)\\)/i;

function shaText(value) {
  return crypto.createHash("sha256").update(value, "utf8").digest("hex");
}

async function walk(root) {
  const output = [];
  for (const entry of await fs.readdir(root, { withFileTypes: true })) {
    const current = path.join(root, entry.name);
    if (entry.isSymbolicLink()) throw new Error("Symbolic links are forbidden in packaged module evidence");
    output.push(current);
    if (entry.isDirectory()) output.push(...await walk(current));
  }
  return output;
}

function unsafe(value) {
  return TASK_THREAD_UUID_RE.test(value) || MACHINE_PATH_RE.test(value);
}

function portableBasename(value) {
  const withoutUri = value.trim().replace(/^file:\/\//i, "");
  const withoutQuery = withoutUri.split(/[?#]/, 1)[0].replaceAll("\\", "/").replace(/\/+$/, "");
  return path.posix.basename(withoutQuery);
}

function buildNameIndex(partitionRoot, entries) {
  const index = new Map();
  for (const entry of entries) {
    const name = path.basename(entry);
    if (!index.has(name)) index.set(name, []);
    index.get(name).push(entry);
  }
  return { partitionRoot, index };
}

function stableRelativePath(metadataFile, target, partitionRoot) {
  const relative = path.relative(path.dirname(metadataFile), target).split(path.sep).join("/");
  if (!relative || relative.startsWith("../") && !path.resolve(target).startsWith(`${path.resolve(partitionRoot)}${path.sep}`)) {
    throw new Error("Resolved metadata target escapes its module partition");
  }
  if (unsafe(relative)) throw new Error("Resolved metadata path is still machine-specific");
  return relative;
}

function rewriteValue(value, context) {
  if (typeof value === "string") {
    if (!unsafe(value)) return value;
    const name = portableBasename(value);
    const candidates = context.nameIndex.get(name) ?? [];
    if (candidates.length !== 1) {
      throw new Error(`Unsafe metadata path cannot be uniquely rebased (fingerprint ${shaText(value)})`);
    }
    const rewritten = stableRelativePath(context.metadataFile, candidates[0], context.partitionRoot);
    context.rewrites.push({
      metadata_file_fingerprint_sha256: shaText(path.relative(context.partitionRoot, context.metadataFile)),
      original_value_fingerprint_sha256: shaText(value),
      stable_relative_path_fingerprint_sha256: shaText(rewritten),
    });
    return rewritten;
  }
  if (Array.isArray(value)) return value.map((item) => rewriteValue(item, context));
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, rewriteValue(item, context)]));
  }
  return value;
}

async function writeJsonAtomic(file, value) {
  const temporary = `${file}.tmp`;
  await fs.writeFile(temporary, JSON.stringify(value, null, 2) + "\n", "utf8");
  await fs.rename(temporary, file);
}

export async function normalizeModuleMetadata(deliveryRoot) {
  const processRoot = path.join(path.resolve(deliveryRoot), PROCESS_DIRECTORY_NAME);
  const result = { status: "pass", partitions_scanned: 0, metadata_files_scanned: 0, rewritten_values: 0, files: [] };

  for (const partition of MODULE_PARTITIONS) {
    const partitionRoot = path.join(processRoot, partition);
    const entries = await walk(partitionRoot);
    const { index } = buildNameIndex(partitionRoot, entries);
    const metadataFiles = entries.filter((entry) => path.extname(entry).toLowerCase() === ".json" && METADATA_NAME_RE.test(path.basename(entry)));
    result.partitions_scanned += 1;

    for (const metadataFile of metadataFiles.sort()) {
      const original = JSON.parse(await fs.readFile(metadataFile, "utf8"));
      const context = { metadataFile, partitionRoot, nameIndex: index, rewrites: [] };
      const rewritten = rewriteValue(original, context);
      if (context.rewrites.length) await writeJsonAtomic(metadataFile, rewritten);
      result.metadata_files_scanned += 1;
      result.rewritten_values += context.rewrites.length;
      result.files.push({
        relative_path: path.relative(processRoot, metadataFile).split(path.sep).join("/"),
        rewritten_values: context.rewrites.length,
        rewrite_evidence: context.rewrites,
      });
    }
  }
  return result;
}

function parseArgs(argv) {
  const output = {};
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === "--delivery-root") output.deliveryRoot = argv[++index];
    else if (value === "--help") output.help = true;
    else throw new Error(`Unknown argument: ${value}`);
  }
  return output;
}

async function cli() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || !args.deliveryRoot) {
    console.log("Usage: node normalize-module-metadata.mjs --delivery-root <path>");
    return;
  }
  console.log(JSON.stringify(await normalizeModuleMetadata(args.deliveryRoot), null, 2));
}

if (path.resolve(process.argv[1] ?? "") === fileURLToPath(import.meta.url)) {
  cli().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
