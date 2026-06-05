<script lang="ts">
	import { queryLog, type QueryEntry } from '$lib/stores/queryLog.svelte';

	let open = $state(false);
	let copied = $state<string | null>(null);

	function compactReplacer(_key: string, value: unknown): unknown {
		if (Array.isArray(value) && value.length > 4 && value.every(v => typeof v === 'number')) {
			return [
				...value.slice(0, 3).map(v => Math.round((v as number) * 10000) / 10000),
				`...${value.length} dims`,
			];
		}
		return value;
	}

	function formatJson(obj: unknown, indent: number): string {
		const pad = '  '.repeat(indent);
		return JSON.stringify(obj, compactReplacer, 2)
			.split('\n')
			.map((line) => pad + line)
			.join('\n');
	}

	function toPyMongo(entry: QueryEntry): string {
		const col = entry.collection;
		const op = entry.operation;
		const args = entry.args;

		if (op === 'aggregate') {
			return `db.${col}.aggregate(\n${formatJson(args, 1)}\n)`;
		}
		if (op === 'find_one') {
			const a = args as Record<string, unknown>;
			let s = `db.${col}.find_one(\n${formatJson(a.filter ?? {}, 1)}`;
			if (a.projection) s += `,\n${formatJson(a.projection, 1)}`;
			return s + '\n)';
		}
		if (op === 'find') {
			const a = args as Record<string, unknown>;
			let s = `db.${col}.find(\n${formatJson(a.filter ?? {}, 1)}`;
			if (a.projection) s += `,\n${formatJson(a.projection, 1)}`;
			s += '\n)';
			if (a.sort) s += `.sort(${formatJson(a.sort, 0)})`;
			if (a.limit) s += `.limit(${a.limit})`;
			return s;
		}
		if (op === 'count_documents') {
			return `db.${col}.count_documents(\n${formatJson(args ?? {}, 1)}\n)`;
		}
		return `db.${col}.${op}(${formatJson(args, 1)})`;
	}

	function formatResult(entry: QueryEntry): string {
		if (!entry.result) return '// No result captured';
		return JSON.stringify(entry.result, compactReplacer, 2);
	}

	function highlight(code: string): string {
		const esc = code
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;');

		const TOKEN = /(?<dims>"\.\.\.?\d+ dims?")|(?<more>"\.\.\.?\+\d+ more")|(?<op>"\$\w+")|(?<key>"[\w_.]+?")(?=\s*:)|(?<=:\s*)(?<num>-?\d+\.?\d*(?:[eE][+-]?\d+)?)(?=[\s,\]\}\n])|(?<=:\s*)(?<str>"(?:[^"\\]|\\.)*")|(?<bool>\b(?:true|false|null)\b)|(?<db>^db\.\w+\.\w+)|(?<comment>\/\/[^\n]*)/gm;

		return esc.replace(TOKEN, (...args) => {
			const g = args[args.length - 1] as Record<string, string | undefined>;
			if (g.dims) return `<span class="tk-dim">${g.dims}</span>`;
			if (g.more) return `<span class="tk-dim">${g.more}</span>`;
			if (g.op)   return `<span class="tk-op">${g.op}</span>`;
			if (g.key)  return `<span class="tk-key">${g.key}</span>`;
			if (g.num !== undefined) return `<span class="tk-num">${g.num}</span>`;
			if (g.str)  return `<span class="tk-str">${g.str}</span>`;
			if (g.bool) return `<span class="tk-bool">${g.bool}</span>`;
			if (g.db)   return `<span class="tk-db">${g.db}</span>`;
			if (g.comment) return `<span class="tk-comment">${g.comment}</span>`;
			return args[0];
		});
	}

	function timeAgo(ts: number): string {
		const sec = Math.floor(Date.now() / 1000 - ts);
		if (sec < 5) return 'just now';
		if (sec < 60) return `${sec}s ago`;
		return `${Math.floor(sec / 60)}m ago`;
	}

	function opBadge(op: string): { bg: string; text: string; ring: string } {
		const map: Record<string, { bg: string; text: string; ring: string }> = {
			aggregate:       { bg: 'rgba(139,92,246,0.15)', text: '#c4b5fd', ring: 'rgba(139,92,246,0.25)' },
			find_one:        { bg: 'rgba(59,130,246,0.15)',  text: '#93c5fd', ring: 'rgba(59,130,246,0.25)' },
			find:            { bg: 'rgba(6,182,212,0.15)',   text: '#67e8f9', ring: 'rgba(6,182,212,0.25)' },
			count_documents: { bg: 'rgba(245,158,11,0.15)',  text: '#fcd34d', ring: 'rgba(245,158,11,0.25)' },
		};
		return map[op] ?? { bg: 'rgba(148,163,184,0.15)', text: '#cbd5e1', ring: 'rgba(148,163,184,0.25)' };
	}

	async function copyCode(key: string, code: string) {
		try {
			await navigator.clipboard.writeText(code);
			copied = key;
			setTimeout(() => { if (copied === key) copied = null; }, 1500);
		} catch { /* ignore */ }
	}

	function docSummary(entry: QueryEntry): string {
		if (!entry.result) return '';
		if (Array.isArray(entry.result)) return `${entry.result.length} doc${entry.result.length !== 1 ? 's' : ''} returned`;
		return '1 doc returned';
	}
</script>

<!-- Toggle Button -->
<button
	onclick={() => (open = !open)}
	class="fixed bottom-6 right-20 z-40 w-11 h-11 rounded-full shadow-lg hover:shadow-2xl
		transition-all flex items-center justify-center cursor-pointer group hover:scale-105"
	style="background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); border: 1px solid rgba(255,255,255,0.08);"
	title="Query Inspector"
>
	<svg class="w-[18px] h-[18px] text-gray-400 group-hover:text-purple-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
		<path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" />
	</svg>
	{#if queryLog.count > 0}
		<span class="absolute -top-1 -right-1 min-w-[18px] h-[18px] rounded-full bg-purple-500 text-white text-[9px] font-bold flex items-center justify-center px-1 ring-2 ring-[#0f172a]">
			{queryLog.count > 99 ? '99+' : queryLog.count}
		</span>
	{/if}
</button>

{#if open}
	<!-- Backdrop -->
	<button
		class="fixed inset-0 bg-black/50 backdrop-blur-[3px] z-40 cursor-default"
		onclick={() => (open = false)}
		tabindex="-1"
		aria-label="Close inspector"
	></button>

	<!-- Drawer — wide for split view -->
	<div class="fixed top-0 right-0 bottom-0 z-50 flex flex-col shadow-2xl qi-drawer" style="width: min(1200px, 94vw);">
		<!-- Header -->
		<div class="flex items-center justify-between px-5 py-3.5 qi-header">
			<div class="flex items-center gap-3">
				<div class="w-8 h-8 rounded-lg flex items-center justify-center qi-icon-badge">
					<svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" />
					</svg>
				</div>
				<div>
					<h3 class="text-[13px] font-semibold text-white tracking-tight">Query Inspector</h3>
					<p class="text-[10px] text-gray-500 mt-px">Document result · MongoDB pipeline</p>
				</div>
			</div>
			<div class="flex items-center gap-1.5">
				<button
					onclick={() => queryLog.clear()}
					class="text-[11px] text-gray-500 hover:text-gray-300 px-2.5 py-1 rounded-md hover:bg-white/5 transition-all cursor-pointer"
				>
					Clear
				</button>
				<button
					onclick={() => (open = false)}
					class="w-7 h-7 rounded-md flex items-center justify-center text-gray-500 hover:text-white hover:bg-white/5 transition-all cursor-pointer"
					aria-label="Close inspector"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"></path></svg>
				</button>
			</div>
		</div>

		<!-- Query List -->
		<div class="flex-1 overflow-auto px-3 py-3 space-y-3">
			{#if queryLog.entries.length === 0}
				<div class="flex flex-col items-center justify-center h-full text-center px-10">
					<div class="w-14 h-14 rounded-2xl flex items-center justify-center mb-4 qi-empty-icon">
						<svg class="w-6 h-6 text-purple-400/50" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
							<path stroke-linecap="round" stroke-linejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
						</svg>
					</div>
					<p class="text-sm text-gray-400 font-medium mb-1">No queries captured</p>
					<p class="text-[11px] text-gray-600 leading-relaxed">
						Search or navigate to see<br/>live MongoDB pipelines here
					</p>
				</div>
			{:else}
				{#each queryLog.entries as entry, i}
					{@const queryCode = toPyMongo(entry)}
					{@const resultCode = formatResult(entry)}
					{@const badge = opBadge(entry.operation)}
					{@const hasResult = !!entry.result}
					{@const summary = docSummary(entry)}

					<div class="rounded-lg overflow-hidden qi-card">
						<!-- Card header bar -->
						<div class="flex items-center justify-between px-3.5 py-2 qi-card-header">
							<div class="flex items-center gap-2.5">
								<span
									class="text-[10px] px-1.5 py-[3px] rounded font-mono font-medium"
									style="background:{badge.bg}; color:{badge.text}; box-shadow: inset 0 0 0 1px {badge.ring};"
								>
									{entry.operation}
								</span>
								<span class="text-[11px] text-gray-400 font-mono">{entry.collection}</span>
								{#if summary}
									<span class="text-[10px] text-gray-600 mx-0.5">→</span>
									<span class="text-[10px] px-1.5 py-[2px] rounded font-mono text-emerald-400/80" style="background: rgba(16,185,129,0.08);">{summary}</span>
								{/if}
							</div>
							<div class="flex items-center gap-3">
								{#if entry.duration_ms}
									<span class="text-[10px] font-mono tabular-nums {entry.duration_ms > 200 ? 'text-red-400' : entry.duration_ms > 50 ? 'text-amber-400' : 'text-emerald-400'}">
										{entry.duration_ms.toFixed(0)}ms
									</span>
								{/if}
								<span class="text-[10px] text-gray-600">{timeAgo(entry.ts)}</span>
							</div>
						</div>

						<!-- Split pane: document left, query right -->
						<div class="qi-split" class:qi-split-single={!hasResult}>
							{#if hasResult}
								<!-- LEFT: Document Result -->
								<div class="qi-pane">
									<div class="qi-pane-label qi-pane-label-doc">
										<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"/></svg>
										<span>Document</span>
										<button
											onclick={() => copyCode(`doc-${i}`, resultCode)}
											class="ml-auto w-5 h-5 rounded flex items-center justify-center text-gray-600 hover:text-gray-300 hover:bg-white/5 transition-all cursor-pointer"
											title="Copy document"
										>
											{#if copied === `doc-${i}`}
												<svg class="w-3 h-3 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path></svg>
											{:else}
												<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
											{/if}
										</button>
									</div>
									<div class="qi-code-scroll">
										<pre class="qi-code">{@html highlight(resultCode)}</pre>
									</div>
								</div>
							{/if}

							<!-- RIGHT (or FULL): Query -->
							<div class="qi-pane">
								<div class="qi-pane-label qi-pane-label-query">
									<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5"/></svg>
									<span>Query</span>
									<button
										onclick={() => copyCode(`query-${i}`, queryCode)}
										class="ml-auto w-5 h-5 rounded flex items-center justify-center text-gray-600 hover:text-gray-300 hover:bg-white/5 transition-all cursor-pointer"
										title="Copy query"
									>
										{#if copied === `query-${i}`}
											<svg class="w-3 h-3 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path></svg>
										{:else}
											<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
										{/if}
									</button>
								</div>
								<div class="qi-code-scroll">
									<pre class="qi-code">{@html highlight(queryCode)}</pre>
								</div>
							</div>
						</div>

						<!-- Footer -->
						<div class="px-3.5 py-1.5 flex items-center justify-between qi-card-footer">
							<span class="text-[10px] text-gray-600 font-mono truncate">{entry.endpoint}</span>
						</div>
					</div>
				{/each}
			{/if}
		</div>

		<!-- Footer bar -->
		<div class="px-5 py-2.5 flex items-center justify-between qi-footer">
			<div class="flex items-center gap-2">
				<div class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></div>
				<span class="text-[10px] text-gray-500">Live capture</span>
			</div>
			<span class="text-[10px] text-gray-600 tabular-nums">{queryLog.count} {queryLog.count === 1 ? 'query' : 'queries'}</span>
		</div>
	</div>
{/if}

<style>
	/* ─── Drawer shell ─── */
	:global(.qi-drawer) {
		background: linear-gradient(180deg, #0c1222 0%, #111827 100%);
		border-left: 1px solid rgba(255,255,255,0.04);
	}
	:global(.qi-header) {
		border-bottom: 1px solid rgba(255,255,255,0.05);
		background: rgba(0,0,0,0.15);
	}
	:global(.qi-icon-badge) {
		background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
		box-shadow: 0 2px 8px rgba(124,58,237,0.3);
	}
	:global(.qi-footer) {
		border-top: 1px solid rgba(255,255,255,0.05);
		background: rgba(0,0,0,0.2);
	}

	/* ─── Cards ─── */
	:global(.qi-card) {
		background: rgba(255,255,255,0.02);
		border: 1px solid rgba(255,255,255,0.04);
		transition: border-color 0.15s;
	}
	:global(.qi-card:hover) {
		border-color: rgba(255,255,255,0.08);
	}
	:global(.qi-card-header) {
		border-bottom: 1px solid rgba(255,255,255,0.03);
	}
	:global(.qi-card-footer) {
		background: rgba(0,0,0,0.12);
		border-top: 1px solid rgba(255,255,255,0.02);
	}

	/* ─── Split pane layout ─── */
	:global(.qi-split) {
		display: flex;
		min-height: 140px;
		max-height: 520px;
	}
	:global(.qi-split-single) {
		max-height: 480px;
	}
	:global(.qi-pane) {
		flex: 1 1 50%;
		display: flex;
		flex-direction: column;
		min-width: 0;
		overflow: hidden;
	}
	:global(.qi-split-single .qi-pane) {
		flex: 1 1 100%;
	}
	:global(.qi-pane + .qi-pane) {
		border-left: 1px solid rgba(255,255,255,0.06);
	}

	/* ─── Pane labels ─── */
	:global(.qi-pane-label) {
		display: flex;
		align-items: center;
		gap: 5px;
		padding: 5px 12px;
		font-size: 9px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #475569;
		border-bottom: 1px solid rgba(255,255,255,0.03);
		flex-shrink: 0;
	}
	:global(.qi-pane-label-doc) {
		background: rgba(16,185,129,0.04);
		border-bottom-color: rgba(16,185,129,0.06);
	}
	:global(.qi-pane-label-doc span) {
		color: rgba(110,231,183,0.7);
	}
	:global(.qi-pane-label-doc svg) {
		color: rgba(110,231,183,0.5);
	}
	:global(.qi-pane-label-query) {
		background: rgba(139,92,246,0.04);
		border-bottom-color: rgba(139,92,246,0.06);
	}
	:global(.qi-pane-label-query span) {
		color: rgba(196,181,253,0.7);
	}
	:global(.qi-pane-label-query svg) {
		color: rgba(196,181,253,0.5);
	}

	/* ─── Code ─── */
	:global(.qi-code-scroll) {
		flex: 1;
		overflow: auto;
	}
	:global(.qi-code) {
		padding: 10px 12px;
		margin: 0;
		font-size: 10.5px;
		line-height: 1.6;
		font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', Menlo, monospace;
		color: #cbd5e1;
		white-space: pre;
		tab-size: 2;
	}

	/* ─── Empty state ─── */
	:global(.qi-empty-icon) {
		background: rgba(124,58,237,0.08);
		border: 1px solid rgba(124,58,237,0.12);
	}

	/* ─── Syntax highlighting tokens ─── */
	:global(.tk-op)      { color: #c4b5fd; font-weight: 600; }
	:global(.tk-key)     { color: #7dd3fc; }
	:global(.tk-str)     { color: #86efac; }
	:global(.tk-num)     { color: #fdba74; }
	:global(.tk-bool)    { color: #fca5a5; }
	:global(.tk-dim)     { color: #fbbf24; font-style: italic; }
	:global(.tk-db)      { color: #e2b74b; font-weight: 700; }
	:global(.tk-comment) { color: #475569; font-style: italic; }
</style>
