<script lang="ts">
	import {
		askInsights,
		getInsightsMemories,
		getInsightsConversations,
		getAppUsers,
		type InsightsResult,
		type MemoryItem,
		type ConversationSummary,
		type AppUser,
	} from '$lib/api';
	import Markdown from '$lib/components/Markdown.svelte';

	interface PipelineStep {
		node: string;
		status?: string;
		[key: string]: unknown;
	}

	interface ChatMessage {
		role: string;
		content: string;
		mql?: unknown;
		result_count?: number;
		userRole?: string;
		has_anomaly?: boolean;
		anomaly_message?: string;
		query_type?: string;
		latency_ms?: number;
		preferences_applied?: boolean;
		preference_saved?: boolean;
		pipeline?: PipelineStep[];
	}

	let question = $state('');
	let role = $state('internal_staff');
	let loading = $state(false);
	let messages = $state<ChatMessage[]>([]);
	let showMQL = $state<number | null>(null);
	let showPipeline = $state<number | null>(null);
	let expandedNodes = $state<Set<string>>(new Set());

	// User & session management
	let users = $state<AppUser[]>([]);
	let selectedUserId = $state('analyst-2');
	let sessionId = $state(`insights-${Date.now()}`);

	// Panels
	let showMemoryPanel = $state(false);
	let showConversations = $state(false);
	let memories = $state<MemoryItem[]>([]);
	let conversations = $state<ConversationSummary[]>([]);

	const roles = [
		{ value: 'internal_staff', label: 'Internal Staff (Full Access)', short: 'Internal' },
		{ value: 'SUP-NESTLE-MY', label: 'Nestle Malaysia (Supplier)', short: 'Nestle MY' },
		{ value: 'SUP-UNILEVER-MY', label: 'Unilever Malaysia (Supplier)', short: 'Unilever MY' },
		{ value: 'SUP-SAMSUNG-MY', label: 'Samsung Malaysia (Supplier)', short: 'Samsung MY' },
		{ value: 'SUP-LOREAL-MY', label: "L'Oreal Malaysia (Supplier)", short: "L'Oreal MY" },
	];

	const fallbackSuggestions = [
		'Which grocery brands have the highest revenue YTD?',
		'How many products are in each lifecycle stage?',
		'Compare electronics vs fashion category revenue',
		'Show the top 10 brands by units sold YTD',
		'What products are in clearance stage with most inventory?',
	];

	const supplierSuggestions: Record<string, string[]> = {
		'SUP-NESTLE-MY': [
			'How are my top products performing this month?',
			'What is my brand revenue vs last quarter?',
			'Which of my products have the highest velocity?',
			'Show my product lifecycle distribution',
			'Which of my categories need restocking?',
		],
		'SUP-UNILEVER-MY': [
			'How are my household brands performing?',
			'Show revenue trends for my product lines',
			'Which products have declining sales velocity?',
			'What is my category market share?',
			'List my top 10 products by units sold',
		],
		'SUP-SAMSUNG-MY': [
			'How are my electronics performing this quarter?',
			'Which Samsung products have the highest revenue?',
			'Show my product lifecycle stages',
			'Compare my flagship vs budget product performance',
			'What is my return rate across categories?',
		],
		'SUP-LOREAL-MY': [
			'How are my beauty products trending?',
			'Which product lines have the best velocity?',
			'Show revenue breakdown by product category',
			'What products are in clearance stage?',
			'Compare my skincare vs haircare performance',
		],
	};

	const PIPELINE_NODES = [
		{ id: 'inject_rbac', label: 'RBAC Injection', icon: '🔒', desc: 'Apply role-based access filters', tech: 'LangGraph Node' },
		{ id: 'classify_query', label: 'Query Classification', icon: '🏷️', desc: 'LLM classifies intent into query type', tech: 'Vertex AI (Gemini)' },
		{ id: 'build_aggregation', label: 'Build MQL Pipeline', icon: '🔧', desc: 'LLM generates MongoDB aggregation from natural language', tech: 'Vertex AI → MongoDB MQL' },
		{ id: 'run_aggregation', label: 'Execute Aggregation', icon: '⚡', desc: 'Run MQL pipeline against MongoDB collection', tech: 'MongoDB Aggregation' },
		{ id: 'check_realtime', label: 'Realtime KPI Check', icon: '📡', desc: 'Query realtime_kpis for velocity anomalies', tech: 'MongoDB Aggregation' },
		{ id: 'vector_search_products', label: 'Vector Search', icon: '🔍', desc: 'Semantic similarity search across product embeddings', tech: 'Voyage AI + MongoDB Atlas Vector Search' },
		{ id: 'rerank_results', label: 'Rerank Results', icon: '📊', desc: 'Re-score search results with cross-encoder', tech: 'Voyage AI Rerank-2.5' },
		{ id: 'generate_insights', label: 'Generate Insights', icon: '🧠', desc: 'Synthesize all data into business insights', tech: 'Vertex AI (Gemini)' },
		{ id: 'format_response', label: 'Format Response', icon: '📝', desc: 'Role-based output formatting with RBAC scoping', tech: 'LangGraph Node' },
	];

	function getStepStatus(step: PipelineStep): 'success' | 'error' | 'skipped' | 'done' {
		if (step.status === 'error') return 'error';
		if (step.status === 'skipped') return 'skipped';
		if (step.status === 'success') return 'success';
		return 'done';
	}

	function getStepSummary(step: PipelineStep): string {
		const parts: string[] = [];
		if (step.query_type) parts.push(`type: ${step.query_type}`);
		if (step.access_level) parts.push(String(step.access_level));
		if (step.collection) parts.push(`${step.collection}`);
		if (step.pipeline_stages) parts.push(`${step.pipeline_stages} stages`);
		if (step.result_count !== undefined) parts.push(`${step.result_count} results`);
		if (step.kpi_count !== undefined) parts.push(`${step.kpi_count} KPIs`);
		if (step.anomaly_count !== undefined && (step.anomaly_count as number) > 0) parts.push(`${step.anomaly_count} anomalies`);
		if (step.input_count !== undefined) parts.push(`${step.input_count} in → ${step.output_count ?? '?'} out`);
		if (step.view_type) parts.push(`${step.view_type} view`);
		if (step.reason) parts.push(String(step.reason));
		if (step.error && step.status === 'error') parts.push(String(step.error));
		return parts.join(' · ');
	}

	function toggleNodeExpand(nodeId: string) {
		const next = new Set(expandedNodes);
		if (next.has(nodeId)) next.delete(nodeId);
		else next.add(nodeId);
		expandedNodes = next;
	}

	function totalPipelineDuration(steps: PipelineStep[]): number {
		return steps.reduce((sum, s) => sum + ((s.duration_ms as number) || 0), 0);
	}

	function maxNodeDuration(steps: PipelineStep[]): number {
		return Math.max(...steps.map((s) => (s.duration_ms as number) || 0), 1);
	}

	function isSupplierMode(): boolean {
		return role.startsWith('SUP-');
	}

	function supplierShortName(): string {
		return roles.find((r) => r.value === role)?.short ?? role;
	}

	function supplierInitials(): string {
		const name = supplierShortName();
		return name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase();
	}

	function currentSuggestions(): string[] {
		if (isSupplierMode()) {
			return supplierSuggestions[role] ?? fallbackSuggestions;
		}
		const u = selectedUser();
		return u?.insights_suggestions?.length ? u.insights_suggestions : fallbackSuggestions;
	}

	$effect(() => {
		getAppUsers().then((u) => (users = u)).catch(() => {});
	});

	function effectiveUserId(): string {
		return isSupplierMode() ? role : selectedUserId;
	}

	$effect(() => {
		const _uid = selectedUserId;
		const _role = role;
		sessionId = `insights-${isSupplierMode() ? _role : _uid}-${Date.now()}`;
		messages = [];
	});

	function submitSuggestion(text: string) {
		question = text;
		ask();
	}

	async function ask() {
		if (!question.trim() || loading) return;
		const q = question;
		question = '';
		messages = [...messages, { role: 'user', content: q, userRole: role }];
		loading = true;

		try {
			const data: InsightsResult = await askInsights(q, role, sessionId, effectiveUserId());
			messages = [
				...messages,
				{
					role: 'assistant',
					content: data.insight || data.error || 'No results',
					mql: data.mql,
					result_count: data.aggregation_results?.length ?? data.search_results?.length ?? 0,
					has_anomaly: data.has_anomaly,
					anomaly_message: data.anomaly_message,
					query_type: data.query_type,
					latency_ms: data.latency_ms,
					preferences_applied: data.preferences_applied,
					preference_saved: data.preference_saved,
					pipeline: (data.queries_executed as PipelineStep[]) ?? [],
				},
			];
		} catch (e) {
			messages = [...messages, { role: 'assistant', content: `Error: ${e}` }];
		} finally {
			loading = false;
		}
	}

	function newSession() {
		sessionId = `insights-${Date.now()}`;
		messages = [];
	}

	async function loadMemories() {
		showMemoryPanel = !showMemoryPanel;
		if (showMemoryPanel) {
			try {
				memories = await getInsightsMemories(selectedUserId);
			} catch {
				memories = [];
			}
		}
	}

	async function loadConversations() {
		showConversations = !showConversations;
		if (showConversations) {
			try {
				conversations = await getInsightsConversations(selectedUserId);
			} catch {
				conversations = [];
			}
		}
	}

	function resumeConversation(conv: ConversationSummary) {
		sessionId = conv.threadId;
		showConversations = false;
		messages = [];
	}

	function selectedUser(): AppUser | undefined {
		return users.find((u) => u.userId === selectedUserId);
	}
</script>

<div class="flex h-full">
	<!-- Conversations sidebar -->
	{#if showConversations}
		<div class="w-72 border-r border-gray-200 bg-gray-50 flex flex-col overflow-hidden">
			<div class="p-3 border-b border-gray-200 flex items-center justify-between">
				<span class="text-sm font-semibold text-gray-700">Past Conversations</span>
				<button onclick={() => (showConversations = false)} class="text-gray-400 hover:text-gray-600 cursor-pointer" aria-label="Close conversations panel">
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
				</button>
			</div>
			<div class="flex-1 overflow-auto">
				{#if conversations.length === 0}
					<p class="text-xs text-gray-400 p-3">No conversations yet.</p>
				{:else}
					{#each conversations as conv}
						<button
							onclick={() => resumeConversation(conv)}
							class="w-full text-left px-3 py-2.5 border-b border-gray-100 hover:bg-white transition-colors cursor-pointer"
						>
							<p class="text-sm font-medium text-gray-700 truncate">{conv.title || conv.lastQuestion}</p>
							<div class="flex items-center gap-2 mt-0.5">
								<span class="text-xs text-gray-400">{conv.turnCount} turns</span>
								{#if conv.category}
									<span class="text-xs px-1.5 py-0.5 rounded bg-amber-50 text-amber-600">{conv.category}</span>
								{/if}
							</div>
						</button>
					{/each}
				{/if}
			</div>
		</div>
	{/if}

	<!-- Main chat area -->
	<div class="flex-1 flex flex-col">
		<div class="p-4 border-b border-gray-200 bg-white">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<button
						onclick={loadConversations}
						class="p-1.5 rounded hover:bg-gray-100 text-gray-500 cursor-pointer"
						title="Past conversations"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
					</button>
					<div>
						<h2 class="text-xl font-bold text-gray-800">Product Insights</h2>
						<p class="text-xs text-gray-500">9-node AI pipeline with RBAC + agentic memory</p>
					</div>
				</div>
				<div class="flex items-center gap-3">
					{#if !isSupplierMode()}
						<button
							onclick={loadMemories}
							class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border {showMemoryPanel ? 'border-purple-300 bg-purple-50 text-purple-700' : 'border-gray-200 text-gray-600 hover:border-purple-200'} cursor-pointer"
						>
							<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path></svg>
							Memories
						</button>
					{/if}
					<button onclick={newSession} class="px-3 py-1.5 text-xs rounded-lg border border-gray-200 text-gray-600 hover:border-amber-200 cursor-pointer">
						+ New Chat
					</button>
					<div class="flex items-center gap-2">
						<select bind:value={role} class="text-sm border rounded-lg px-2.5 py-1.5 bg-white">
							{#each roles as r}
								<option value={r.value}>{r.label}</option>
							{/each}
						</select>
					</div>
					{#if isSupplierMode()}
						<div class="flex items-center gap-2 pl-1">
							<div class="w-7 h-7 rounded-full bg-[#c8a951] text-white flex items-center justify-center text-[10px] font-bold">
								{supplierInitials()}
							</div>
							<span class="text-sm font-medium text-gray-700">{supplierShortName()}</span>
						</div>
					{:else if users.length > 0}
						<div class="flex items-center gap-2">
							<div class="w-7 h-7 rounded-full bg-[#c8a951] text-white flex items-center justify-center text-xs font-semibold">
								{selectedUser()?.avatar ?? '??'}
							</div>
							<select bind:value={selectedUserId} class="text-sm border rounded-lg px-2.5 py-1.5 bg-white">
								{#each users as u}
									<option value={u.userId}>{u.name}</option>
								{/each}
							</select>
						</div>
					{/if}
				</div>
			</div>
			{#if isSupplierMode()}
				<div class="mt-2 px-3 py-1.5 bg-amber-50/80 border border-amber-200 rounded-lg text-xs text-amber-800 flex items-center gap-2">
					<svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
					Supplier view — results auto-filtered to <strong>{supplierShortName()}</strong> data
				</div>
			{/if}
		</div>

		<!-- Messages -->
		<div class="flex-1 overflow-auto p-6 space-y-4">
			{#if messages.length === 0}
				<div class="text-center py-12 space-y-4">
					<div class="w-14 h-14 mx-auto rounded-full bg-[#c8a951]/10 flex items-center justify-center">
						<svg class="w-7 h-7 text-[#c8a951]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
					</div>
					{#if isSupplierMode()}
						<p class="text-lg text-gray-500">Ask about your product performance</p>
						<p class="text-xs text-gray-400">
							Viewing as <strong>{supplierShortName()}</strong> — queries are scoped to your data
						</p>
					{:else}
						<p class="text-lg text-gray-500">Ask about product performance and trends</p>
						<p class="text-xs text-gray-400">
							Say <strong>"remember..."</strong> to save preferences. They'll be applied to future queries.
						</p>
						{#if selectedUser()?.focus}
							<p class="text-xs text-gray-400 mt-1">
								{selectedUser()?.name}'s focus: <span class="text-gray-500">{selectedUser()?.focus}</span>
							</p>
						{/if}
					{/if}
				<div class="flex flex-wrap justify-center gap-2 max-w-xl mx-auto mt-2">
					{#each currentSuggestions() as sug}
						<button
							onclick={() => submitSuggestion(sug)}
							class="text-xs px-3 py-1.5 rounded-full border border-gray-200 text-gray-600 hover:border-[#c8a951] hover:text-[#c8a951] hover:bg-amber-50/50 transition-colors cursor-pointer"
						>{sug}</button>
					{/each}
				</div>
				</div>
			{/if}

			{#each messages as msg, i}
				<div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
					<div class="max-w-3xl {msg.role === 'user' ? 'bg-[#003b73] text-white rounded-2xl rounded-br-sm' : 'bg-white border border-gray-100 shadow-sm rounded-2xl rounded-bl-sm'} px-5 py-3.5">
						{#if msg.userRole && msg.userRole !== 'internal_staff'}
							<p class="text-[11px] opacity-60 mb-1.5 font-medium uppercase tracking-wide">as {msg.userRole}</p>
						{/if}
						{#if msg.preference_saved}
							<div class="mb-2.5 px-3 py-2 bg-purple-50 border border-purple-200 rounded-lg text-xs text-purple-700 flex items-center gap-2">
								<svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
								Preference saved to memory
							</div>
						{/if}

						{#if msg.role === 'user'}
							<p class="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
						{:else}
							<div class="text-sm text-gray-700">
								<Markdown content={msg.content} />
							</div>
						{/if}

						{#if msg.role === 'assistant'}
							<div class="flex items-center gap-2 mt-3 pt-2.5 border-t border-gray-100 flex-wrap">
								{#if msg.latency_ms}
									<span class="text-[11px] text-gray-400 tabular-nums">{(msg.latency_ms / 1000).toFixed(1)}s</span>
								{/if}
								{#if msg.query_type}
									<span class="text-[11px] px-1.5 py-0.5 rounded-md bg-gray-100 text-gray-500 font-medium">{msg.query_type}</span>
								{/if}
								{#if msg.has_anomaly}
									<span class="text-[11px] px-1.5 py-0.5 rounded-md bg-amber-50 text-amber-700 font-medium" title={msg.anomaly_message || ''}>velocity spike</span>
								{/if}
								{#if msg.preferences_applied}
									<span class="text-[11px] px-1.5 py-0.5 rounded-md bg-purple-50 text-purple-600 font-medium">prefs applied</span>
								{/if}
								{#if msg.pipeline && msg.pipeline.length > 0}
									<button
										onclick={() => (showPipeline = showPipeline === i ? null : i)}
										class="text-[11px] text-teal-600 hover:text-teal-800 font-medium cursor-pointer flex items-center gap-1"
									>
										<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
										{msg.pipeline.length} nodes
									</button>
								{/if}
								{#if msg.mql}
									<button
										onclick={() => (showMQL = showMQL === i ? null : i)}
										class="text-[11px] text-blue-600 hover:text-blue-800 font-medium cursor-pointer"
									>
										{showMQL === i ? 'Hide MQL' : 'MQL'}
									</button>
								{/if}
								{#if msg.result_count !== undefined}
									<span class="text-[11px] text-gray-400">{msg.result_count} results</span>
								{/if}
							</div>
						{/if}

						{#if msg.mql && showMQL === i}
							<pre class="mt-2 p-3 bg-gray-900 text-green-400 rounded-lg text-xs overflow-auto max-h-48 leading-relaxed">{JSON.stringify(msg.mql, null, 2)}</pre>
						{/if}
					</div>
				</div>
			{/each}

			{#if loading}
				<div class="flex justify-start">
					<div class="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-5 py-4 shadow-sm">
						<div class="flex items-center gap-1.5">
							<span class="w-2 h-2 rounded-full bg-[#c8a951]/50 animate-bounce" style="animation-delay: 0ms"></span>
							<span class="w-2 h-2 rounded-full bg-[#c8a951]/50 animate-bounce" style="animation-delay: 150ms"></span>
							<span class="w-2 h-2 rounded-full bg-[#c8a951]/50 animate-bounce" style="animation-delay: 300ms"></span>
						</div>
					</div>
				</div>
			{/if}
		</div>

		<!-- Input -->
		<div class="p-4 border-t border-gray-200 bg-white">
			<div class="flex gap-3 max-w-3xl mx-auto">
				<input
					bind:value={question}
					placeholder="Ask about product insights..."
					class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#003b73]/30"
					onkeydown={(e) => { if (e.key === 'Enter') ask(); }}
					disabled={loading}
				/>
				<button onclick={ask} disabled={loading} class="px-6 py-2 bg-[#003b73] text-white rounded-lg hover:opacity-90 cursor-pointer disabled:opacity-50">
					Ask
				</button>
			</div>
		</div>
	</div>

	<!-- Memory panel (internal staff only) -->
	{#if showMemoryPanel && !isSupplierMode()}
		<div class="w-72 border-l border-gray-200 bg-gray-50 flex flex-col overflow-hidden">
			<div class="p-3 border-b border-gray-200 flex items-center justify-between">
				<span class="text-sm font-semibold text-gray-700">Saved Memories</span>
				<button onclick={() => (showMemoryPanel = false)} class="text-gray-400 hover:text-gray-600 cursor-pointer" aria-label="Close memory panel">
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
				</button>
			</div>
			<div class="p-3 space-y-1">
				<p class="text-xs text-gray-500">
					User: <strong>{selectedUser()?.name ?? selectedUserId}</strong>
				</p>
				{#if selectedUser()?.role}
					<p class="text-xs text-gray-400">{selectedUser()?.role} &mdash; {selectedUser()?.department}</p>
				{/if}
			</div>
			<div class="flex-1 overflow-auto px-3 pb-3 space-y-2">
				{#if memories.length === 0}
					<p class="text-xs text-gray-400">No memories saved yet. Try saying "remember I prefer charts" in the chat.</p>
				{:else}
					{#each memories as mem}
						<div class="p-2.5 bg-white rounded-lg border border-gray-100 shadow-sm">
							<p class="text-xs font-semibold text-purple-700">{mem.key}</p>
							<p class="text-xs text-gray-600 mt-0.5">{mem.value?.content ?? JSON.stringify(mem.value)}</p>
						</div>
					{/each}
				{/if}
			</div>
		</div>
	{/if}
</div>

<!-- Pipeline Process Modal -->
{#if showPipeline !== null}
	{@const msg = messages[showPipeline]}
	{@const steps = msg?.pipeline ?? []}
	{@const executedIds = new Set(steps.map((s: PipelineStep) => s.node))}
	{@const totalDur = totalPipelineDuration(steps)}
	{@const maxDur = maxNodeDuration(steps)}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
		onclick={() => { showPipeline = null; expandedNodes = new Set(); }}
		onkeydown={(e) => { if (e.key === 'Escape') { showPipeline = null; expandedNodes = new Set(); } }}
	>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 overflow-hidden"
			onclick={(e) => e.stopPropagation()}
			onkeydown={() => {}}
		>
			<!-- Header -->
			<div class="px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
				<div class="flex items-center justify-between">
					<div>
						<div class="flex items-center gap-2">
							<svg class="w-4 h-4 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
							<h3 class="text-sm font-bold text-gray-800">LangGraph Pipeline Trace</h3>
						</div>
						<div class="flex items-center gap-3 mt-1">
							<span class="text-[11px] text-gray-400">{steps.length} of {PIPELINE_NODES.length} nodes executed</span>
							<span class="text-[11px] text-gray-300">|</span>
							<span class="text-[11px] text-gray-400 tabular-nums">Node time: {(totalDur / 1000).toFixed(1)}s</span>
							{#if msg?.latency_ms}
								<span class="text-[11px] text-gray-300">|</span>
								<span class="text-[11px] text-gray-400 tabular-nums">Total: {(msg.latency_ms / 1000).toFixed(1)}s</span>
							{/if}
						</div>
					</div>
					<button onclick={() => { showPipeline = null; expandedNodes = new Set(); }} class="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 cursor-pointer" aria-label="Close pipeline view">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
					</button>
				</div>
			</div>

			<!-- Pipeline steps -->
			<div class="px-6 py-4 max-h-[70vh] overflow-auto">
				{#each PIPELINE_NODES as node, ni}
					{@const step = steps.find((s: PipelineStep) => s.node === node.id)}
					{@const executed = executedIds.has(node.id)}
					{@const status = step ? getStepStatus(step) : 'pending'}
					{@const summary = step ? getStepSummary(step) : ''}
					{@const dur = (step?.duration_ms as number) || 0}
					{@const isExpanded = expandedNodes.has(node.id)}
					{@const hasDetail = executed && step && status !== 'pending'}

					<div class="flex gap-3">
						<!-- Timeline connector -->
						<div class="flex flex-col items-center w-8 shrink-0">
							<div class="w-7 h-7 rounded-full flex items-center justify-center text-sm shrink-0
								{status === 'success' || status === 'done' ? 'bg-emerald-100' : ''}
								{status === 'skipped' ? 'bg-gray-100' : ''}
								{status === 'error' ? 'bg-red-100' : ''}
								{status === 'pending' ? 'bg-gray-50 border border-dashed border-gray-200' : ''}
							">{node.icon}</div>
							{#if ni < PIPELINE_NODES.length - 1}
								<div class="w-px flex-1 min-h-3 {executed ? 'bg-emerald-200' : 'bg-gray-100'}"></div>
							{/if}
						</div>

						<!-- Node content -->
						<div class="flex-1 pb-3 min-w-0">
							<!-- Clickable header row -->
							<button
								class="w-full text-left cursor-pointer group"
								onclick={() => { if (hasDetail) toggleNodeExpand(node.id); }}
								disabled={!hasDetail}
							>
								<div class="flex items-center gap-2">
									<span class="text-xs font-semibold {executed ? 'text-gray-800' : 'text-gray-400'}">{node.label}</span>
									{#if status === 'success' || status === 'done'}
										<svg class="w-3 h-3 text-emerald-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
									{:else if status === 'skipped'}
										<span class="text-[9px] px-1 py-0.5 rounded bg-gray-100 text-gray-400 font-medium">SKIP</span>
									{:else if status === 'error'}
										<svg class="w-3 h-3 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
									{/if}
									{#if dur > 0}
										<span class="text-[10px] text-gray-400 tabular-nums ml-auto">{dur < 1000 ? `${Math.round(dur)}ms` : `${(dur / 1000).toFixed(1)}s`}</span>
									{/if}
									{#if hasDetail}
										<svg class="w-3 h-3 text-gray-300 group-hover:text-gray-500 transition-transform {isExpanded ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
									{/if}
								</div>

								<!-- Tech label + timing bar -->
								<div class="flex items-center gap-2 mt-1">
									<span class="text-[10px] text-gray-400">{node.tech}</span>
									{#if dur > 0 && maxDur > 0}
										<div class="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
											<div
												class="h-full rounded-full {status === 'error' ? 'bg-red-300' : status === 'skipped' ? 'bg-gray-200' : 'bg-teal-400'}"
												style="width: {Math.max(2, (dur / maxDur) * 100)}%"
											></div>
										</div>
									{/if}
								</div>

								{#if summary && !isExpanded}
									<p class="text-[11px] mt-1 {status === 'error' ? 'text-red-500' : 'text-teal-600'} font-medium truncate">{summary}</p>
								{/if}
							</button>

							<!-- Expanded detail panel -->
							{#if isExpanded && step}
								<div class="mt-2 rounded-lg border border-gray-100 bg-gray-50/50 overflow-hidden text-[11px]">
									<!-- Key-value pairs -->
									<div class="px-3 py-2 space-y-1.5">
										{#if step.model}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Model</span><span class="text-gray-700 font-mono">{step.model}</span></div>
										{/if}
										{#if step.collection}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Collection</span><span class="text-gray-700 font-mono">{step.collection}</span></div>
										{/if}
										{#if step.index}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Index</span><span class="text-gray-700 font-mono">{step.index}</span></div>
										{/if}
										{#if step.embedding_model}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Embedding</span><span class="text-gray-700 font-mono">{step.embedding_model}</span></div>
										{/if}
										{#if step.rerank_model}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Reranker</span><span class="text-gray-700 font-mono">{step.rerank_model}</span></div>
										{/if}
										{#if step.query_type}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Query type</span><span class="text-gray-700">{step.query_type}</span></div>
										{/if}
										{#if step.access_level}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Access</span><span class="text-gray-700">{step.access_level}</span></div>
										{/if}
										{#if step.filter && Object.keys(step.filter as Record<string, unknown>).length > 0}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">RBAC filter</span><span class="text-gray-700 font-mono">{JSON.stringify(step.filter)}</span></div>
										{/if}
										{#if step.result_count !== undefined}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Results</span><span class="text-gray-700">{step.result_count}</span></div>
										{/if}
										{#if step.kpi_count !== undefined}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">KPIs</span><span class="text-gray-700">{step.kpi_count} windows{step.has_anomaly ? `, ${step.anomaly_count} anomalies` : ''}</span></div>
										{/if}
										{#if step.anomaly_threshold}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Threshold</span><span class="text-gray-700 font-mono">{step.anomaly_threshold}</span></div>
										{/if}
										{#if step.input_count !== undefined}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Reranking</span><span class="text-gray-700">{step.input_count} in → {step.output_count} out (top score: {((step.top_rerank_score as number) || 0).toFixed(3)})</span></div>
										{/if}
										{#if step.prompt_chars}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Prompt</span><span class="text-gray-700">{((step.prompt_chars as number) / 1000).toFixed(1)}k chars</span></div>
										{/if}
										{#if step.response_chars}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Response</span><span class="text-gray-700">{((step.response_chars as number) / 1000).toFixed(1)}k chars</span></div>
										{/if}
										{#if step.preferences_injected}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Prefs</span><span class="text-purple-600">user preferences injected into prompt</span></div>
										{/if}
										{#if step.view_type}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">View</span><span class="text-gray-700">{step.view_type} ({((step.output_chars as number) / 1000).toFixed(1)}k chars)</span></div>
										{/if}
										{#if step.explanation}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Explanation</span><span class="text-gray-600">{step.explanation}</span></div>
										{/if}
										{#if step.reason}
											<div class="flex gap-2"><span class="text-gray-400 shrink-0 w-20">Reason</span><span class="text-gray-500 italic">{step.reason}</span></div>
										{/if}
										{#if step.error}
											<div class="flex gap-2"><span class="text-red-400 shrink-0 w-20">Error</span><span class="text-red-600">{step.error}</span></div>
										{/if}
										{#if step.data_sources && typeof step.data_sources === 'object'}
											<div class="flex gap-2">
												<span class="text-gray-400 shrink-0 w-20">Data fed</span>
												<span class="text-gray-700">
													{#each Object.entries(step.data_sources as Record<string, unknown>) as [k, v]}
														<span class="inline-block mr-2">{String(v)} {k.replace(/_/g, ' ')}</span>
													{/each}
												</span>
											</div>
										{/if}
									</div>

									<!-- MQL Pipeline (if present) -->
									{#if step.mql_pipeline && Array.isArray(step.mql_pipeline) && (step.mql_pipeline as unknown[]).length > 0}
										<div class="border-t border-gray-100">
											<div class="px-3 py-1.5 bg-gray-100/50 text-[10px] font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
												<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>
												MQL Pipeline{#if step.stage_types} — {(step.stage_types as string[]).join(' → ')}{/if}
											</div>
											<pre class="px-3 py-2 text-[10px] leading-relaxed bg-[#1e293b] text-cyan-300 overflow-x-auto max-h-40 font-mono">{JSON.stringify(step.mql_pipeline, null, 2)}</pre>
										</div>
									{/if}

									<!-- LLM Response (if present) -->
									{#if step.llm_response}
										<div class="border-t border-gray-100">
											<div class="px-3 py-1.5 bg-gray-100/50 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">LLM Response</div>
											<pre class="px-3 py-2 text-[10px] leading-relaxed text-gray-600 overflow-x-auto max-h-32 whitespace-pre-wrap">{step.llm_response}</pre>
										</div>
									{/if}

									<!-- Sample Results (if present) -->
									{#if step.sample_results && Array.isArray(step.sample_results) && (step.sample_results as unknown[]).length > 0}
										<div class="border-t border-gray-100">
											<div class="px-3 py-1.5 bg-gray-100/50 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Sample Results (top 3)</div>
											<pre class="px-3 py-2 text-[10px] leading-relaxed bg-[#1e293b] text-emerald-300 overflow-x-auto max-h-40 font-mono">{JSON.stringify(step.sample_results, null, 2)}</pre>
										</div>
									{/if}
								</div>
							{/if}
						</div>
					</div>
				{/each}
			</div>

			<!-- Footer -->
			<div class="px-6 py-3 border-t border-gray-100 bg-gray-50/50 flex items-center justify-between">
				<div class="flex items-center gap-3 text-[11px] text-gray-400">
					<span class="flex items-center gap-1">
						<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
						LangGraph
					</span>
					<span class="text-gray-300">|</span>
					<span>{msg?.query_type ?? '—'}</span>
					<span class="text-gray-300">|</span>
					<span class="tabular-nums">Node: {(totalDur / 1000).toFixed(1)}s</span>
					{#if msg?.latency_ms}
						<span class="text-gray-300">|</span>
						<span class="tabular-nums">E2E: {(msg.latency_ms / 1000).toFixed(1)}s</span>
					{/if}
				</div>
				<button onclick={() => { showPipeline = null; expandedNodes = new Set(); }} class="text-xs px-3 py-1.5 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 cursor-pointer font-medium">
					Close
				</button>
			</div>
		</div>
	</div>
{/if}
