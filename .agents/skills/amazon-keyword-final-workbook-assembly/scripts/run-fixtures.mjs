#!/usr/bin/env node

import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";

import { auditDelivery, writeAuditReport } from "./delivery-privacy-audit.mjs";
import { normalizeModuleMetadata } from "./normalize-module-metadata.mjs";
import { preparePackage, sealPackage, verifyFinalPackage } from "./post-qa-package.mjs";

const PROCESS_DIRECTORY_NAME = "过程性文件";
const PARTITIONS = [
  "01_第一板块_来源采集",
  "02_第二板块_品类清洗",
  "03_第三板块_分类与分析",
  "04_独立质量验证",
];
const OFFICE_GUIDS = {
  custom: ["D5CDD505", "2E9C", "101B", "9397", "08002B2CF9AE"].join("-"),
  styles: ["EB79DEF2", "80B8", "43e5", "95BD", "54CBDDF9020C"].join("-"),
  workbook: ["B58B0392", "4F1F", "4190", "BB64", "5DF3571DCE5F"].join("-"),
};

function shaBuffer(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

async function shaFile(file) {
  return shaBuffer(await fs.readFile(file));
}

async function writeJson(file, value) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.writeFile(file, JSON.stringify(value, null, 2) + "\n", "utf8");
}

async function createMiniXlsx(output, options = {}) {
  const staging = await fs.mkdtemp(path.join(path.dirname(output), "xlsx-stage-"));
  try {
    await fs.mkdir(path.join(staging, "docProps"), { recursive: true });
    await fs.mkdir(path.join(staging, "xl", "worksheets"), { recursive: true });
    const workbookGuid = options.structuralGuid ?? OFFICE_GUIDS.workbook;
    await fs.writeFile(
      path.join(staging, "docProps", "custom.xml"),
      `<Properties><property fmtid="{${OFFICE_GUIDS.custom}}"/></Properties>`,
      "utf8",
    );
    await fs.writeFile(
      path.join(staging, "xl", "styles.xml"),
      `<styleSheet><extLst><ext uri="{${OFFICE_GUIDS.styles}}"/></extLst></styleSheet>`,
      "utf8",
    );
    await fs.writeFile(
      path.join(staging, "xl", "workbook.xml"),
      `<workbook><fileVersion codeName="{${workbookGuid}}"/></workbook>`,
      "utf8",
    );
    await fs.writeFile(path.join(staging, "xl", "worksheets", "sheet1.xml"), "<worksheet/>", "utf8");
    if (options.sharedString !== undefined) {
      await fs.writeFile(path.join(staging, "xl", "sharedStrings.xml"), `<sst><si><t>${options.sharedString}</t></si></sst>`, "utf8");
    }
    execFileSync("zip", ["-q", "-r", output, "."], { cwd: staging });
  } finally {
    await fs.rm(staging, { recursive: true, force: true });
  }
}

async function assertAuditFailure(root, resultField) {
  const report = await auditDelivery(root);
  assert.equal(report.status, "fail");
  assert.ok(report.results[resultField] > 0, `${resultField} should be positive`);
}

async function buildLifecycleDelivery(root, taskUuid, safeXlsx, qaMode = "full-regression") {
  const deliveryRoot = path.join(root, `delivery-${qaMode}`);
  const processRoot = path.join(deliveryRoot, PROCESS_DIRECTORY_NAME);
  for (const partition of PARTITIONS) await fs.mkdir(path.join(processRoot, partition), { recursive: true });
  await fs.copyFile(safeXlsx, path.join(deliveryRoot, "AKW-FIXTURE-最终关键词词库.xlsx"));

  const safeShaContainingPrefix = `01a${"b".repeat(61)}`;
  const metadataNames = ["manifest.json", "handoff.json", "verification.json"];
  for (let index = 0; index < 3; index += 1) {
    const partitionRoot = path.join(processRoot, PARTITIONS[index]);
    const artifactName = `module-${index + 1}-artifact.xlsx`;
    await fs.copyFile(safeXlsx, path.join(partitionRoot, artifactName));
    const machineSpecificPath = ["", "Users", "fixture", "runs", taskUuid, artifactName].join("/");
    await writeJson(path.join(partitionRoot, metadataNames[index]), {
      artifact_path: machineSpecificPath,
      artifact_sha256: safeShaContainingPrefix,
      module: `module-${index + 1}`,
    });
  }

  const qualityRoot = path.join(processRoot, PARTITIONS[3]);
  if (qaMode === "compact-production") {
    await writeJson(path.join(qualityRoot, "compact-qa-result.json"), {
      schema: "amazon-keyword-compact-qa/v1",
      qa_mode: qaMode,
      run_id: "AKW-FIXTURE",
      revision: "fixture-revision",
      checker_version: "fixture-checker/v1",
      locked_hashes: { final_workbook: "fixture-locked-before-seal" },
      qa_conclusion: "pass",
      delivery_status: "completed",
      gates: Array.from({ length: 21 }, (_, index) => ({
        Gate_ID: index + 1,
        status: "pass",
        method: "fixture mechanical full-population check",
        population: "fixture locked population",
        actual: "pass",
        evidence: "fixture relative evidence",
      })),
      risk_population: {
        sets: [{ id: "fixture-risk-population", count: 17 }],
        union: 17,
        non_risk: 83,
        total: 100,
        uncovered: 0,
      },
    });
  } else {
    const qualityWorkbook = path.join(qualityRoot, "独立质量验证.xlsx");
    await fs.copyFile(safeXlsx, qualityWorkbook);
    const previewRoot = path.join(qualityRoot, "independent-qa-previews");
    await fs.mkdir(previewRoot, { recursive: true });
    const previews = [];
    for (let index = 1; index <= 8; index += 1) {
      const name = `sheet-${String(index).padStart(2, "0")}.png`;
      const file = path.join(previewRoot, name);
      const body = Buffer.from(`fixture-preview-${index}`, "utf8");
      await fs.writeFile(file, body);
      previews.push({ relative_path: `independent-qa-previews/${name}`, bytes: body.length, sha256: shaBuffer(body) });
    }
    const issueReference = path.join(qualityRoot, "issue-reference.json");
    await writeJson(issueReference, { issue_register: "canonical-run-issue-register", issue_count: 7 });
    await writeJson(path.join(qualityRoot, "quality-manifest.json"), {
      schema: "fixture-quality-manifest/v1",
      qa_mode: qaMode,
      qa_conclusion: "pass",
      delivery_status: "completed",
      quality_workbook: { relative_path: "独立质量验证.xlsx", sha256: await shaFile(qualityWorkbook) },
      previews,
      issue_reference: { relative_path: "issue-reference.json", sha256: await shaFile(issueReference) },
      gates: { passed: 21, failed: 0, not_executed: 0, not_applicable: 0, total: 21 },
    });
  }

  for (const name of ["QA_INPUT.md", "assembly-manifest.json", "handoff.json", "verification.json", "independent-qa-status.json"]) {
    await fs.writeFile(path.join(qualityRoot, name), "fixture assembly placeholder\n", "utf8");
  }
  await fs.mkdir(path.join(qualityRoot, "checks"), { recursive: true });
  await fs.mkdir(path.join(qualityRoot, "previews"), { recursive: true });
  await fs.writeFile(path.join(qualityRoot, "checks", "assembly-check.txt"), "candidate only\n", "utf8");
  await fs.writeFile(path.join(qualityRoot, "previews", "assembly-preview.png"), "candidate only\n", "utf8");

  await writeJson(path.join(processRoot, "process-manifest.json"), {
    schema: "fixture-process-manifest/v1",
    qa_mode: qaMode,
    delivery_identity: { candidate_status: "incomplete", qa_status: "pending_quality_validation", p1: false },
    gates: Array.from({ length: 21 }, (_, index) => ({
      id: index + 1,
      status: index === 20 ? "pending_quality_validation" : "pass",
    })),
    files: [],
  });
  return deliveryRoot;
}

async function main() {
  const fixtureRoot = await fs.mkdtemp(path.join(os.tmpdir(), "amazon-keyword-assembly-fixture-"));
  const taskUuid = ["01234567", "89ab", "cdef", "0123", "456789abcdef"].join("-");
  const otherUuid = ["fedcba98", "7654", "3210", "fedc", "ba9876543210"].join("-");
  const tests = [];
  try {
    const safeRoot = path.join(fixtureRoot, "safe-audit");
    await fs.mkdir(safeRoot, { recursive: true });
    await fs.writeFile(path.join(safeRoot, "sha.json"), JSON.stringify({ sha256: `01a${"c".repeat(61)}` }), "utf8");
    const safeXlsx = path.join(safeRoot, "safe.xlsx");
    await createMiniXlsx(safeXlsx);
    const safeReport = await auditDelivery(safeRoot);
    assert.equal(safeReport.status, "pass");
    assert.equal(safeReport.results.generic_01a_matcher_used, false);
    assert.equal(safeReport.results.sha256_tokens_containing_01a, 1);
    assert.equal(safeReport.results.office_internal_guid_occurrences, 3);
    tests.push("ordinary SHA-256 and exact Office structural GUID allowlist pass");

    const textUuidRoot = path.join(fixtureRoot, "text-uuid");
    await fs.mkdir(textUuidRoot);
    await fs.writeFile(path.join(textUuidRoot, "manifest.json"), JSON.stringify({ task: taskUuid }), "utf8");
    await assertAuditFailure(textUuidRoot, "task_thread_uuid_hits_in_text_or_binary");
    tests.push("full task/thread UUID in text fails");

    const pathUuidRoot = path.join(fixtureRoot, "path-uuid");
    await fs.mkdir(pathUuidRoot);
    await fs.mkdir(path.join(pathUuidRoot, taskUuid));
    await assertAuditFailure(pathUuidRoot, "task_thread_uuid_hits_in_file_paths");
    tests.push("full task/thread UUID in a packaged path fails");

    const xlsxUuidRoot = path.join(fixtureRoot, "xlsx-uuid");
    await fs.mkdir(xlsxUuidRoot);
    await createMiniXlsx(path.join(xlsxUuidRoot, "business-string.xlsx"), { sharedString: taskUuid });
    await assertAuditFailure(xlsxUuidRoot, "task_thread_uuid_hits_in_xlsx_business_strings");
    tests.push("full task/thread UUID in XLSX business strings fails");

    const xlsxPathRoot = path.join(fixtureRoot, "xlsx-path");
    await fs.mkdir(xlsxPathRoot);
    await createMiniXlsx(path.join(xlsxPathRoot, "machine-path.xlsx"), {
      sharedString: ["", "Users", "fixture", "runs", taskUuid, "evidence.json"].join("/"),
    });
    await assertAuditFailure(xlsxPathRoot, "machine_absolute_path_hits_in_xlsx");
    tests.push("machine absolute path in XLSX fails");

    const structuralRoot = path.join(fixtureRoot, "structural-uuid");
    await fs.mkdir(structuralRoot);
    await createMiniXlsx(path.join(structuralRoot, "unknown-guid.xlsx"), { structuralGuid: otherUuid });
    await assertAuditFailure(structuralRoot, "ooxml_non_allowlisted_uuid_hits");
    tests.push("non-allowlisted OOXML UUID fails");

    const deliveryRoot = await buildLifecycleDelivery(fixtureRoot, taskUuid, safeXlsx, "full-regression");
    const normalization = await normalizeModuleMetadata(deliveryRoot);
    assert.equal(normalization.partitions_scanned, 3);
    assert.equal(normalization.metadata_files_scanned, 3);
    assert.equal(normalization.rewritten_values, 3);
    for (let index = 0; index < 3; index += 1) {
      const manifest = JSON.parse(await fs.readFile(path.join(deliveryRoot, PROCESS_DIRECTORY_NAME, PARTITIONS[index], ["manifest.json", "handoff.json", "verification.json"][index]), "utf8"));
      assert.equal(manifest.artifact_path, `module-${index + 1}-artifact.xlsx`);
    }
    tests.push("every module partition rebases unsafe metadata paths to stable local relative paths");

    const quarantineDir = path.join(fixtureRoot, "assembly-placeholder-quarantine");
    const prepared = await preparePackage({ deliveryRoot, quarantineDir, qaMode: "full-regression" });
    assert.equal(prepared.moved_assembly_owned_entries.length, 7);
    assert.deepEqual(prepared.quality_directory_whitelist, [
      "independent-qa-previews",
      "issue-reference.json",
      "quality-manifest.json",
      "独立质量验证.xlsx",
    ]);
    const preparedAgain = await preparePackage({ deliveryRoot, quarantineDir, qaMode: "full-regression" });
    assert.equal(preparedAgain.moved_assembly_owned_entries.length, 0);
    tests.push("post-QA prepare removes all assembly-owned QA placeholders into outside recovery quarantine");

    const privacyReport = path.join(fixtureRoot, "independent-privacy-report.json");
    const audit = await writeAuditReport(deliveryRoot, privacyReport);
    assert.equal(audit.status, "pass");
    assert.equal(audit.results.forbidden_hit_count, 0);
    const sealed = await sealPackage({ deliveryRoot, privacyReport, qaMode: "full-regression" });
    assert.equal(sealed.gate_21, "pending_post_packaging_QA");
    assert.equal(sealed.unlisted_files, 0);
    const verified = await verifyFinalPackage({ deliveryRoot, privacyReport, qaMode: "full-regression" });
    assert.equal(verified.verification_status, "pass_read_only");
    const processManifestPath = path.join(deliveryRoot, PROCESS_DIRECTORY_NAME, "process-manifest.json");
    const processManifest = JSON.parse(await fs.readFile(processManifestPath, "utf8"));
    assert.equal(processManifest.process_inventory.self_excluded, true);
    assert.equal(processManifest.delivery_identity.final_workbook.sha256, await shaFile(path.join(deliveryRoot, "AKW-FIXTURE-最终关键词词库.xlsx")));
    assert.equal(processManifest.gates.length, 21);
    assert.equal(processManifest.gates.find((gate) => gate.id === 21).status, "pending_post_packaging_QA");
    tests.push("seal closes hashes without self-hash and read-only verification preserves pending Gate 21");

    const rogueFile = path.join(deliveryRoot, PROCESS_DIRECTORY_NAME, PARTITIONS[0], "unlisted.txt");
    await fs.writeFile(rogueFile, "rogue", "utf8");
    await assert.rejects(() => verifyFinalPackage({ deliveryRoot, privacyReport, qaMode: "full-regression" }));
    await fs.rm(rogueFile);
    const rogueDirectory = path.join(deliveryRoot, PROCESS_DIRECTORY_NAME, PARTITIONS[0], "unlisted-empty-directory");
    await fs.mkdir(rogueDirectory);
    await assert.rejects(() => verifyFinalPackage({ deliveryRoot, privacyReport, qaMode: "full-regression" }));
    await fs.rmdir(rogueDirectory);
    await verifyFinalPackage({ deliveryRoot, privacyReport, qaMode: "full-regression" });
    tests.push("unlisted final-package file is rejected with zero-tolerance");

    const compactDeliveryRoot = await buildLifecycleDelivery(fixtureRoot, taskUuid, safeXlsx, "compact-production");
    await normalizeModuleMetadata(compactDeliveryRoot);
    const compactQuarantine = path.join(fixtureRoot, "compact-placeholder-quarantine");
    const compactPrepared = await preparePackage({ deliveryRoot: compactDeliveryRoot, quarantineDir: compactQuarantine, qaMode: "compact-production" });
    assert.deepEqual(compactPrepared.quality_directory_whitelist, ["compact-qa-result.json"]);
    const compactPrivacyReport = path.join(fixtureRoot, "compact-privacy-report.json");
    await writeAuditReport(compactDeliveryRoot, compactPrivacyReport);
    await sealPackage({ deliveryRoot: compactDeliveryRoot, privacyReport: compactPrivacyReport, qaMode: "compact-production" });
    const compactVerified = await verifyFinalPackage({ deliveryRoot: compactDeliveryRoot, privacyReport: compactPrivacyReport, qaMode: "compact-production" });
    assert.equal(compactVerified.qa_mode, "compact-production");
    tests.push("compact-production accepts only compact result and preserves the same sealed hash and privacy gates");

    const compactMissingGateRoot = await buildLifecycleDelivery(path.join(fixtureRoot, "compact-missing-gate"), taskUuid, safeXlsx, "compact-production");
    const compactMissingGateResult = path.join(compactMissingGateRoot, PROCESS_DIRECTORY_NAME, PARTITIONS[3], "compact-qa-result.json");
    const missingGatePayload = JSON.parse(await fs.readFile(compactMissingGateResult, "utf8"));
    missingGatePayload.gates.pop();
    await writeJson(compactMissingGateResult, missingGatePayload);
    await assert.rejects(() => preparePackage({
      deliveryRoot: compactMissingGateRoot,
      quarantineDir: path.join(fixtureRoot, "compact-missing-gate-quarantine"),
      qaMode: "compact-production",
    }));
    tests.push("compact-production rejects a missing Gate ID instead of silently shrinking the 21-gate contract");

    const compactRiskGapRoot = await buildLifecycleDelivery(path.join(fixtureRoot, "compact-risk-gap"), taskUuid, safeXlsx, "compact-production");
    const compactRiskGapResult = path.join(compactRiskGapRoot, PROCESS_DIRECTORY_NAME, PARTITIONS[3], "compact-qa-result.json");
    const riskGapPayload = JSON.parse(await fs.readFile(compactRiskGapResult, "utf8"));
    riskGapPayload.risk_population.uncovered = 1;
    await writeJson(compactRiskGapResult, riskGapPayload);
    await assert.rejects(() => preparePackage({
      deliveryRoot: compactRiskGapRoot,
      quarantineDir: path.join(fixtureRoot, "compact-risk-gap-quarantine"),
      qaMode: "compact-production",
    }));
    tests.push("compact-production rejects any uncovered semantic-risk population");

    const compactDuplicateArtifactRoot = await buildLifecycleDelivery(path.join(fixtureRoot, "compact-duplicate-artifact"), taskUuid, safeXlsx, "compact-production");
    await fs.copyFile(safeXlsx, path.join(compactDuplicateArtifactRoot, PROCESS_DIRECTORY_NAME, PARTITIONS[3], "独立质量验证.xlsx"));
    await assert.rejects(() => preparePackage({
      deliveryRoot: compactDuplicateArtifactRoot,
      quarantineDir: path.join(fixtureRoot, "compact-duplicate-artifact-quarantine"),
      qaMode: "compact-production",
    }));
    tests.push("compact-production rejects duplicate full-regression artifacts");

    console.log(JSON.stringify({ status: "pass", test_count: tests.length, tests }, null, 2));
  } finally {
    await fs.rm(fixtureRoot, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error.stack ?? error.message);
  process.exitCode = 1;
});
