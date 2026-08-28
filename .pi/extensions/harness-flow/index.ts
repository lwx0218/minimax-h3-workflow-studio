import { createHash, randomUUID } from "node:crypto";
import { spawn } from "node:child_process";
import { createReadStream, existsSync } from "node:fs";
import { lstat, mkdtemp, readFile, readlink, realpath, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, dirname, isAbsolute, join, posix, relative, resolve, sep } from "node:path";
import { StringEnum } from "@earendil-works/pi-ai";
import type {
	ExtensionAPI,
	ExtensionContext,
	ReplacedSessionContext,
} from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const EXTENSION_NAME = "harness-flow";
const READ_ONLY_TOOLS = ["read", "grep", "find", "ls"] as const;
const MAX_CAPTURE_BYTES = 5 * 1024 * 1024;
const MAX_REVIEW_OUTPUT_BYTES = 512 * 1024;
const HANDOFF_TTL_MS = 10 * 60 * 1000;
const REVIEW_MARKER = "HARNESS_REVIEW_RESULT";

interface PendingHandoff {
	createdAt: number;
	parentSession: string;
	sessionName: string;
	roundId: string;
	prompt: string;
	fallback: string;
}

interface RoundHandoffContract {
	contractPaths: string[];
	latestWorkLog?: string;
	latestReview?: string;
	reviewWorkLog: string;
	nonGoals: string[];
	dependencies: string[];
	expectedChangeSurfaces: string[];
	validation: string[];
	reviewMode: string;
	roundReviewArtifact: string;
	finalReviewArtifact: string;
	acceptanceEvidence: string[];
	nextGate: string;
	blockersAndAssumptions: string[];
	blockedConditions: string[];
}

interface PlanRound {
	sessionName: string;
	deliveryBoundary: string;
	acceptanceEvidence: string;
	status: "pending" | "in_progress" | "blocked" | "accepted";
}

interface GitSnapshot {
	head: string;
	status: string;
	statusHash: string;
	candidateHash: string;
	candidatePaths: string[];
}

interface ReviewFinding {
	severity: "P0" | "P1" | "P2";
	summary: string;
	evidence: string;
}

interface ParsedReview {
	decision: "pass" | "changes_required" | "blocked";
	findings: ReviewFinding[];
	limitations: string[];
}

interface ProcessResult {
	pid?: number;
	code: number | null;
	signal: NodeJS.Signals | null;
	stdout: string;
	stderr: string;
	timedOut: boolean;
	aborted: boolean;
	truncated: boolean;
	durationMs: number;
}

function textResult(text: string, details: unknown = {}) {
	return { content: [{ type: "text" as const, text }], details };
}

function sha256(value: string | Buffer): string {
	return createHash("sha256").update(value).digest("hex");
}

function isInside(root: string, candidate: string): boolean {
	const rel = relative(root, candidate);
	return rel === "" || (!rel.startsWith(`..${sep}`) && rel !== ".." && !isAbsolute(rel));
}

function normalizeRelativePath(input: string): string | undefined {
	const value = input.trim().replace(/^@/, "");
	if (!value || isAbsolute(value) || value.includes("\0")) return undefined;
	const normalized = value.replaceAll("\\", "/").replace(/^\.\//, "");
	if (/^[A-Za-z]:\//.test(normalized)) return undefined;
	const canonical = posix.normalize(normalized);
	if (canonical === ".." || canonical.startsWith("../") || canonical.includes("/../")) return undefined;
	return canonical;
}

async function assertNoSymlinkComponents(root: string, absolute: string, includeLeaf: boolean): Promise<void> {
	const rel = relative(root, absolute);
	const parts = rel.split(sep).filter(Boolean);
	let current = root;
	for (const [index, part] of parts.entries()) {
		if (!includeLeaf && index === parts.length - 1) break;
		current = join(current, part);
		if ((await lstat(current)).isSymbolicLink()) throw new Error("project path contains a symlink component");
	}
}

async function resolveExistingProjectFile(cwd: string, input: string): Promise<{ relativePath: string; absolutePath: string }> {
	const relativePath = normalizeRelativePath(input);
	if (!relativePath) throw new Error(`Path must be repository-relative: ${input}`);
	const root = await realpath(cwd);
	const lexical = resolve(root, relativePath);
	if (!isInside(root, lexical)) throw new Error(`Path escapes the project root: ${input}`);
	await assertNoSymlinkComponents(root, lexical, true);
	const info = await lstat(lexical);
	if (!info.isFile() || info.isSymbolicLink()) throw new Error(`Path must be a regular non-symlink file: ${input}`);
	const absolutePath = await realpath(lexical);
	if (!isInside(root, absolutePath)) throw new Error(`Resolved path escapes the project root: ${input}`);
	return { relativePath, absolutePath };
}

async function validateFutureProjectPath(cwd: string, input: string, requiredPrefix: string): Promise<string> {
	const relativePath = normalizeRelativePath(input);
	if (!relativePath || !relativePath.startsWith(requiredPrefix) || !relativePath.endsWith(".md")) {
		throw new Error(`Expected a repository-relative Markdown path under ${requiredPrefix}`);
	}
	const root = await realpath(cwd);
	const absolute = resolve(root, relativePath);
	if (!isInside(root, absolute)) throw new Error("future project path escapes the project root");
	await assertNoSymlinkComponents(root, dirname(absolute), true);
	const physicalParent = await realpath(dirname(absolute));
	if (!isInside(root, physicalParent)) throw new Error("future project path parent escapes the project root");
	try {
		const leaf = await lstat(absolute);
		if (leaf.isSymbolicLink() || !leaf.isFile()) throw new Error("existing future artifact leaf must be a regular non-symlink file");
		const physicalLeaf = await realpath(absolute);
		if (!isInside(root, physicalLeaf)) throw new Error("existing future artifact leaf escapes the project root");
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
	}
	return relativePath;
}

function stripMarkdown(value: string): string {
	return value.trim().replace(/^`|`$/g, "").replace(/\*\*/g, "").trim();
}

function parsePlanRound(plan: string, roundId: string): PlanRound | undefined {
	const matches: PlanRound[] = [];
	for (const line of plan.split(/\r?\n/)) {
		if (!line.trim().startsWith("|")) continue;
		const cells = line.split("|").slice(1, -1).map(stripMarkdown);
		if (cells[0] !== roundId || !cells[1] || /^primary implementation session$/i.test(cells[1])) continue;
		const status = cells.at(-1);
		if (!status || !["pending", "in_progress", "blocked", "accepted"].includes(status) || cells.length < 5 || !cells[2] || !cells[3]) return undefined;
		matches.push({ sessionName: cells[1], deliveryBoundary: cells[2], acceptanceEvidence: cells.slice(3, -1).join(" | "), status: status as PlanRound["status"] });
	}
	return matches.length === 1 ? matches[0] : undefined;
}

function planMetadataPreamble(plan: string): string {
	const headings = [...plan.matchAll(/^##\s+(.+?)\s*$/gm)];
	if (headings.filter((heading) => /^(Metadata|Gate)$/i.test(heading[1])).length > 1) return "";
	if (headings.length === 0) return plan;
	if (/^(Metadata|Gate)$/i.test(headings[0][1])) {
		return plan.slice(0, headings[1]?.index ?? plan.length);
	}
	return plan.slice(0, headings[0].index);
}

function planIsApproved(plan: string): boolean {
	const matches = [...plan.matchAll(/^\s*(?:[-*]\s*)?Plan approval\s*:\s*`?([^`\s]+)`?\s*$/gim)];
	if (matches.length !== 1 || matches[0][1].toLowerCase() !== "approved") return false;
	return (matches[0].index ?? plan.length) < planMetadataPreamble(plan).length;
}

function normalizedEvidence(value: string): string {
	return stripMarkdown(value).replace(/[`*_#]/g, "").replace(/\s+/g, " ").trim().toLowerCase();
}

function extractRoundSection(plan: string, roundId: string): string | undefined {
	const headings = [...plan.matchAll(/^##\s+(.+?)\s*$/gm)];
	const matches = headings.map((heading, index) => ({ heading, index })).filter(({ heading }) => new RegExp(`^${roundId}(?:\\s|\\b|—|-)`, "i").test(heading[1]));
	if (matches.length !== 1) return undefined;
	const match = matches[0];
	const start = match.heading.index ?? 0;
	const end = headings[match.index + 1]?.index ?? plan.length;
	return plan.slice(start, end);
}

function parseContractList(value: string, field: string): string[] {
	const items = value.split(";").map(stripMarkdown).filter(Boolean);
	if (items.length === 0 || items.length > 20) throw new Error(`${field} must declare 1-20 semicolon-separated values`);
	for (const item of items) if (item.length > 1200) throw new Error(`${field} item exceeds 1200 characters`);
	return items;
}

function extractRoundField(section: string, label: string): string {
	const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
	const matches = [...section.matchAll(new RegExp(`^\\s*[-*]\\s*${escaped}\\s*:\\s*(.+?)\\s*$`, "gim"))];
	if (matches.length !== 1 || !matches[0][1].trim()) throw new Error(`owning Round must declare exactly one ${label}`);
	return stripMarkdown(matches[0][1]);
}

function optionalEvidencePath(value: string): string | undefined {
	const normalized = stripMarkdown(value);
	return /^none$/i.test(normalized) ? undefined : normalized;
}

function parseRoundHandoffContract(section: string): RoundHandoffContract {
	const contract: RoundHandoffContract = {
		contractPaths: parseContractList(extractRoundField(section, "Handoff contracts"), "Handoff contracts"),
		latestWorkLog: optionalEvidencePath(extractRoundField(section, "Latest work log")),
		latestReview: optionalEvidencePath(extractRoundField(section, "Latest review")),
		reviewWorkLog: extractRoundField(section, "Review work log"),
		nonGoals: parseContractList(extractRoundField(section, "Non-goals"), "Non-goals"),
		dependencies: parseContractList(extractRoundField(section, "Dependencies / Definition of Ready"), "Dependencies / Definition of Ready"),
		expectedChangeSurfaces: parseContractList(extractRoundField(section, "Expected change surfaces"), "Expected change surfaces"),
		validation: parseContractList(extractRoundField(section, "Exact validation strategy"), "Exact validation strategy"),
		reviewMode: extractRoundField(section, "Independent Review mode"),
		roundReviewArtifact: extractRoundField(section, "Round review"),
		finalReviewArtifact: extractRoundField(section, "Final integrated review"),
		acceptanceEvidence: parseContractList(extractRoundField(section, "Acceptance evidence"), "Acceptance evidence"),
		nextGate: extractRoundField(section, "Exact next gate"),
		blockersAndAssumptions: parseContractList(extractRoundField(section, "Blockers / assumptions"), "Blockers / assumptions"),
		blockedConditions: parseContractList(extractRoundField(section, "Blocked / rebaseline conditions"), "Blocked / rebaseline conditions"),
	};
	if (!["spawned_pi_process", "human_review"].includes(contract.reviewMode)) throw new Error("Independent Review mode must be spawned_pi_process or human_review");
	const roundArtifact = normalizeRelativePath(contract.roundReviewArtifact);
	const finalArtifact = normalizeRelativePath(contract.finalReviewArtifact);
	if (!roundArtifact || !finalArtifact || roundArtifact === finalArtifact) throw new Error("Round and final integrated Review artifacts must be distinct canonical paths");
	return contract;
}

function extractUniqueMetadata(text: string, label: string): string | undefined {
	const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
	const matches = [...planMetadataPreamble(text).matchAll(new RegExp(`^\\s*(?:[-*]\\s*)?${escaped}\\s*:\\s*(.+?)\\s*$`, "gim"))];
	return matches.length === 1 ? stripMarkdown(matches[0][1]) : undefined;
}

function extractBaseline(text: string): string | undefined {
	const value = extractUniqueMetadata(text, "Git baseline");
	return value && /^(?:[0-9a-f]{7,40}|[0-9a-f]{64})$/.test(value) ? value : undefined;
}

function acceptedEffectiveRounds(plan: string): Set<string> | undefined {
	const value = extractUniqueMetadata(plan, "Accepted-effective Rounds");
	if (!value) return undefined;
	if (/^none$/i.test(value)) return new Set();
	const ids = value.split(/[,;]\s*/).filter(Boolean);
	if (ids.some((id) => !/^R[1-9]\d*$/.test(id)) || new Set(ids).size !== ids.length) return undefined;
	return new Set(ids);
}

function assertEffectiveRoundSet(plan: string, activeRound: string): Set<string> {
	const ids = parsePlanRoundIds(plan);
	if (new Set(ids).size !== ids.length) throw new Error("Round Ledger contains duplicate Round IDs");
	const activeIndex = ids.indexOf(activeRound);
	if (activeIndex < 0) throw new Error(`active Round ${activeRound} is not in the Ledger`);
	const expected = ids.slice(0, activeIndex).filter((id) => parsePlanRound(plan, id)?.status === "accepted");
	const effective = acceptedEffectiveRounds(plan);
	if (!effective || effective.size !== expected.length || expected.some((id) => !effective.has(id))) {
		throw new Error("Accepted-effective Rounds metadata must exactly equal accepted prior Ledger Rounds");
	}
	return effective;
}

function parsePlanRoundIds(plan: string): string[] {
	const ids: string[] = [];
	for (const line of plan.split(/\r?\n/)) {
		if (!line.trim().startsWith("|")) continue;
		const first = stripMarkdown(line.split("|")[1] ?? "");
		if (/^R[1-9]\d*$/.test(first)) ids.push(first);
	}
	return ids;
}

function modelOutputPreview(value: string): string {
	const lines = value.split(/\r?\n/);
	let preview = lines.slice(0, 1000).join("\n");
	while (Buffer.byteLength(preview, "utf8") > 12 * 1024) preview = preview.slice(0, Math.floor(preview.length * 0.9));
	if (preview !== value) preview += "\n[Reviewer stdout truncated in model-visible content; full bounded capture is in tool details.]";
	return preview;
}

function validateRoundId(roundId: string): void {
	if (!/^R[1-9]\d*$/.test(roundId)) throw new Error(`Invalid fixed Round ID: ${roundId}`);
}

function validateSessionName(roundId: string, sessionName: string): void {
	if (!/^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$/.test(sessionName) || !sessionName.startsWith(`${roundId}-`)) {
		throw new Error(`Invalid declared session name for ${roundId}`);
	}
}

function redactSecrets(value: string): string {
	return value
		.replace(/\b(?:sk|ghp|github_pat|glpat)-?[A-Za-z0-9_-]{16,}\b/g, "<redacted-secret>")
		.replace(/\bBearer\s+[A-Za-z0-9._~+\/-]{16,}/gi, "Bearer <redacted-secret>")
		.replace(/\b(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+/gi, "$1=<redacted-secret>");
}

function bullets(values: string[], empty = "None declared"): string {
	return values.length > 0 ? values.map((value) => `- ${value}`).join("\n") : `- ${empty}`;
}

function buildHandoffPrompt(input: {
	planPath: string;
	roundId: string;
	sessionName: string;
	target: string;
	contractPaths: string[];
	latestWorkLog?: string;
	latestReview?: string;
	nonGoals: string[];
	dependencies: string[];
	expectedChangeSurfaces: string[];
	blockersAndAssumptions: string[];
	validation: string[];
	reviewMode: string;
	reviewArtifactPath: string;
	finalReviewArtifactPath: string;
	acceptanceEvidence: string[];
	nextGate: string;
	blockedConditions: string[];
}): string {
	const durable = [
		...input.contractPaths,
		input.planPath,
		...(input.latestWorkLog ? [input.latestWorkLog] : []),
		...(input.latestReview ? [input.latestReview] : []),
	];
	return redactSecrets(`# ${input.sessionName}\n\nThis is a new implementation session. Chat history is not the durable source of truth.\n\n## Read First\n${bullets(durable)}\n\n## Active Boundary\n- Round: ${input.roundId}\n- Declared primary implementation session: ${input.sessionName}\n- Bounded target: ${input.target}\n- Round is the only acceptance-bearing unit.\n\n## Non-Goals\n${bullets(input.nonGoals)}\n\n## Dependencies / Definition Of Ready\n${bullets(input.dependencies)}\n\n## Expected Change Surfaces\n${bullets(input.expectedChangeSurfaces)}\n\n## Blockers And Assumptions\n${bullets(input.blockersAndAssumptions)}\n\n## Exact Validation\n${bullets(input.validation)}\n\n## Independent Review\n- Mode: ${input.reviewMode}\n- Per-Round artifact (written by the Builder, never the review child): ${input.reviewArtifactPath}\n- Final integrated artifact (last Round only): ${input.finalReviewArtifactPath}\n- After automated verification, automatically call harness_run_independent_review. P0/P1 remains in ${input.roundId} through Fix -> Verify -> Re-review; disposition every P2.\n\n## Acceptance Evidence\n${bullets(input.acceptanceEvidence)}\n\n## Next Gate\n${input.nextGate}\n\n## Blocked / Rebaseline Conditions\n${bullets(input.blockedConditions)}\n\nDo not expand scope, create Phase acceptance, or create a letter-suffixed Round. Do not claim accepted before required Review, acceptance commit, and post-commit verification. Do not push unless explicitly instructed.`);
}

function manualHandoff(sessionName: string, prompt: string): string {
	return `/session\n/new\n/name ${sessionName}\n\n${prompt}`;
}

function cleanupPending(pending: Map<string, PendingHandoff>): void {
	const cutoff = Date.now() - HANDOFF_TTL_MS;
	for (const [token, item] of pending) if (item.createdAt < cutoff) pending.delete(token);
}

function getPiInvocation(args: string[]): { command: string; args: string[]; displayCommand: string } {
	const currentScript = process.argv[1];
	const isBunVirtualScript = currentScript?.startsWith("/$bunfs/root/");
	if (currentScript && !isBunVirtualScript && existsSync(currentScript)) {
		return { command: process.execPath, args: [currentScript, ...args], displayCommand: "pi" };
	}
	const executable = basename(process.execPath).toLowerCase();
	if (!/^(node|bun)(\.exe)?$/.test(executable)) {
		return { command: process.execPath, args, displayCommand: "pi" };
	}
	return { command: "pi", args, displayCommand: "pi" };
}

function buildReviewerEnv(auth: { apiKey?: string; env?: Record<string, string> }): NodeJS.ProcessEnv {
	const safeNames = new Set([
		"PATH", "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "TEMP", "TMP", "SystemRoot", "WINDIR",
		"LANG", "TZ", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS",
		"PI_CODING_AGENT_DIR", "PI_PACKAGE_DIR",
	]);
	const env: NodeJS.ProcessEnv = {};
	for (const [key, value] of Object.entries(process.env)) {
		if (value !== undefined && (safeNames.has(key) || key.startsWith("LC_") || (auth.apiKey !== undefined && value === auth.apiKey))) env[key] = value;
	}
	for (const [key, value] of Object.entries(auth.env ?? {})) env[key] = value;
	env.PI_SKIP_VERSION_CHECK = "1";
	return env;
}

function runProcess(
	command: string,
	args: string[],
	options: {
		cwd: string;
		env?: NodeJS.ProcessEnv;
		timeoutMs: number;
		signal?: AbortSignal;
		maxBytes: number;
	},
): Promise<ProcessResult> {
	return new Promise((done) => {
		const started = Date.now();
		let stdout = Buffer.alloc(0);
		let stderr = Buffer.alloc(0);
		let truncated = false;
		let timedOut = false;
		let aborted = false;
		let settled = false;
		let killTimer: NodeJS.Timeout | undefined;
		const child = spawn(command, args, {
			cwd: options.cwd,
			env: options.env ?? process.env,
			shell: false,
			stdio: ["ignore", "pipe", "pipe"],
		});

		const append = (current: Buffer, chunk: Buffer): Buffer => {
			if (current.length >= options.maxBytes) {
				truncated = true;
				return current;
			}
			const remaining = options.maxBytes - current.length;
			if (chunk.length > remaining) truncated = true;
			return Buffer.concat([current, chunk.subarray(0, remaining)]);
		};
		child.stdout?.on("data", (chunk: Buffer) => { stdout = append(stdout, chunk); });
		child.stderr?.on("data", (chunk: Buffer) => { stderr = append(stderr, chunk); });

		const terminate = () => {
			if (child.exitCode !== null || child.killed) return;
			child.kill("SIGTERM");
			killTimer = setTimeout(() => child.kill("SIGKILL"), 3000);
		};
		const timeout = setTimeout(() => { timedOut = true; terminate(); }, options.timeoutMs);
		const onAbort = () => { aborted = true; terminate(); };
		if (options.signal?.aborted) onAbort();
		else options.signal?.addEventListener("abort", onAbort, { once: true });

		const finish = (code: number | null, signal: NodeJS.Signals | null) => {
			if (settled) return;
			settled = true;
			clearTimeout(timeout);
			if (killTimer) clearTimeout(killTimer);
			options.signal?.removeEventListener("abort", onAbort);
			done({
				pid: child.pid,
				code,
				signal,
				stdout: stdout.toString("utf8"),
				stderr: stderr.toString("utf8"),
				timedOut,
				aborted,
				truncated,
				durationMs: Date.now() - started,
			});
		};
		child.on("error", (error) => {
			stderr = append(stderr, Buffer.from(error.message));
			finish(null, null);
		});
		child.on("close", finish);
	});
}

async function runGit(cwd: string, args: string[], maxBytes = MAX_CAPTURE_BYTES): Promise<string> {
	const result = await runProcess("git", args, { cwd, timeoutMs: 30_000, maxBytes });
	if (result.code !== 0 || result.truncated) {
		throw new Error(`git ${args[0]} failed${result.truncated ? " (output truncated)" : ""}: ${result.stderr.trim()}`);
	}
	if (result.stdout.includes("\uFFFD")) throw new Error(`git ${args[0]} returned a non-UTF-8 path or payload; fail closed`);
	return result.stdout;
}

function nulList(value: string): string[] {
	return value.split("\0").filter(Boolean);
}

async function hashCandidateFile(hash: ReturnType<typeof createHash>, path: string, expectedSize: number): Promise<void> {
	if (expectedSize > 20 * 1024 * 1024) throw new Error(`candidate file exceeds 20 MiB hash boundary: ${path}`);
	await new Promise<void>((done, fail) => {
		let bytes = 0;
		const stream = createReadStream(path);
		stream.on("data", (chunk: Buffer) => {
			bytes += chunk.length;
			if (bytes > 20 * 1024 * 1024) { stream.destroy(new Error(`candidate file grew beyond 20 MiB hash boundary: ${path}`)); return; }
			hash.update(chunk);
		});
		stream.on("error", fail);
		stream.on("end", () => bytes === expectedSize ? done() : fail(new Error(`candidate file size changed during snapshot: ${path}`)));
	});
}

async function captureGitSnapshot(cwd: string, additionalPaths: string[] = []): Promise<GitSnapshot> {
	const head = (await runGit(cwd, ["rev-parse", "HEAD"])).trim();
	const status = await runGit(cwd, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]);
	const changed = nulList(await runGit(cwd, ["diff", "--name-only", "-z", "HEAD", "--"]));
	const untracked = nulList(await runGit(cwd, ["ls-files", "--others", "--exclude-standard", "-z"]));
	const candidatePaths = [...new Set([...changed, ...untracked, ...additionalPaths])].sort();
	const hash = createHash("sha256").update(head).update("\0").update(status);
	let totalBytes = 0;
	for (const path of candidatePaths) {
		hash.update("\0").update(path).update("\0");
		const absolute = resolve(cwd, path);
		let info;
		try { info = await lstat(absolute); }
		catch { hash.update("<missing>"); continue; }
		hash.update(`type:${info.mode & 0o170000};mode:${info.mode & 0o7777};size:${info.size};`);
		if (info.isSymbolicLink()) hash.update(`symlink:${await readlink(absolute)}`);
		else if (info.isFile()) {
			totalBytes += info.size;
			if (totalBytes > 50 * 1024 * 1024) throw new Error("candidate files exceed 50 MiB aggregate hash boundary");
			await hashCandidateFile(hash, absolute, info.size);
		}
		else if (info.isDirectory()) throw new Error(`directory/gitlink candidate requires an OS-isolated or distinct-human review fallback: ${path}`);
		else throw new Error(`unsupported candidate file type: ${path}`);
	}
	return { head, status, statusHash: sha256(status), candidateHash: hash.digest("hex"), candidatePaths };
}

function snapshotsEqual(before: GitSnapshot, after: GitSnapshot): boolean {
	return before.head === after.head && before.status === after.status && before.candidateHash === after.candidateHash;
}

async function collectUntrackedEvidence(cwd: string, paths: string[]): Promise<string> {
	const untracked = new Set(nulList(await runGit(cwd, ["ls-files", "--others", "--exclude-standard", "-z"])));
	let total = 0;
	const parts: string[] = [];
	for (const path of paths.filter((item) => untracked.has(item))) {
		const absolute = resolve(cwd, path);
		const info = await lstat(absolute);
		if (!info.isFile() || info.isSymbolicLink()) {
			throw new Error(`untracked candidate must be a regular non-symlink file: ${path}`);
		}
		if (info.size > 2 * 1024 * 1024) throw new Error(`untracked review evidence exceeds 2 MiB: ${path}`);
		const content = await readFile(absolute);
		total += info.size;
		if (total > 2 * 1024 * 1024) throw new Error("untracked review evidence exceeds 2 MiB");
		let decoded: string | undefined;
		try { decoded = new TextDecoder("utf-8", { fatal: true }).decode(content); }
		catch { /* binary evidence uses exact hash */ }
		if (decoded === undefined || content.includes(0)) parts.push(`\n### ${path}\n\n<binary sha256=${sha256(content)} bytes=${content.length}>\n`);
		else parts.push(`\n### ${path}\n\n\`\`\`text\n${decoded}\n\`\`\`\n`);
	}
	return parts.join("");
}

function parseReviewOutput(stdout: string): ParsedReview | undefined {
	const markerIndex = stdout.lastIndexOf(REVIEW_MARKER);
	if (markerIndex < 0) return undefined;
	const tail = stdout.slice(markerIndex + REVIEW_MARKER.length).trimStart();
	const firstLine = tail.split(/\r?\n/, 1)[0]?.trim();
	if (!firstLine) return undefined;
	try {
		const value = JSON.parse(firstLine) as Partial<ParsedReview>;
		if (!value || !["pass", "changes_required", "blocked"].includes(value.decision ?? "")) return undefined;
		if (!Array.isArray(value.findings) || value.findings.length > 100 || !Array.isArray(value.limitations) || value.limitations.length > 20) return undefined;
		const findings: ReviewFinding[] = [];
		for (const finding of value.findings) {
			if (!finding || !["P0", "P1", "P2"].includes(finding.severity)) return undefined;
			if (typeof finding.summary !== "string" || !finding.summary.trim() || /[\r\n]/.test(finding.summary) || Buffer.byteLength(finding.summary, "utf8") > 600) return undefined;
			if (typeof finding.evidence !== "string" || !finding.evidence.trim() || /[\r\n]/.test(finding.evidence) || Buffer.byteLength(finding.evidence, "utf8") > 600) return undefined;
			findings.push({ severity: finding.severity, summary: finding.summary, evidence: finding.evidence });
		}
		if (findings.filter((item) => item.severity !== "P2").length > 20) return undefined;
		if (value.limitations.some((item) => typeof item !== "string" || /[\r\n]/.test(item) || Buffer.byteLength(item, "utf8") > 1000)) return undefined;
		return { decision: value.decision!, findings, limitations: value.limitations as string[] };
	} catch {
		return undefined;
	}
}

function structuredFindingsPreview(review: ParsedReview): string {
	const rank = { P0: 0, P1: 1, P2: 2 } as const;
	const ordered = [...review.findings].sort((a, b) => rank[a.severity] - rank[b.severity]);
	const blocking = ordered.filter((finding) => finding.severity !== "P2");
	const p2 = ordered.filter((finding) => finding.severity === "P2");
	const lines = blocking.map((finding, index) => `${index + 1}. ${finding.severity}: ${finding.summary} — ${finding.evidence}`);
	let p2Bytes = 0;
	for (const finding of p2) {
		const line = `${lines.length + 1}. P2: ${finding.summary} — ${finding.evidence}`;
		if (p2Bytes + Buffer.byteLength(line, "utf8") > 6 * 1024) { lines.push("[Additional P2 previews omitted; full P2 findings remain in tool details for disposition.]"); break; }
		lines.push(line); p2Bytes += Buffer.byteLength(line, "utf8");
	}
	if (lines.length === 0) lines.push("None.");
	if (review.limitations.length > 0) lines.push(`Limitations: ${review.limitations.map((item) => item.slice(0, 300)).join("; ")}`);
	return lines.join("\n");
}

async function requirePassedRoundReview(cwd: string, path: string, roundId: string): Promise<void> {
	let text: string;
	try {
		const file = await resolveExistingProjectFile(cwd, path);
		text = await readFile(file.absolutePath, "utf8");
	} catch {
		throw new Error("final integrated Review requires a distinct passed per-Round artifact with zero unresolved P0/P1");
	}
	const role = extractUniqueMetadata(text, "Review role");
	const round = extractUniqueMetadata(text, "Round");
	const decision = extractUniqueMetadata(text, "Decision");
	const p0 = extractUniqueMetadata(text, "Unresolved P0");
	const p1 = extractUniqueMetadata(text, "Unresolved P1");
	if (role !== "per-round" || !round || !new RegExp(`^${roundId}(?:\\s|$|—|-)`).test(round) || decision !== "pass" || p0 !== "0" || p1 !== "0") {
		throw new Error("final integrated Review requires a distinct passed per-Round artifact with zero unresolved P0/P1");
	}
}

function boundModelVisibleText(value: string): string {
	const lines = value.split(/\r?\n/).slice(0, 1900);
	let output = lines.join("\n");
	let truncated = lines.length < value.split(/\r?\n/).length;
	while (Buffer.byteLength(output, "utf8") > 48 * 1024) { output = output.slice(0, Math.floor(output.length * 0.9)); truncated = true; }
	return truncated ? `${output}\n[Model-visible tool output truncated; complete bounded evidence remains in tool details.]` : output;
}

function manualReviewFallback(input: {
	roundId: string;
	role: string;
	planPath: string;
	workLogPath: string;
	reviewArtifactPath: string;
	baselineRef: string;
}): string {
	return `Manual Independent Review fallback (requires an Owner-approved human distinct from the Builder):\n- Round: ${input.roundId}\n- Role: ${input.role}\n- Read: AGENTS.md, ${input.planPath}, ${input.workLogPath}\n- Candidate: ${input.baselineRef}..working-tree\n- Review read-only; do not modify candidate files or write ${input.reviewArtifactPath}\n- Return P0/P1/P2 findings plus pass, changes_required, or blocked\n- Builder records reviewer identity, inputs, tool boundary, decision, P2 dispositions, and before/after Git immutability evidence in ${input.reviewArtifactPath}`;
}

function reviewBlocked(reason: string, fallback: string, details: Record<string, unknown> = {}) {
	const safeReason = redactSecrets(reason).slice(0, 2000);
	const safeFallback = fallback.slice(0, 6000);
	return textResult(`Review decision: blocked\nReason: ${safeReason}\n\n${safeFallback}`, {
		decision: "blocked",
		findings: [],
		manualFallback: safeFallback,
		...details,
	});
}

function buildReviewBundle(input: {
	role: "per_round" | "final_integrated";
	roundId: string;
	planPath: string;
	workLogPath: string;
	reviewArtifactPath: string;
	baselineRef: string;
	candidateSummary: string;
	validationSummary: string;
	scopePaths: string[];
	head: string;
	status: string;
	changedPaths: string[];
	diff: string;
	untrackedEvidence: string;
}): string {
	return `# Harness Independent Review Bundle\n\nReview role: ${input.role}\nOwning Round: ${input.roundId}\nPlan: ${input.planPath}\nWork log: ${input.workLogPath}\nDurable artifact target (Builder-only write): ${input.reviewArtifactPath}\nBaseline: ${input.baselineRef}\nCandidate HEAD: ${input.head}\n\n## Candidate Summary\n${input.candidateSummary}\n\n## Automated Validation Summary\n${input.validationSummary}\n\n## Required Scope Paths\n${bullets(input.scopePaths)}\n\n## Git Status Before Review\n\`\`\`text\n${input.status || "(clean)"}\n\`\`\`\n\n## Changed Paths\n${bullets(input.changedPaths)}\n\n## Baseline-To-Candidate Diff\n\`\`\`diff\n${input.diff}\n\`\`\`\n\n## Untracked Candidate Contents\n${input.untrackedEvidence || "(none)"}\n`;
}

async function restoreParentAfterSubmissionFailure(
	replacementCtx: ReplacedSessionContext,
	parentSession: string,
	fallback: string,
	error: string,
): Promise<void> {
	replacementCtx.ui.setEditorText(fallback);
	try {
		const result = await replacementCtx.switchSession(parentSession, {
			withSession: async (restoredCtx) => {
				restoredCtx.ui.setEditorText(fallback);
				restoredCtx.ui.notify(`Automatic handoff failed; parent session restored: ${error}`, "error");
			},
		});
		if (result.cancelled) {
			replacementCtx.ui.setEditorText(fallback);
			replacementCtx.ui.notify(`Automatic handoff failed and parent restore was cancelled; fallback loaded in the replacement session: ${error}`, "error");
		}
	} catch {
		// switchSession() can reject after tearing down the replacement runtime.
		// The replacement context may be stale, so never call it in this catch.
		// The fallback was preloaded before the switch attempt and remains in the
		// persisted confirming tool result.
	}
}

export default function harnessFlow(pi: ExtensionAPI): void {
	const pendingHandoffs = new Map<string, PendingHandoff>();

	pi.registerTool({
		name: "harness_request_plan_approval",
		label: "Harness Plan Approval",
		description: "Request structured Owner approval only after a complete greenfield Plan Preview is visible in chat. This action performs no project write and returns approved, changes_requested, or cancelled. Accepting discovery defaults is never Plan approval.",
		promptSnippet: "Request explicit Owner approval for a complete Plan Preview without writing project files",
		promptGuidelines: [
			"Use harness_request_plan_approval only after presenting the complete Plan Preview and before any project write.",
			"Never treat accepted discovery defaults as Plan approval; call harness_request_plan_approval for the separate durable-Plan decision.",
		],
		parameters: Type.Object({
			previewTitle: Type.String({ description: "Short title of the complete Plan Preview", maxLength: 160 }),
			previewSummary: Type.String({ description: "Concise goal, scope, validation, and delivery summary already shown in chat", maxLength: 4000 }),
			previewComplete: Type.Boolean({ description: "Must be true only after the complete Preview is visible" }),
			discoveryDefaultsAccepted: Type.Boolean({ description: "Informational only; never grants Plan approval" }),
		}),
		executionMode: "sequential",
		async execute(_id, params, _signal, _update, ctx) {
			if (!params.previewComplete) {
				return textResult("Plan approval result: changes_requested\nReason: the Plan Preview is not complete.", {
					status: "changes_requested",
					projectWritesAuthorized: false,
				});
			}
			if (!ctx.hasUI) {
				return textResult("Plan approval result: cancelled\nReason: explicit Owner UI is unavailable; use the copyable manual confirmation fallback.", {
					status: "cancelled",
					projectWritesAuthorized: false,
				});
			}
			const summary = redactSecrets(params.previewSummary).slice(0, 4000);
			const choice = await ctx.ui.select(
				`Plan approval — ${redactSecrets(params.previewTitle).slice(0, 160)}\n\n${summary}\n\nThis is the durable Plan decision; accepted discovery defaults alone do not approve it.`,
				[
					"Approve durable Plan persistence",
					"Request changes",
					"Cancel",
				],
			);
			if (choice === "Approve durable Plan persistence") {
				return textResult("Plan approval result: approved\nAuthority: persist only the approved Plan evidence, then offer handoff. Do not implement in the orchestration session.", {
					status: "approved",
					projectWritesAuthorized: true,
					discoveryDefaultsAccepted: params.discoveryDefaultsAccepted,
					summary,
				});
			}
			if (choice === "Request changes") {
				const requested = await ctx.ui.input("Requested Plan changes", "Describe the changes needed");
				const boundedRequest = requested?.trim() ? redactSecrets(requested.trim()).slice(0, 4000) : undefined;
				return textResult(`Plan approval result: changes_requested${boundedRequest ? `\nRequested changes: ${boundedRequest}` : ""}`, {
					status: "changes_requested",
					projectWritesAuthorized: false,
					requestedChanges: boundedRequest,
				});
			}
			return textResult("Plan approval result: cancelled\nNo project write is authorized.", {
				status: "cancelled",
				projectWritesAuthorized: false,
			});
		},
	});

	pi.registerTool({
		name: "harness_offer_session_handoff",
		label: "Harness Session Handoff",
		description: "Validate an approved durable Plan and fixed Round, show the proposed session and bounded handoff, request one Owner confirmation, then queue a parent-linked new/name/seed/start transition. Cancellation or capability failure preserves a copyable manual fallback.",
		promptSnippet: "Offer one-confirmation implementation-session handoff from approved durable evidence",
		promptGuidelines: [
			"Use harness_offer_session_handoff only after the approved Plan has been persisted; chat history is not authority.",
			"Pass the exact Plan-declared Round ID and primary implementation session name to harness_offer_session_handoff.",
		],
		parameters: Type.Object({
			planPath: Type.String({ maxLength: 500 }),
			roundId: Type.String({ maxLength: 20 }),
			sessionName: Type.String({ maxLength: 80 }),
		}),
		executionMode: "sequential",
		async execute(_id, params, _signal, _update, ctx) {
			let prompt = "";
			let fallback = "";
			try {
				if (!ctx.isProjectTrusted()) throw new Error("project-local trust is not active");
				validateRoundId(params.roundId);
				validateSessionName(params.roundId, params.sessionName);
				const planFile = await resolveExistingProjectFile(ctx.cwd, params.planPath);
				if (!planFile.relativePath.startsWith("operations/planning/") || !planFile.relativePath.endsWith(".md")) {
					throw new Error("approved Plan must be under operations/planning/");
				}
				const plan = await readFile(planFile.absolutePath, "utf8");
				if (!planIsApproved(plan)) throw new Error("durable Plan does not contain exact `Plan approval: approved` metadata");
				const planRound = parsePlanRound(plan, params.roundId);
				if (!planRound) throw new Error(`Round ${params.roundId} does not have a complete Ledger declaration in the Plan`);
				if (planRound.sessionName !== params.sessionName) {
					throw new Error(`session name mismatch: Plan declares ${planRound.sessionName}, request supplied ${params.sessionName}`);
				}
				if (planRound.status === "blocked" || planRound.status === "accepted") {
					throw new Error(`Round ${params.roundId} status ${planRound.status} is not eligible for a new implementation handoff`);
				}
				assertEffectiveRoundSet(plan, params.roundId);

				const roundSection = extractRoundSection(plan, params.roundId);
				if (!roundSection) throw new Error(`Round ${params.roundId} has no owning-Round contract section`);
				const contract = parseRoundHandoffContract(roundSection);
				const contractPaths: string[] = [];
				for (const item of contract.contractPaths) contractPaths.push((await resolveExistingProjectFile(ctx.cwd, item)).relativePath);
				const latestWorkLog = contract.latestWorkLog
					? (await resolveExistingProjectFile(ctx.cwd, contract.latestWorkLog)).relativePath
					: undefined;
				const latestReview = contract.latestReview
					? (await resolveExistingProjectFile(ctx.cwd, contract.latestReview)).relativePath
					: undefined;
				if (latestWorkLog && !latestWorkLog.startsWith("operations/work_logs/")) throw new Error("Latest work log must be under operations/work_logs/");
				if (latestReview && !latestReview.startsWith("operations/reviews/")) throw new Error("Latest review must be under operations/reviews/");
				const reviewArtifactPath = await validateFutureProjectPath(ctx.cwd, contract.roundReviewArtifact, "operations/reviews/");
				const finalReviewArtifactPath = await validateFutureProjectPath(ctx.cwd, contract.finalReviewArtifact, "operations/reviews/");
				const target = redactSecrets(planRound.deliveryBoundary.trim()).slice(0, 1200);
				if (!target) throw new Error("Round Ledger delivery boundary is empty");
				if (normalizedEvidence(contract.acceptanceEvidence.join("; ")) !== normalizedEvidence(planRound.acceptanceEvidence)) {
					throw new Error("owning-Round acceptance evidence does not exactly match the Ledger boundary");
				}
				prompt = buildHandoffPrompt({
					planPath: planFile.relativePath,
					roundId: params.roundId,
					sessionName: params.sessionName,
					target,
					contractPaths,
					latestWorkLog,
					latestReview,
					nonGoals: contract.nonGoals,
					dependencies: contract.dependencies,
					expectedChangeSurfaces: contract.expectedChangeSurfaces,
					blockersAndAssumptions: contract.blockersAndAssumptions,
					validation: contract.validation,
					reviewMode: contract.reviewMode,
					reviewArtifactPath,
					finalReviewArtifactPath,
					acceptanceEvidence: contract.acceptanceEvidence,
					nextGate: contract.nextGate,
					blockedConditions: contract.blockedConditions,
				});
				if (Buffer.byteLength(prompt, "utf8") > 32 * 1024 || prompt.split(/\r?\n/).length > 1200) {
					throw new Error("Plan-grounded handoff exceeds the safe copyable output boundary");
				}
				fallback = manualHandoff(params.sessionName, prompt);

				const parentSession = ctx.sessionManager.getSessionFile();
				if (ctx.mode !== "tui" || !ctx.hasUI || !parentSession || !ctx.model) {
					return textResult(`Automatic handoff unavailable; current session unchanged.\n\nCopyable manual fallback:\n${fallback}`, {
						status: "capability_failure",
						currentSessionPreserved: true,
						manualFallback: fallback,
					});
				}

				const confirmed = await ctx.ui.confirm(
					"Start implementation session?",
					`Proposed session: ${params.sessionName}\nRound: ${params.roundId} (${planRound.status})\nBounded target: ${target}\n\nHandoff summary:\n- Contracts: ${contractPaths.join(", ")}\n- Non-goals: ${contract.nonGoals.join("; ")}\n- Dependencies / DoR: ${contract.dependencies.join("; ")}\n- Expected surfaces: ${contract.expectedChangeSurfaces.join("; ")}\n- Blockers / assumptions: ${contract.blockersAndAssumptions.join("; ")}\n- Validation: ${contract.validation.join("; ")}\n- Review: ${contract.reviewMode} -> ${reviewArtifactPath}; final -> ${finalReviewArtifactPath}\n- Latest work log/review: ${latestWorkLog ?? "none"}; ${latestReview ?? "none"}\n- Acceptance: ${contract.acceptanceEvidence.join("; ")}\n- Next gate: ${contract.nextGate}\n- Blocked / rebaseline: ${contract.blockedConditions.join("; ")}\n\nGrounded in ${planFile.relativePath}. Create, name, seed, and submit once?`,
				);
				if (!confirmed) {
					return textResult(`Handoff cancelled; current session unchanged.\n\nCopyable manual fallback:\n${fallback}`, {
						status: "cancelled",
						currentSessionPreserved: true,
						manualFallback: fallback,
					});
				}

				cleanupPending(pendingHandoffs);
				const token = randomUUID();
				pendingHandoffs.set(token, {
					createdAt: Date.now(),
					parentSession,
					sessionName: params.sessionName,
					roundId: params.roundId,
					prompt,
					fallback,
				});
				pi.sendUserMessage(`/harness-flow-continue ${token}`, {
					deliverAs: "followUp",
					expandPromptTemplates: true,
				});
				return textResult(`Handoff confirmed and queued. The current turn will settle before the parent-linked ${params.sessionName} session is created and its prompt is submitted once.\n\nContingency manual fallback:\n${fallback}`, {
					status: "confirmed_queued",
					parentLinked: true,
					sessionName: params.sessionName,
					roundId: params.roundId,
					manualFallback: fallback,
				});
			} catch (error) {
				const reason = redactSecrets(error instanceof Error ? error.message : String(error)).slice(0, 1200);
				const safeSessionName = /^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$/.test(params.sessionName) ? params.sessionName : "<declared-session-name>";
				const manual = fallback || (prompt ? manualHandoff(safeSessionName, prompt) : `/session-handoff ${safeSessionName}`);
				return textResult(`Automatic handoff blocked; current session unchanged.\nReason: ${reason}\n\nCopyable manual fallback:\n${manual}`, {
					status: "blocked",
					currentSessionPreserved: true,
					manualFallback: manual,
				});
			}
		},
	});

	pi.registerCommand("harness-flow-continue", {
		description: "Complete a previously confirmed Harness handoff",
		handler: async (args, ctx) => {
			cleanupPending(pendingHandoffs);
			const token = args.trim();
			const handoff = pendingHandoffs.get(token);
			if (!handoff) {
				ctx.ui.notify("Handoff token is missing or expired; use the manual fallback.", "error");
				return;
			}
			pendingHandoffs.delete(token);
			if (ctx.sessionManager.getSessionFile() !== handoff.parentSession) {
				ctx.ui.setEditorText(handoff.fallback);
				ctx.ui.notify("Current session changed before handoff; automatic transition cancelled.", "error");
				return;
			}
			await ctx.waitForIdle();
			ctx.ui.setEditorText(handoff.fallback);
			try {
				const result = await ctx.newSession({
					parentSession: handoff.parentSession,
					setup: async (sessionManager) => {
						sessionManager.appendSessionInfo(handoff.sessionName);
					},
					withSession: async (replacementCtx) => {
						replacementCtx.ui.notify(`Starting ${handoff.sessionName} for ${handoff.roundId}`, "info");
						try {
							await replacementCtx.sendUserMessage(handoff.prompt);
						} catch (error) {
							const reason = error instanceof Error ? error.message : String(error);
							await restoreParentAfterSubmissionFailure(replacementCtx, handoff.parentSession, handoff.fallback, reason);
						}
					},
				});
				if (result.cancelled) {
					ctx.ui.setEditorText(handoff.fallback);
					ctx.ui.notify("New session was cancelled; current session preserved and fallback loaded.", "warning");
				}
			} catch (error) {
				// newSession() may throw after the old runtime is torn down. The original
				// command context is stale in that state, so never call it here. The full
				// fallback was persisted in the confirming tool result and preloaded in the
				// old editor before replacement; successful replacement failures are handled
				// inside withSession using only replacementCtx.
				console.error(`${EXTENSION_NAME}: automatic handoff replacement failed`, error instanceof Error ? error.message : String(error));
			}
		},
	});

	pi.registerTool({
		name: "harness_run_independent_review",
		label: "Harness Independent Review",
		description: "Automatically run the required fixed-Round Independent Review after automated verification. Spawns a distinct non-interactive no-session Pi child with only read, grep, find, and ls; captures process/model/output evidence and Git immutability; returns P0/P1/P2 plus pass, changes_required, or blocked.",
		promptSnippet: "Run a distinct read-only Pi Independent Review for a verified fixed-Round candidate",
		promptGuidelines: [
			"After fixed-Round automated verification, call harness_run_independent_review without waiting for the Owner to request routine review.",
			"If harness_run_independent_review returns P0/P1 or changes_required, keep the same Round open, fix, verify, and call harness_run_independent_review again automatically.",
			"The Builder, not the child reviewer, writes the durable review artifact and dispositions every P2 before acceptance.",
		],
		parameters: Type.Object({
			reviewRole: StringEnum(["per_round", "final_integrated"] as const),
			roundId: Type.String({ maxLength: 20 }),
			planPath: Type.String({ maxLength: 500 }),
			candidateSummary: Type.String({ maxLength: 20_000 }),
			validationSummary: Type.String({ maxLength: 30_000 }),
			scopePaths: Type.Array(Type.String({ maxLength: 500 }), { maxItems: 100 }),
			timeoutSeconds: Type.Optional(Type.Integer({ minimum: 30, maximum: 1800, default: 600 })),
		}),
		executionMode: "sequential",
		async execute(_id, params, signal, _update, ctx: ExtensionContext) {
			let fallback = "Use an Owner-approved human distinct from the Builder to review the declared Round read-only and record P0/P1/P2 plus candidate immutability.";
			try { validateRoundId(params.roundId); }
			catch (error) { return reviewBlocked(error instanceof Error ? error.message : String(error), fallback); }

			if (!ctx.isProjectTrusted()) return reviewBlocked("project-local trust is not active", fallback);
			if (!ctx.model) return reviewBlocked("no active reviewer model is available", fallback);

			let planPath: string;
			let workLogPath: string;
			let reviewArtifactPath: string;
			let planText: string;
			let expectedBaseline: string;
			let reviewMode = "";
			const scopePaths: string[] = [];
			try {
				const planFile = await resolveExistingProjectFile(ctx.cwd, params.planPath);
				planPath = planFile.relativePath;
				if (!planPath.startsWith("operations/planning/")) throw new Error("review requires a project-local Plan path");
				planText = await readFile(planFile.absolutePath, "utf8");
				if (!planIsApproved(planText)) throw new Error("review Plan lacks unique authoritative `Plan approval: approved` metadata");
				const planRound = parsePlanRound(planText, params.roundId);
				if (!planRound || planRound.status !== "in_progress") throw new Error(`Round ${params.roundId} must be declared uniquely as in_progress for Review`);
				const reviewRoundSection = extractRoundSection(planText, params.roundId);
				if (!reviewRoundSection) throw new Error(`Round ${params.roundId} must have exactly one owning-Round contract section`);
				const reviewContract = parseRoundHandoffContract(reviewRoundSection);
				reviewMode = reviewContract.reviewMode;
				const workLogFile = await resolveExistingProjectFile(ctx.cwd, reviewContract.reviewWorkLog);
				workLogPath = workLogFile.relativePath;
				if (!workLogPath.startsWith("operations/work_logs/")) throw new Error("owning Round review work log must be project-local");
				const workLogText = await readFile(workLogFile.absolutePath, "utf8");
				const logRound = extractUniqueMetadata(workLogText, "Round");
				const logPlan = extractUniqueMetadata(workLogText, "Plan");
				if (!logRound || !new RegExp(`^${params.roundId}(?:\\s|$|—|-)`).test(logRound) || normalizedEvidence(logPlan ?? "") !== normalizedEvidence(planPath)) {
					throw new Error("declared review work log lacks unique authoritative Round/Plan metadata");
				}
				const declaredReviewArtifact = params.reviewRole === "final_integrated" ? reviewContract.finalReviewArtifact : reviewContract.roundReviewArtifact;
				reviewArtifactPath = await validateFutureProjectPath(ctx.cwd, declaredReviewArtifact, "operations/reviews/");
				expectedBaseline = params.reviewRole === "final_integrated" ? (extractBaseline(planText) ?? "") : (extractBaseline(workLogText) ?? "");
				if (!expectedBaseline) throw new Error(`missing declared Git baseline for ${params.reviewRole} Review`);
				const effective = assertEffectiveRoundSet(planText, params.roundId);
				if (params.reviewRole === "final_integrated") {
					await requirePassedRoundReview(ctx.cwd, await validateFutureProjectPath(ctx.cwd, reviewContract.roundReviewArtifact, "operations/reviews/"), params.roundId);
					const ids = parsePlanRoundIds(planText);
					if (ids.at(-1) !== params.roundId) throw new Error("final integrated Review must belong to the last planned Round");
					for (const id of ids.slice(0, -1)) if (!effective.has(id)) throw new Error(`prior Round ${id} is not accepted effective`);
				}
				for (const item of params.scopePaths.slice(0, 100)) {
					scopePaths.push((await resolveExistingProjectFile(ctx.cwd, item)).relativePath);
				}
				fallback = manualReviewFallback({ roundId: params.roundId, role: params.reviewRole, planPath, workLogPath, reviewArtifactPath, baselineRef: expectedBaseline });
			} catch (error) {
				return reviewBlocked(redactSecrets(error instanceof Error ? error.message : String(error)).slice(0, 1200), fallback);
			}
			if (reviewMode !== "spawned_pi_process") return reviewBlocked("owning Round requires approved distinct human_review; automatic Pi spawn is not authorized", fallback);

			const auth = await ctx.modelRegistry.getApiKeyAndHeaders(ctx.model);
			if (!auth.ok) return reviewBlocked(`provider/auth unavailable: ${auth.error}`, fallback);

			let before: GitSnapshot;
			let baselineCommit: string;
			let diff: string;
			let changedPaths: string[];
			let untrackedEvidence: string;
			try {
				baselineCommit = (await runGit(ctx.cwd, ["rev-parse", "--verify", `${expectedBaseline}^{commit}`])).trim();
				const rawDiff = await runGit(ctx.cwd, ["diff", "--raw", "--no-abbrev", "-z", baselineCommit, "--"]);
				if (/(?:^|\0):(?:160000\s|\d{6}\s160000\s)/.test(rawDiff)) throw new Error("baseline candidate contains a gitlink conversion/deletion and requires distinct-human or OS-isolated review");
				changedPaths = nulList(await runGit(ctx.cwd, ["diff", "--name-only", "-z", baselineCommit, "--"]));
				before = await captureGitSnapshot(ctx.cwd, changedPaths);
				changedPaths = [...new Set([...changedPaths, ...before.candidatePaths])].sort();
				diff = await runGit(ctx.cwd, ["diff", "--no-ext-diff", "--binary", "--full-index", "--unified=60", baselineCommit, "--"]);
				if (changedPaths.length === 0) throw new Error("review candidate is empty");
				untrackedEvidence = await collectUntrackedEvidence(ctx.cwd, changedPaths);
			} catch (error) {
				return reviewBlocked(`candidate snapshot failed: ${error instanceof Error ? error.message : String(error)}`, fallback);
			}

			let tempDir: string | undefined;
			let processResult: ProcessResult | undefined;
			let after: GitSnapshot | undefined;
			try {
				tempDir = await mkdtemp(join(tmpdir(), "harness-flow-review-"));
				const bundlePath = join(tempDir, "review-bundle.md");
				const bundle = buildReviewBundle({
					role: params.reviewRole,
					roundId: params.roundId,
					planPath,
					workLogPath,
					reviewArtifactPath,
					baselineRef: baselineCommit,
					candidateSummary: redactSecrets(params.candidateSummary).slice(0, 20_000),
					validationSummary: redactSecrets(params.validationSummary).slice(0, 30_000),
					scopePaths,
					head: before.head,
					status: before.status.replaceAll("\0", "\n"),
					changedPaths,
					diff,
					untrackedEvidence,
				});
				await writeFile(bundlePath, bundle, { encoding: "utf8", mode: 0o600 });

				const reviewerPrompt = `Read AGENTS.md, ${planPath}, ${workLogPath}, every changed path listed in @${bundlePath}, and every additional required scope path. Review the complete ${params.reviewRole} candidate read-only. The bundle contains the tracked baseline diff and bounded contents for every untracked candidate file. Do not modify files, run commands, commit, push, or write ${reviewArtifactPath}. Verify contract, correctness, regression, security, fallback, bootstrap, portability, evidence, and Round ownership. Findings must cite file/line or bundle evidence. End with exactly one single-line JSON record prefixed by ${REVIEW_MARKER} using this schema: {"decision":"pass|changes_required|blocked","findings":[{"severity":"P0|P1|P2","summary":"...","evidence":"..."}],"limitations":["..."]}. A pass requires zero P0/P1. Do not wrap the final JSON in a code fence.`;
				const args = [
					"--no-session",
					"--no-approve",
					"--no-extensions",
					"--no-skills",
					"--no-prompt-templates",
					"--no-themes",
					"--no-context-files",
					"--tools", READ_ONLY_TOOLS.join(","),
					"--provider", ctx.model.provider,
					"--model", ctx.model.id,
					"--thinking", ctx.thinkingLevel ?? "medium",
					"-p",
					reviewerPrompt,
				];
				const invocation = getPiInvocation(args);
				const env = buildReviewerEnv(auth);
				processResult = await runProcess(invocation.command, invocation.args, {
					cwd: ctx.cwd,
					env,
					timeoutMs: (params.timeoutSeconds ?? 600) * 1000,
					signal,
					maxBytes: MAX_REVIEW_OUTPUT_BYTES,
				});
				after = await captureGitSnapshot(ctx.cwd, changedPaths);
				const immutable = snapshotsEqual(before, after);
				const processEvidence = {
					builderPid: process.pid,
					reviewerPid: processResult.pid,
					distinctProcess: processResult.pid !== undefined && processResult.pid !== process.pid,
					invocation: {
						command: invocation.displayCommand,
						args: args.map((arg) => arg.includes(tempDir!) ? arg.replaceAll(tempDir!, "<temporary-review-bundle>") : arg),
					},
					mode: "print",
					noSession: true,
					projectResourcesDisabled: true,
					toolBoundary: [...READ_ONLY_TOOLS],
					writableShell: false,
					environmentBoundary: "allowlisted runtime variables plus active provider auth only",
					readConfinement: false,
					provider: ctx.model.provider,
					model: ctx.model.id,
					thinkingLevel: ctx.thinkingLevel ?? "medium",
					auth: "ready (credential not captured)",
					exitCode: processResult.code,
					exitSignal: processResult.signal,
					timedOut: processResult.timedOut,
					aborted: processResult.aborted,
					outputTruncated: processResult.truncated,
					durationMs: processResult.durationMs,
					stdout: processResult.stdout,
					stderr: processResult.stderr,
				};
				const immutability = { before, after, unchanged: immutable };
				if (!processEvidence.distinctProcess) {
					return reviewBlocked("reviewer process was not distinct", fallback, { processEvidence, immutability });
				}
				if (!immutable) {
					return reviewBlocked("candidate changed during review", fallback, { processEvidence, immutability });
				}
				if (processResult.code !== 0 || processResult.timedOut || processResult.aborted || processResult.truncated) {
					return reviewBlocked("review child failed, timed out, was aborted, or produced truncated evidence", fallback, { processEvidence, immutability });
				}
				const parsed = parseReviewOutput(processResult.stdout);
				if (!parsed) return reviewBlocked("review output did not contain the required structured result", fallback, { processEvidence, immutability });
				const counts = {
					P0: parsed.findings.filter((item) => item.severity === "P0").length,
					P1: parsed.findings.filter((item) => item.severity === "P1").length,
					P2: parsed.findings.filter((item) => item.severity === "P2").length,
				};
				let decision = parsed.decision;
				if (decision === "pass" && (counts.P0 > 0 || counts.P1 > 0)) decision = "changes_required";
				const nextAction = decision === "pass"
					? "Builder must write the durable review artifact, disposition every P2, and continue to the declared acceptance gate."
					: decision === "changes_required"
						? `Keep ${params.roundId} open. Fix all P0/P1, rerun regression verification, and automatically call harness_run_independent_review again.`
						: "Fail closed or use the Owner-approved distinct-human manual fallback.";
				const modelVisible = boundModelVisibleText(`Review decision: ${decision}\nFindings: P0=${counts.P0} P1=${counts.P1} P2=${counts.P2}\nCandidate immutable: yes\n${nextAction}\n\nActionable structured findings:\n${structuredFindingsPreview(parsed)}\n\nReviewer output preview:\n${modelOutputPreview(processResult.stdout)}`);
				return textResult(modelVisible, {
					decision,
					findings: parsed.findings,
					limitations: parsed.limitations,
					counts,
					processEvidence,
					immutability,
					manualFallback: fallback,
					nextAction,
				});
			} catch (error) {
				try { after = await captureGitSnapshot(ctx.cwd, changedPaths); } catch { /* captured as unavailable */ }
				return reviewBlocked(error instanceof Error ? error.message : String(error), fallback, {
					processEvidence: processResult,
					immutability: after ? { before, after, unchanged: snapshotsEqual(before, after) } : { before, after: "unavailable", unchanged: false },
				});
			} finally {
				if (tempDir) await rm(tempDir, { recursive: true, force: true });
			}
		},
	});
}
