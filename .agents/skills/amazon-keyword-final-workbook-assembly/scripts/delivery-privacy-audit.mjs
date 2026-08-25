#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

export const AUDIT_SCHEMA = "amazon-keyword-delivery-privacy-audit/v1";
export const PROCESS_MANIFEST_RELATIVE_PATH = "过程性文件/process-manifest.json";
export const TASK_THREAD_UUID_RE = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi;
export const SHA256_RE = /\b[0-9a-f]{64}\b/gi;
export const MACHINE_PATH_RE = /(?:file:\/\/\/Users\/|\/Users\/|\/home\/|\/Volumes\/|\/private\/|\/var\/folders\/|\/tmp\/|[a-z]:\\(?:Users|Documents and Settings|Temp)\\)/gi;

const TEXT_EXTENSIONS = new Set([
  ".csv", ".json", ".jsonl", ".log", ".md", ".ndjson", ".txt", ".tsv", ".xml", ".yaml", ".yml",
]);
const XLSX_EXTENSIONS = new Set([".xlsx", ".xlsm"]);
const OFFICE_GUID_ALLOWLIST = new Map([
  ["d5cdd505-2e9c-101b-9397-08002b2cf9ae", "docProps/custom.xml"],
  ["eb79def2-80b8-43e5-95bd-54cbddf9020c", "xl/styles.xml"],
  ["b58b0392-4f1f-4190-bb64-5df3571dce5f", "xl/workbook.xml"],
]);

function shaBuffer(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

async function shaFile(file) {
  return shaBuffer(await fs.readFile(file));
}

function matches(text, regex) {
  return [...String(text ?? "").matchAll(regex)].map((match) => match[0]);
}

function decodeXmlEntities(text) {
  return text
    .replace(/&#x([0-9a-f]+);/gi, (_, value) => String.fromCodePoint(Number.parseInt(value, 16)))
    .replace(/&#([0-9]+);/g, (_, value) => String.fromCodePoint(Number.parseInt(value, 10)))
    .replaceAll("&quot;", '"')
    .replaceAll("&apos;", "'")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&amp;", "&");
}

function unzipEntryPattern(entry) {
  return entry.replaceAll("[", "\\[").replaceAll("]", "\\]").replaceAll("*", "\\*").replaceAll("?", "\\?");
}

async function walk(root) {
  const output = [];
  for (const entry of await fs.readdir(root, { withFileTypes: true })) {
    const current = path.join(root, entry.name);
    if (entry.isSymbolicLink()) throw new Error("Symbolic links are forbidden in the two-object delivery");
    if (entry.isDirectory()) output.push(...await walk(current));
    else output.push(current);
  }
  return output;
}

async function walkDirectories(root) {
  const output = [];
  for (const entry of await fs.readdir(root, { withFileTypes: true })) {
    const current = path.join(root, entry.name);
    if (entry.isSymbolicLink()) throw new Error("Symbolic links are forbidden in the two-object delivery");
    if (entry.isDirectory()) {
      output.push(current);
      output.push(...await walkDirectories(current));
    }
  }
  return output;
}

function safeFinding(kind, relativePath, extra = {}) {
  return {
    kind,
    relative_path_fingerprint_sha256: shaBuffer(Buffer.from(relativePath, "utf8")),
    ...extra,
  };
}

function scanTextBody(body, relativePath, bucket, surface) {
  const taskIds = matches(body, TASK_THREAD_UUID_RE);
  const machinePaths = matches(body, MACHINE_PATH_RE);
  const hashes = matches(body, SHA256_RE);
  bucket.sha256_tokens += hashes.length;
  bucket.sha256_tokens_containing_01a += hashes.filter((hash) => hash.toLowerCase().includes("01a")).length;
  if (taskIds.length) {
    bucket.task_thread_uuid_hits += taskIds.length;
    bucket.findings.push(safeFinding(`${surface}_task_thread_uuid`, relativePath, { count: taskIds.length }));
  }
  if (machinePaths.length) {
    bucket.machine_path_hits += machinePaths.length;
    bucket.findings.push(safeFinding(`${surface}_machine_absolute_path`, relativePath, { count: machinePaths.length }));
  }
}

function scanXlsx(file, relativePath, bucket) {
  let entries;
  try {
    entries = execFileSync("unzip", ["-Z1", file], { encoding: "utf8" }).split(/\r?\n/).filter(Boolean);
  } catch (error) {
    bucket.package_errors += 1;
    bucket.findings.push(safeFinding("xlsx_package_unreadable", relativePath, { error_code: error.status ?? 1 }));
    return;
  }

  for (const entry of entries) {
    const entryTaskIds = matches(entry, TASK_THREAD_UUID_RE);
    if (entryTaskIds.length) {
      bucket.xlsx_entry_task_thread_uuid_hits += entryTaskIds.length;
      bucket.findings.push(safeFinding("xlsx_entry_task_thread_uuid", relativePath, { count: entryTaskIds.length }));
    }
  }

  for (const entry of entries.filter((name) => name.endsWith(".xml") || name.endsWith(".rels"))) {
    let raw;
    try {
      raw = execFileSync("unzip", ["-p", file, unzipEntryPattern(entry)], {
        encoding: "utf8",
        maxBuffer: 128 * 1024 * 1024,
      });
    } catch (error) {
      bucket.package_errors += 1;
      bucket.findings.push(safeFinding("xlsx_part_unreadable", relativePath, {
        part_fingerprint_sha256: shaBuffer(Buffer.from(entry, "utf8")),
        error_code: error.status ?? 1,
      }));
      continue;
    }

    const body = decodeXmlEntities(raw);
    const machinePaths = matches(body, MACHINE_PATH_RE);
    if (machinePaths.length) {
      bucket.xlsx_machine_path_hits += machinePaths.length;
      bucket.findings.push(safeFinding("xlsx_machine_absolute_path", relativePath, {
        part_fingerprint_sha256: shaBuffer(Buffer.from(entry, "utf8")),
        count: machinePaths.length,
      }));
    }

    const uuids = matches(body, TASK_THREAD_UUID_RE).map((value) => value.toLowerCase());
    const businessPart = /xl\/(sharedStrings\.xml|worksheets\/|comments|threadedComments)/i.test(entry);
    if (businessPart && uuids.length) bucket.xlsx_business_string_uuid_hits += uuids.length;
    for (const uuid of uuids) {
      if (OFFICE_GUID_ALLOWLIST.get(uuid) === entry) {
        bucket.office_internal_guid_occurrences += 1;
      } else {
        bucket.ooxml_non_allowlisted_uuid_hits += 1;
        bucket.findings.push(safeFinding("ooxml_non_allowlisted_uuid", relativePath, {
          part_fingerprint_sha256: shaBuffer(Buffer.from(entry, "utf8")),
        }));
      }
    }
  }
}

function emptyBucket() {
  return {
    task_thread_uuid_hits: 0,
    path_task_thread_uuid_hits: 0,
    machine_path_hits: 0,
    xlsx_machine_path_hits: 0,
    xlsx_entry_task_thread_uuid_hits: 0,
    xlsx_business_string_uuid_hits: 0,
    ooxml_non_allowlisted_uuid_hits: 0,
    office_internal_guid_occurrences: 0,
    package_errors: 0,
    sha256_tokens: 0,
    sha256_tokens_containing_01a: 0,
    findings: [],
  };
}

export async function contentFingerprintExcludingManifest(deliveryRoot) {
  const files = (await walk(deliveryRoot)).sort();
  const directories = (await walkDirectories(deliveryRoot)).sort();
  const lines = [];
  let fileCount = 0;
  for (const directory of directories) {
    lines.push(`D\0${path.relative(deliveryRoot, directory)}\n`);
  }
  for (const file of files) {
    const relativePath = path.relative(deliveryRoot, file);
    if (relativePath === PROCESS_MANIFEST_RELATIVE_PATH) continue;
    lines.push(`F\0${relativePath}\0${await shaFile(file)}\n`);
    fileCount += 1;
  }
  return {
    sha256: shaBuffer(Buffer.from(lines.join(""), "utf8")),
    file_count: fileCount,
    directory_count: directories.length,
  };
}

export async function auditDelivery(deliveryRoot) {
  const resolvedRoot = path.resolve(deliveryRoot);
  const files = (await walk(resolvedRoot)).sort();
  const directories = (await walkDirectories(resolvedRoot)).sort();
  const bucket = emptyBucket();
  let textFileCount = 0;
  let binaryFileCount = 0;
  let xlsxFileCount = 0;

  for (const directory of directories) {
    const relativePath = path.relative(resolvedRoot, directory);
    const pathTaskIds = matches(relativePath, TASK_THREAD_UUID_RE);
    if (pathTaskIds.length) {
      bucket.path_task_thread_uuid_hits += pathTaskIds.length;
      bucket.findings.push(safeFinding("directory_path_task_thread_uuid", relativePath, { count: pathTaskIds.length }));
    }
  }

  for (const file of files) {
    const relativePath = path.relative(resolvedRoot, file);
    const pathTaskIds = matches(relativePath, TASK_THREAD_UUID_RE);
    if (pathTaskIds.length) {
      bucket.path_task_thread_uuid_hits += pathTaskIds.length;
      bucket.findings.push(safeFinding("file_path_task_thread_uuid", relativePath, { count: pathTaskIds.length }));
    }

    const extension = path.extname(file).toLowerCase();
    if (XLSX_EXTENSIONS.has(extension)) {
      xlsxFileCount += 1;
      scanXlsx(file, relativePath, bucket);
      continue;
    }
    if (TEXT_EXTENSIONS.has(extension)) {
      textFileCount += 1;
      scanTextBody(await fs.readFile(file, "utf8"), relativePath, bucket, "text");
      continue;
    }

    binaryFileCount += 1;
    scanTextBody((await fs.readFile(file)).toString("latin1"), relativePath, bucket, "binary_metadata");
  }

  const fingerprint = await contentFingerprintExcludingManifest(resolvedRoot);
  const forbiddenHitCount =
    bucket.task_thread_uuid_hits +
    bucket.path_task_thread_uuid_hits +
    bucket.machine_path_hits +
    bucket.xlsx_machine_path_hits +
    bucket.xlsx_entry_task_thread_uuid_hits +
    bucket.ooxml_non_allowlisted_uuid_hits +
    bucket.package_errors;

  return {
    schema: AUDIT_SCHEMA,
    status: forbiddenHitCount === 0 ? "pass" : "fail",
    delivery_root_name: path.basename(resolvedRoot),
    method: {
      task_thread_uuid: "full hyphenated 8-4-4-4-12 hexadecimal token; no UUID-version restriction",
      machine_absolute_path: "POSIX user/private/temp roots, file:///Users, and Windows user roots",
      sha256: "64 non-hyphenated hexadecimal characters are counted separately and never matched by generic 01a",
      xlsx: "all OOXML XML/rels parts after numeric-entity decoding; cell/shared-string/comment parts identified separately",
      office_guid: "exact three-token allowlist bound to docProps/custom.xml, xl/styles.xml, and xl/workbook.xml",
      findings: "only classification and SHA-256 fingerprints are emitted; raw task IDs and machine paths are never echoed",
    },
    scanned: {
      file_count: files.length,
      file_count_excluding_process_manifest: fingerprint.file_count,
      directory_count: directories.length,
      text_file_count: textFileCount,
      binary_file_count: binaryFileCount,
      xlsx_file_count: xlsxFileCount,
    },
    content_fingerprint_excluding_process_manifest_sha256: fingerprint.sha256,
    results: {
      forbidden_hit_count: forbiddenHitCount,
      task_thread_uuid_hits_in_text_or_binary: bucket.task_thread_uuid_hits,
      task_thread_uuid_hits_in_file_paths: bucket.path_task_thread_uuid_hits,
      task_thread_uuid_hits_in_packaged_paths: bucket.path_task_thread_uuid_hits,
      machine_absolute_path_hits_in_text_or_binary: bucket.machine_path_hits,
      machine_absolute_path_hits_in_xlsx: bucket.xlsx_machine_path_hits,
      task_thread_uuid_hits_in_xlsx_entry_paths: bucket.xlsx_entry_task_thread_uuid_hits,
      task_thread_uuid_hits_in_xlsx_business_strings: bucket.xlsx_business_string_uuid_hits,
      ooxml_non_allowlisted_uuid_hits: bucket.ooxml_non_allowlisted_uuid_hits,
      office_internal_guid_occurrences: bucket.office_internal_guid_occurrences,
      office_guid_allowlist_size: OFFICE_GUID_ALLOWLIST.size,
      xlsx_package_errors: bucket.package_errors,
      sha256_tokens_observed: bucket.sha256_tokens,
      sha256_tokens_containing_01a: bucket.sha256_tokens_containing_01a,
      generic_01a_matcher_used: false,
    },
    findings: bucket.findings,
  };
}

function isInside(parent, child) {
  const relative = path.relative(path.resolve(parent), path.resolve(child));
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

export async function writeAuditReport(deliveryRoot, reportPath) {
  if (isInside(deliveryRoot, reportPath)) throw new Error("Privacy report must stay outside the two-object delivery");
  const report = await auditDelivery(deliveryRoot);
  await fs.mkdir(path.dirname(path.resolve(reportPath)), { recursive: true });
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + "\n", "utf8");
  return report;
}

function parseArgs(argv) {
  const output = {};
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === "--delivery-root") output.deliveryRoot = argv[++index];
    else if (value === "--report") output.report = argv[++index];
    else if (value === "--help") output.help = true;
    else throw new Error(`Unknown argument: ${value}`);
  }
  return output;
}

async function cli() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || !args.deliveryRoot) {
    console.log("Usage: node delivery-privacy-audit.mjs --delivery-root <path> [--report <outside-delivery.json>]");
    return;
  }
  const report = args.report ? await writeAuditReport(args.deliveryRoot, args.report) : await auditDelivery(args.deliveryRoot);
  console.log(JSON.stringify(report, null, 2));
  if (report.status !== "pass") process.exitCode = 1;
}

if (path.resolve(process.argv[1] ?? "") === fileURLToPath(import.meta.url)) {
  cli().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
