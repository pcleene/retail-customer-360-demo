<script lang="ts">
	import {
		askCopilot,
		getCopilotMemories,
		getCopilotConversations,
		getAppUsers,
		type CopilotResult,
		type MemoryItem,
		type ConversationSummary,
		type AppUser,
		type MemoryTraceEntry,
	} from '$lib/api';
	import Markdown from '$lib/components/Markdown.svelte';

	let question = $state('');
	let loading = $state(false);
	let messages = $state<
		{ role: string; content: string; mql?: unknown; latency_ms?: number; memory_trace?: MemoryTraceEntry[] }[]
	>([]);

	// User & session management
	let users = $state<AppUser[]>([]);
	let selectedUserId = $state('analyst-1');
	let sessionId = $state(`session-${Date.now()}`);

	// Side panels
	let showMemoryPanel = $state(false);
	let showConversations = $state(false);
	let memories = $state<MemoryItem[]>([]);
	let conversations = $state<ConversationSummary[]>([]);

	let showMQL = $state<number | null>(null);
	let showTrace = $state<number | null>(null);

	const fallbackSuggestions = [
		'What is the churn risk distribution across tiers?',
		'How many tri-entity customers are in Selangor?',
		'Compare average LTV for retail_credit vs credit_bank segments',
		'How many active cross-sell campaigns are running?',
		'Show customer counts by segment',
	];

	function currentSuggestions(): string[] {
		const u = selectedUser();
		return u?.copilot_suggestions?.length ? u.copilot_suggestions : fallbackSuggestions;
	}

	$effect(() => {
		getAppUsers().then((u) => (users = u)).catch(() => {});
	});

	$effect(() => {
		// Reset session and messages when switching users
		const _uid = selectedUserId;
		sessionId = `session-${_uid}-${Date.now()}`;
		messages = [];
	});

	async function ask() {
		if (!question.trim() || loading) return;
		const q = question;
		question = '';
		messages = [...messages, { role: 'user', content: q }];
		loading = true;

		try {
			const data: CopilotResult = await askCopilot(q, sessionId, selectedUserId);
			messages = [
				...messages,
				{
					role: 'assistant',
					content: data.answer,
					mql: data.mql,
					latency_ms: data.latency_ms,
					memory_trace: data.memory_trace,
				},
			];
		} catch (e) {
			messages = [...messages, { role: 'assistant', content: `Error: ${e}` }];
		} finally {
			loading = false;
		}
	}

	function submitSuggestion(text: string) {
		question = text;
		ask();
	}

	function newSession() {
		sessionId = `session-${Date.now()}`;
		messages = [];
	}

	async function loadMemories() {
		showMemoryPanel = !showMemoryPanel;
		if (showMemoryPanel) {
			try {
				memories = await getCopilotMemories(selectedUserId);
			} catch {
				memories = [];
			}
		}
	}

	async function loadConversations() {
		showConversations = !showConversations;
		if (showConversations) {
			try {
				conversations = await getCopilotConversations(selectedUserId);
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
									<span class="text-xs px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">{conv.category}</span>
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
						<h2 class="text-xl font-bold text-gray-800">Customer Intelligence Co-pilot</h2>
						<p class="text-xs text-gray-500">MCP Server + LangGraph ReAct agent with agentic memory</p>
					</div>
				</div>
				<div class="flex items-center gap-3">
					<button
						onclick={loadMemories}
						class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border {showMemoryPanel ? 'border-purple-300 bg-purple-50 text-purple-700' : 'border-gray-200 text-gray-600 hover:border-purple-200'} cursor-pointer"
					>
						<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path></svg>
						Memories
					</button>
					<button onclick={newSession} class="px-3 py-1.5 text-xs rounded-lg border border-gray-200 text-gray-600 hover:border-blue-200 cursor-pointer">
						+ New Chat
					</button>
					{#if users.length > 0}
						<div class="flex items-center gap-2">
							<div class="w-7 h-7 rounded-full bg-[#003b73] text-white flex items-center justify-center text-xs font-semibold">
								{selectedUser()?.avatar ?? '??'}
							</div>
							<select bind:value={selectedUserId} class="text-sm border rounded px-2 py-1 bg-white">
								{#each users as u}
									<option value={u.userId}>{u.name}</option>
								{/each}
							</select>
						</div>
					{/if}
				</div>
			</div>
		</div>

		<!-- Messages -->
		<div class="flex-1 overflow-auto p-6 space-y-4">
			{#if messages.length === 0}
				<div class="text-center py-12 space-y-4">
					<div class="w-14 h-14 mx-auto rounded-full bg-[#003b73]/10 flex items-center justify-center">
						<svg class="w-7 h-7 text-[#003b73]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path></svg>
					</div>
					<p class="text-lg text-gray-500">Ask anything about your customers</p>
					<p class="text-xs text-gray-400">
						Say <strong>"remember..."</strong> to save preferences across sessions
					</p>
				{#if selectedUser()?.focus}
					<p class="text-xs text-gray-400 mt-1">
						{selectedUser()?.name}'s focus: <span class="text-gray-500">{selectedUser()?.focus}</span>
					</p>
				{/if}
				<div class="flex flex-wrap justify-center gap-2 max-w-xl mx-auto mt-2">
					{#each currentSuggestions() as sug}
						<button
							onclick={() => submitSuggestion(sug)}
							class="text-xs px-3 py-1.5 rounded-full border border-gray-200 text-gray-600 hover:border-[#003b73] hover:text-[#003b73] hover:bg-blue-50/50 transition-colors cursor-pointer"
						>{sug}</button>
					{/each}
				</div>
				</div>
			{/if}

			{#each messages as msg, i}
				<div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
					<div class="max-w-3xl {msg.role === 'user' ? 'bg-[#003b73] text-white rounded-2xl rounded-br-sm' : 'bg-white border border-gray-100 shadow-sm rounded-2xl rounded-bl-sm'} px-5 py-3.5">
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
								{#if msg.mql}
									<button
										onclick={() => (showMQL = showMQL === i ? null : i)}
										class="text-[11px] text-blue-600 hover:text-blue-800 font-medium cursor-pointer"
									>
										{showMQL === i ? 'Hide MQL' : 'Show MQL'}
									</button>
								{/if}
								{#if msg.memory_trace && msg.memory_trace.length > 0}
									<button
										onclick={() => (showTrace = showTrace === i ? null : i)}
										class="text-[11px] text-purple-600 hover:text-purple-800 font-medium cursor-pointer"
									>
										{showTrace === i ? 'Hide Memory Trace' : `Memory (${msg.memory_trace.length})`}
									</button>
								{/if}
							</div>
						{/if}

						{#if showMQL === i && msg.mql}
							<pre class="mt-2 p-3 bg-gray-900 text-green-400 rounded-lg text-xs overflow-auto max-h-48 leading-relaxed">{JSON.stringify(msg.mql, null, 2)}</pre>
						{/if}

						{#if showTrace === i && msg.memory_trace}
							<div class="mt-2 space-y-1.5">
								{#each msg.memory_trace as trace}
									<div class="p-2.5 bg-purple-50/70 border border-purple-100 rounded-lg text-xs">
										<span class="font-semibold text-purple-700">{trace.tool}</span>
										<span class="text-purple-400 ml-1.5">{JSON.stringify(trace.input)}</span>
										<p class="text-purple-600 mt-1 leading-relaxed">{trace.output}</p>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			{/each}

			{#if loading}
				<div class="flex justify-start">
					<div class="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-5 py-4 shadow-sm">
						<div class="flex items-center gap-1.5">
							<span class="w-2 h-2 rounded-full bg-[#003b73]/40 animate-bounce" style="animation-delay: 0ms"></span>
							<span class="w-2 h-2 rounded-full bg-[#003b73]/40 animate-bounce" style="animation-delay: 150ms"></span>
							<span class="w-2 h-2 rounded-full bg-[#003b73]/40 animate-bounce" style="animation-delay: 300ms"></span>
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
					placeholder="Ask a question about your customers..."
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

	<!-- Memory panel -->
	{#if showMemoryPanel}
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
					<p class="text-xs text-gray-400">No memories saved yet. Try saying "remember I prefer percentages" in the chat.</p>
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
