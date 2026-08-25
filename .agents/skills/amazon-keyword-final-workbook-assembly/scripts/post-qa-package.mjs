#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const PROCESS_DIRECTORY_NAME = "过程性文件";
const PROCESS_MANIFEST_NAME = "process-manifest.json";
const QUALITY_DIRECTORY_NAME = "04_独立质量验证";
const PROCESS_PARTITIONS = [
  "01_第一板块_来源采集",
  "02_第二板块_品类清洗",
  "03_第三板块_分类与分析",
  QUALITY_DIRECTORY_NAME,
];
const ASSEMBLY_OWNED_QUALITY_PLACEHOLDERS = [
  "QA_INPUT.md",
  "assembly-manifest.json",
  "handoff.json",
  "verification.json",
  "independent-qa-status.json",
  "checks",
  "previews",
];
const REQUIRED_QUALITY_ENTRIES = ["独立质量验证.xlsx", "quality-manifest.json", "independent-qa-previews"];
const ISSUE_ENTRY_ALTERNATIVES = ["issues.md", "issue-reference.json"];
const TASK_THREAD_UUID_RE = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi;
const MACHINE_PATH_RE = /(?:file:\/\/\/Users\/|\/Users\/|\/home\/|\/Volumes\/|\/private\/|\/var\/folders\/|\/tmp\/|[a-z]:\\(?:Users|Documents and Settings|Temp)\\)/gi;
const TEXT_EXTENSIONS = new Set([".csv", ".json", ".jsonl", ".log", ".md", ".ndjson", ".txt", ".tsv", ".xml", ".yaml", ".yml"]);

function shaBuffer(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

async function shaFile(file) {
  return shaBuffer(await fs.readFile(file));
}

async function exists(target) {
  try {
    await fs.access(target);
    return true;
  } catch {
    return false;
  }
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

function isInside(parent, child) {
  const relative = path.relative(path.resolve(parent), path.resolve(child));
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

function expectedQualityWhitelist(actualEntries) {
  const issueEntries = actualEntries.filter((entry) => ISSUE_ENTRY_ALTERNATIVES.includes(entry));
  if (issueEntries.length !== 1) {
    throw new Error("Quality directory must contain exactly one canonical issues document or one issue reference");
  }
  return [...REQUIRED_QUALITY_ENTRIES, issueEntries[0]].sort();
}

async function validateDeliveryLayout(deliveryRoot) {
  const root = path.resolve(deliveryRoot);
  const topEntries = (await fs.readdir(root)).sort();
  const finalWorkbooks = topEntries.filter((entry) => entry.endsWith("-最终关键词词库.xlsx"));
  const expectedTop = [PROCESS_DIRECTORY_NAME, ...finalWorkbooks].sort();
  if (finalWorkbooks.length !== 1 || JSON.stringify(topEntries) !== JSON.stringify(expectedTop)) {
    throw new Error("Delivery root must contain exactly the process directory and one final eight-sheet workbook");
  }

  const processRoot = path.join(root, PROCESS_DIRECTORY_NAME);
  const processEntries = (await fs.readdir(processRoot)).sort();
  const expectedProcess = [...PROCESS_PARTITIONS, PROCESS_MANIFEST_NAME].sort();
  if (JSON.stringify(processEntries) !== JSON.stringify(expectedProcess)) {
    throw new Error("Process directory must contain exactly four partitions and the unique process manifest");
  }
  return {
    root,
    processRoot,
    processManifest: path.join(processRoot, PROCESS_MANIFEST_NAME),
    qualityRoot: path.join(processRoot, QUALITY_DIRECTORY_NAME),
    finalWorkbook: path.join(root, finalWorkbooks[0]),
    finalWorkbookName: finalWorkbooks[0],
  };
}

async function validateQualityDirectory(qualityRoot) {
  const actualEntries = (await fs.readdir(qualityRoot)).sort();
  const whitelist = expectedQualityWhitelist(actualEntries);
  if (JSON.stringify(actualEntries) !== JSON.stringify(whitelist)) {
    throw new Error(`Quality directory whitelist failed; expected ${whitelist.join(", ")}`);
  }

  const qualityManifestPath = path.join(qualityRoot, "quality-manifest.json");
  const qualityManifest = JSON.parse(await fs.readFile(qualityManifestPath, "utf8"));
  const qualityWorkbook = qualityManifest.quality_workbook;
  if (!qualityWorkbook || qualityWorkbook.relative_path !== "独立质量验证.xlsx") {
    throw new Error("Quality manifest must lock the fixed quality workbook");
  }
  const qualityWorkbookPath = path.join(qualityRoot, qualityWorkbook.relative_path);
  if (await shaFile(qualityWorkbookPath) !== qualityWorkbook.sha256) throw new Error("Quality workbook hash mismatch");

  if (!Array.isArray(qualityManifest.previews) || qualityManifest.previews.length < 8) {
    throw new Error("Quality manifest must list at least the eight final-sheet previews");
  }
  const previewRoot = path.join(qualityRoot, "independent-qa-previews");
  const previewFiles = (await walk(previewRoot)).sort();
  const listedPreviewPaths = [];
  for (const preview of qualityManifest.previews) {
    const normalizedRelativePath = path.posix.normalize(preview.relative_path ?? "");
    if (
      normalizedRelativePath !== preview.relative_path ||
      !normalizedRelativePath.startsWith("independent-qa-previews/")
    ) {
      throw new Error("QA preview path must be canonical and stay in independent-qa-previews");
    }
    const previewPath = path.resolve(qualityRoot, ...normalizedRelativePath.split("/"));
    if (!isInside(previewRoot, previewPath) || previewPath === previewRoot) {
      throw new Error("QA preview path escapes independent-qa-previews");
    }
    const stat = await fs.stat(previewPath);
    if (stat.size !== preview.bytes || await shaFile(previewPath) !== preview.sha256) throw new Error("QA preview hash or size mismatch");
    listedPreviewPaths.push(path.resolve(previewPath));
  }
  if (JSON.stringify(previewFiles.map((file) => path.resolve(file)).sort()) !== JSON.stringify(listedPreviewPaths.sort())) {
    throw new Error("Unlisted or missing files found in independent-qa-previews");
  }

  const issueEntry = whitelist.find((entry) => ISSUE_ENTRY_ALTERNATIVES.includes(entry));
  const issueKey = issueEntry === "issues.md" ? "issue_document" : "issue_reference";
  const issueLock = qualityManifest[issueKey];
  if (!issueLock || issueLock.relative_path !== issueEntry || await shaFile(path.join(qualityRoot, issueEntry)) !== issueLock.sha256) {
    throw new Error("Quality issue artifact hash mismatch");
  }

  return {
    whitelist,
    qualityManifest,
    locks: {
      quality_workbook: { relative_path: qualityWorkbook.relative_path, sha256: qualityWorkbook.sha256 },
      quality_manifest: { relative_path: "quality-manifest.json", sha256: await shaFile(qualityManifestPath) },
      issue_artifact: { relative_path: issueEntry, sha256: issueLock.sha256 },
      previews: qualityManifest.previews.map((preview) => ({
        relative_path: preview.relative_path,
        sha256: preview.sha256,
        bytes: preview.bytes,
      })),
    },
  };
}

async function independentFingerprintExcludingManifest(deliveryRoot) {
  const files = (await walk(deliveryRoot)).sort();
  const directories = (await walkDirectories(deliveryRoot)).sort();
  const lines = [];
  let fileCount = 0;
  for (const directory of directories) {
    lines.push(`D\0${path.relative(deliveryRoot, directory)}\n`);
  }
  for (const file of files) {
    const relativePath = path.relative(deliveryRoot, file);
    if (relativePath === `${PROCESS_DIRECTORY_NAME}/${PROCESS_MANIFEST_NAME}`) continue;
    lines.push(`F\0${relativePath}\0${await shaFile(file)}\n`);
    fileCount += 1;
  }
  return { sha256: shaBuffer(Buffer.from(lines.join(""), "utf8")), file_count: fileCount, directory_count: directories.length };
}

async function independentTextPathScan(deliveryRoot) {
  let uuidHits = 0;
  let machinePathHits = 0;
  const files = await walk(deliveryRoot);
  const directories = await walkDirectories(deliveryRoot);
  for (const directory of directories) {
    uuidHits += [...path.relative(deliveryRoot, directory).matchAll(TASK_THREAD_UUID_RE)].length;
  }
  for (const file of files) {
    const relativePath = path.relative(deliveryRoot, file);
    uuidHits += [...relativePath.matchAll(TASK_THREAD_UUID_RE)].length;
    if (TEXT_EXTENSIONS.has(path.extname(file).toLowerCase())) {
      const body = await fs.readFile(file, "utf8");
      uuidHits += [...body.matchAll(TASK_THREAD_UUID_RE)].length;
      machinePathHits += [...body.matchAll(MACHINE_PATH_RE)].length;
    } else if (!new Set([".xlsx", ".xlsm"]).has(path.extname(file).toLowerCase())) {
      const body = (await fs.readFile(file)).toString("latin1");
      uuidHits += [...body.matchAll(TASK_THREAD_UUID_RE)].length;
      machinePathHits += [...body.matchAll(MACHINE_PATH_RE)].length;
    }
  }
  return { uuid_hits: uuidHits, machine_path_hits: machinePathHits };
}

async function validateIndependentPrivacyReport(deliveryRoot, reportPath) {
  if (isInside(deliveryRoot, reportPath)) throw new Error("Independent privacy report must remain outside delivery");
  const report = JSON.parse(await fs.readFile(reportPath, "utf8"));
  if (report.schema !== "amazon-keyword-delivery-privacy-audit/v1" || report.status !== "pass") {
    throw new Error("Independent privacy audit did not pass");
  }
  if (report.results?.forbidden_hit_count !== 0 || report.findings?.length !== 0) {
    throw new Error("Independent privacy report contains forbidden findings");
  }
  const fingerprint = await independentFingerprintExcludingManifest(deliveryRoot);
  if (
    report.content_fingerprint_excluding_process_manifest_sha256 !== fingerprint.sha256 ||
    report.scanned?.file_count_excluding_process_manifest !== fingerprint.file_count ||
    report.scanned?.directory_count !== fingerprint.directory_count
  ) {
    throw new Error("Independent privacy report does not match the current delivery contents");
  }
  const crossScan = await independentTextPathScan(deliveryRoot);
  if (crossScan.uuid_hits !== 0 || crossScan.machine_path_hits !== 0) {
    throw new Error("Assembly cross-scan disagrees with the independent privacy report");
  }
  return { report, fingerprint, crossScan };
}

function upsertGate(manifest, id, status, evidence) {
  if (!Array.isArray(manifest.gates)) manifest.gates = [];
  let gate = manifest.gates.find((item) => item.id === id);
  if (!gate) {
    gate = { id, name: id === 19 ? "过程文件齐全与哈希" : id === 20 ? "唯一问题文档与质量报告" : "最终封包增量独立QA" };
    manifest.gates.push(gate);
  }
  gate.status = status;
  gate.evidence = evidence;
  if (id === 21) gate.gap = "Independent QA must read-only verify the sealed final-package delta";
  else delete gate.gap;
  manifest.gates.sort((left, right) => left.id - right.id);
}

function validateGateSet(manifest, { final = false } = {}) {
  if (!Array.isArray(manifest.gates) || manifest.gates.length !== 21) throw new Error("Process manifest must contain exactly 21 assembly gates");
  const byId = new Map(manifest.gates.map((gate) => [gate.id, gate]));
  if (byId.size !== 21 || Array.from({ length: 21 }, (_, index) => index + 1).some((id) => !byId.has(id))) {
    throw new Error("Process manifest assembly gate IDs must be unique and complete from 1 through 21");
  }
  const lastPassingGate = final ? 20 : 18;
  for (let id = 1; id <= lastPassingGate; id += 1) {
    if (byId.get(id).status !== "pass") throw new Error(`Assembly Gate ${id} must pass before final packaging`);
  }
  if (final && byId.get(21).status !== "pending_post_packaging_QA") {
    throw new Error("Gate 21 must remain pending until read-only final-package QA returns");
  }
  if (!final && !["pending_independent_QA", "pending_post_packaging_QA"].includes(byId.get(21).status)) {
    throw new Error("Candidate Gate 21 cannot be marked pass before final-package QA");
  }
}

async function buildProcessInventory(processRoot, processManifest) {
  const files = (await walk(processRoot)).filter((file) => file !== processManifest).sort();
  const items = [];
  for (const file of files) {
    const stat = await fs.stat(file);
    items.push({
      relative_path: path.relative(processRoot, file),
      type: path.extname(file).slice(1).toLowerCase() || "file",
      bytes: stat.size,
      sha256: await shaFile(file),
      status: "packaged",
    });
  }
  return items;
}

async function writeFinalManifestAtomic(file, value, deliveryRoot) {
  const temporary = path.join(
    path.dirname(deliveryRoot),
    `.process-manifest-seal-${process.pid}-${crypto.randomBytes(6).toString("hex")}.tmp`,
  );
  try {
    await fs.writeFile(temporary, JSON.stringify(value, null, 2) + "\n", "utf8");
    await fs.rename(temporary, file);
  } finally {
    await fs.rm(temporary, { force: true });
  }
}

export async function preparePackage({ deliveryRoot, quarantineDir }) {
  const layout = await validateDeliveryLayout(deliveryRoot);
  if (isInside(layout.root, quarantineDir)) throw new Error("Quarantine must remain outside delivery");

  const present = [];
  for (const entry of ASSEMBLY_OWNED_QUALITY_PLACEHOLDERS) {
    if (await exists(path.join(layout.qualityRoot, entry))) present.push(entry);
  }
  if (present.length) {
    if (await exists(quarantineDir)) throw new Error("Quarantine target already exists; refusing to overwrite recovery evidence");
    await fs.mkdir(quarantineDir, { recursive: true });
    for (const entry of present) await fs.rename(path.join(layout.qualityRoot, entry), path.join(quarantineDir, entry));
  }
  const quality = await validateQualityDirectory(layout.qualityRoot);
  return {
    status: "prepared",
    moved_assembly_owned_entries: present,
    quality_directory_whitelist: quality.whitelist,
    quality_directory_file_count: (await walk(layout.qualityRoot)).length,
    recovery_quarantine_created: present.length > 0,
  };
}

export async function sealPackage({ deliveryRoot, privacyReport }) {
  const layout = await validateDeliveryLayout(deliveryRoot);
  const quality = await validateQualityDirectory(layout.qualityRoot);
  const privacy = await validateIndependentPrivacyReport(layout.root, privacyReport);
  const manifest = JSON.parse(await fs.readFile(layout.processManifest, "utf8"));
  validateGateSet(manifest);
  const finalWorkbookStat = await fs.stat(layout.finalWorkbook);

  manifest.delivery_identity = {
    ...(manifest.delivery_identity ?? {}),
    candidate_status: "incomplete",
    delivery_status: "incomplete",
    status: "incomplete",
    qa_status: "pending_post_packaging_QA",
    p1: false,
    top_level_objects: [PROCESS_DIRECTORY_NAME, layout.finalWorkbookName],
    final_workbook: {
      relative_path: layout.finalWorkbookName,
      bytes: finalWorkbookStat.size,
      sha256: await shaFile(layout.finalWorkbook),
    },
  };
  manifest.delivery_status = "incomplete";
  manifest.status = "incomplete";
  manifest.qa_status = "pending_post_packaging_QA";
  manifest.p1 = false;
  manifest.packaging_lifecycle = {
    schema: "amazon-keyword-final-package-lifecycle/v1",
    stage: "sealed_pending_post_packaging_QA",
    candidate_assembly: "completed_before_independent_QA",
    immutable_QA_artifacts: "locked_and_preserved",
    assembly_post_QA_packaging: "sealed",
    final_incremental_QA: "pending_read_only_verification",
    assembly_owned_quality_placeholders_present: false,
  };
  manifest.quality_directory = {
    relative_path: QUALITY_DIRECTORY_NAME,
    top_level_whitelist: quality.whitelist,
    unlisted_files: 0,
    locks: quality.locks,
  };
  manifest.privacy_audit = {
    status: "pass_cross_verified",
    report_schema: privacy.report.schema,
    content_fingerprint_excluding_process_manifest_sha256: privacy.fingerprint.sha256,
    file_count_excluding_process_manifest: privacy.fingerprint.file_count,
    directory_count: privacy.fingerprint.directory_count,
    independent_forbidden_hit_count: 0,
    assembly_cross_scan_task_thread_uuid_hits: privacy.crossScan.uuid_hits,
    assembly_cross_scan_machine_path_hits: privacy.crossScan.machine_path_hits,
    report_location: "temporary_outside_delivery",
  };
  upsertGate(manifest, 19, "pass", "Final process inventory is rebuilt after immutable QA artifacts and excludes only process-manifest.json itself");
  upsertGate(manifest, 20, "pass", "Quality directory matches the fixed whitelist; every QA-owned file is hash-locked; independent privacy audit and assembly cross-scan report zero forbidden hits");
  upsertGate(manifest, 21, "pending_post_packaging_QA", "Package is sealed; independent QA has not yet read-only verified the final packaging delta");

  manifest.files = await buildProcessInventory(layout.processRoot, layout.processManifest);
  manifest.process_inventory = {
    listed_file_count: manifest.files.length,
    actual_file_count_excluding_self: manifest.files.length,
    unlisted_files: 0,
    missing_files: 0,
    hash_mismatches: 0,
    self_excluded: true,
  };
  manifest.self_inventory_note = "process-manifest.json is excluded from its own inventory; all other files are frozen before this single seal write";
  await writeFinalManifestAtomic(layout.processManifest, manifest, layout.root);

  const verification = await verifyFinalPackage({ deliveryRoot, privacyReport });
  return { status: "sealed_pending_post_packaging_QA", ...verification };
}

export async function verifyFinalPackage({ deliveryRoot, privacyReport }) {
  const layout = await validateDeliveryLayout(deliveryRoot);
  const quality = await validateQualityDirectory(layout.qualityRoot);
  const privacy = await validateIndependentPrivacyReport(layout.root, privacyReport);
  const manifest = JSON.parse(await fs.readFile(layout.processManifest, "utf8"));
  validateGateSet(manifest, { final: true });
  const files = (await walk(layout.processRoot)).filter((file) => file !== layout.processManifest).sort();
  const listed = new Map((manifest.files ?? []).map((item) => [item.relative_path, item]));
  if ([...listed.keys()].some((relativePath) => path.isAbsolute(relativePath) || path.normalize(relativePath) !== relativePath || relativePath.startsWith(".."))) {
    throw new Error("Process manifest contains a non-canonical or escaping inventory path");
  }
  let hashMismatches = 0;
  for (const file of files) {
    const relativePath = path.relative(layout.processRoot, file);
    const item = listed.get(relativePath);
    const stat = await fs.stat(file);
    if (!item || item.bytes !== stat.size || item.sha256 !== await shaFile(file)) hashMismatches += 1;
  }
  const staleEntries = [...listed.keys()].filter((relativePath) => !files.includes(path.join(layout.processRoot, relativePath))).length;
  if (listed.size !== files.length || hashMismatches || staleEntries) throw new Error("Final process manifest inventory is not closed");
  if (manifest.files?.some((item) => item.relative_path === PROCESS_MANIFEST_NAME)) throw new Error("Process manifest must exclude itself");
  const finalWorkbookLock = manifest.delivery_identity?.final_workbook;
  const finalWorkbookStat = await fs.stat(layout.finalWorkbook);
  if (
    finalWorkbookLock?.relative_path !== layout.finalWorkbookName ||
    finalWorkbookLock?.bytes !== finalWorkbookStat.size ||
    finalWorkbookLock?.sha256 !== await shaFile(layout.finalWorkbook)
  ) {
    throw new Error("Final workbook lock is missing or stale");
  }
  if (manifest.delivery_identity?.qa_status !== "pending_post_packaging_QA") throw new Error("Sealed manifest QA status is invalid");
  if (
    manifest.delivery_identity?.candidate_status !== "incomplete" ||
    manifest.delivery_identity?.delivery_status !== "incomplete" ||
    manifest.delivery_identity?.status !== "incomplete" ||
    manifest.delivery_identity?.p1 !== false ||
    manifest.delivery_status !== "incomplete" ||
    manifest.status !== "incomplete" ||
    manifest.qa_status !== "pending_post_packaging_QA" ||
    manifest.p1 !== false
  ) {
    throw new Error("Sealed package must remain incomplete and P1=false pending final-package QA");
  }
  const inventorySummary = manifest.process_inventory;
  if (
    inventorySummary?.listed_file_count !== files.length ||
    inventorySummary?.actual_file_count_excluding_self !== files.length ||
    inventorySummary?.unlisted_files !== 0 ||
    inventorySummary?.missing_files !== 0 ||
    inventorySummary?.hash_mismatches !== 0 ||
    inventorySummary?.self_excluded !== true
  ) {
    throw new Error("Process manifest inventory summary is missing or stale");
  }

  return {
    verification_status: "pass_read_only",
    process_manifest_sha256: await shaFile(layout.processManifest),
    final_workbook_sha256: await shaFile(layout.finalWorkbook),
    process_inventory_file_count: files.length,
    unlisted_files: 0,
    hash_mismatches: 0,
    stale_manifest_entries: 0,
    quality_directory_whitelist: quality.whitelist,
    privacy_status: "pass_cross_verified",
    content_fingerprint_excluding_process_manifest_sha256: privacy.fingerprint.sha256,
    packaged_directory_count: privacy.fingerprint.directory_count,
    gate_21: "pending_post_packaging_QA",
    delivery_status: "incomplete",
    p1: false,
  };
}

function parseArgs(argv) {
  const output = { command: argv[0] };
  for (let index = 1; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === "--delivery-root") output.deliveryRoot = argv[++index];
    else if (value === "--quarantine-dir") output.quarantineDir = argv[++index];
    else if (value === "--privacy-report") output.privacyReport = argv[++index];
    else if (value === "--help") output.help = true;
    else throw new Error(`Unknown argument: ${value}`);
  }
  return output;
}

async function cli() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || !args.command || !args.deliveryRoot) {
    console.log("Usage:\n  node post-qa-package.mjs prepare --delivery-root <path> --quarantine-dir <outside-path>\n  node post-qa-package.mjs seal --delivery-root <path> --privacy-report <outside-report.json>\n  node post-qa-package.mjs verify-final --delivery-root <path> --privacy-report <outside-report.json>");
    return;
  }
  let result;
  if (args.command === "prepare") {
    if (!args.quarantineDir) throw new Error("prepare requires --quarantine-dir");
    result = await preparePackage(args);
  } else if (args.command === "seal") {
    if (!args.privacyReport) throw new Error("seal requires --privacy-report");
    result = await sealPackage(args);
  } else if (args.command === "verify-final") {
    if (!args.privacyReport) throw new Error("verify-final requires --privacy-report");
    result = await verifyFinalPackage(args);
  } else {
    throw new Error(`Unknown command: ${args.command}`);
  }
  console.log(JSON.stringify(result, null, 2));
}

if (path.resolve(process.argv[1] ?? "") === fileURLToPath(import.meta.url)) {
  cli().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
