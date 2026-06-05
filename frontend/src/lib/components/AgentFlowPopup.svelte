<script lang="ts">
	import type { RecommendationResult } from '$lib/api';

	interface Props {
		result: RecommendationResult;
		customerName: string;
		onclose: () => void;
	}
	let { result, customerName, onclose }: Props = $props();

	const steps = $derived(result.reasoning_steps ?? []);
	const queries = $derived(result.queries_executed ?? []);
	const enrollment = $derived(result.enrollment_result ?? {});
	const totalMs = $derived(steps.reduce((sum: number, s: { duration_ms?: number }) => sum + (s.duration_ms ?? 0), 0));
	const mongoOps = $derived(queries.filter((q: Record<string, unknown>) => q.collection).length);
	const llmCalls = $derived(queries.filter((q: Record<string, unknown>) => String(q.operation ?? '').includes('llm')).length);
	const embedCalls = $derived(queries.filter((q: Record<string, unknown>) => String(q.operation ?? '').includes('embed')).length);
	const rerankCalls = $derived(queries.filter((q: Record<string, unknown>) => String(q.operation ?? '').includes('rerank')).length);

	function queriesForNode(nodeName: string): Record<string, unknown>[] {
		return queries.filter((q: Record<string, unknown>) => q.node === nodeName);
	}

	type NodeCfg = { label: string; desc: string; tech: string[]; accentFrom: string; accentTo: string };
	const nodeConfig: Record<string, NodeCfg> = {
		classify_intent:             { label: 'Classify Intent',          desc: 'LangGraph conditional edge routes to individual or segment branch', tech: ['LangGraph'],                          accentFrom: '#64748b', accentTo: '#94a3b8' },
		fetch_profile:               { label: 'Fetch Profile',            desc: 'Load full customer 360 document and recent transactions',           tech: ['MongoDB Atlas', 'PyMongo Async'],     accentFrom: '#3b82f6', accentTo: '#60a5fa' },
		fetch_segment:               { label: 'Fetch Segment',            desc: 'Load representative segment profiles via aggregation',               tech: ['MongoDB Atlas', 'PyMongo Async'],     accentFrom: '#3b82f6', accentTo: '#60a5fa' },
		analyze_patterns:            { label: 'Analyze Patterns',         desc: 'Deep analysis of spending, entity gaps and lifecycle stage',         tech: ['Gemini 2.5 Flash', 'LangChain'],      accentFrom: '#8b5cf6', accentTo: '#a78bfa' },
		vector_search_customers:     { label: 'Vector Search Customers',  desc: '$vectorSearch on 1024-dim Voyage embeddings for lookalikes',        tech: ['Atlas Vector Search', 'Voyage AI'],   accentFrom: '#06b6d4', accentTo: '#22d3ee' },
		vector_search_campaigns:     { label: 'Vector Search Campaigns',  desc: '$vectorSearch with pre-filter on active campaign status',           tech: ['Atlas Vector Search', 'Voyage AI'],   accentFrom: '#10b981', accentTo: '#34d399' },
		vector_search_content:       { label: 'Vector Search Content',    desc: '$vectorSearch filtered to matched campaign IDs',                    tech: ['Atlas Vector Search', 'Voyage AI'],   accentFrom: '#14b8a6', accentTo: '#2dd4bf' },
		analyze_similar_conversions: { label: 'Analyze Conversions',      desc: 'LLM analysis of lookalike conversion patterns and rates',           tech: ['Gemini 2.5 Flash', 'LangChain'],      accentFrom: '#f59e0b', accentTo: '#fbbf24' },
		determine_channel:           { label: 'Determine Channel',        desc: 'Select optimal delivery channel from engagement history',           tech: ['LangGraph Node'],                     accentFrom: '#6366f1', accentTo: '#818cf8' },
		rerank_results:              { label: 'Rerank Results',           desc: 'Cross-encoder reranking on campaigns and content assets',            tech: ['Voyage Rerank 2.5'],                  accentFrom: '#f97316', accentTo: '#fb923c' },
		generate_recommendations:    { label: 'Generate Recommendations', desc: 'Structured JSON synthesis from all upstream context',                tech: ['Gemini 2.5 Flash', 'LangChain'],      accentFrom: '#e11d48', accentTo: '#fb7185' },
		execute_actions:             { label: 'Execute Actions',          desc: 'Write ActiveCampaign + CampaignAction documents',                   tech: ['MongoDB Atlas', 'PyMongo Async'],     accentFrom: '#16a34a', accentTo: '#4PartsDistributor80' },
	};

	function cfg(step: string): NodeCfg {
		return nodeConfig[step] ?? { label: step, desc: '', tech: [], accentFrom: '#6b7280', accentTo: '#9ca3af' };
	}

	function fmtMs(ms: number): string {
		if (ms < 1) return '<1ms';
		if (ms < 1000) return `${Math.round(ms)}ms`;
		return `${(ms / 1000).toFixed(1)}s`;
	}

	function fmtJson(obj: unknown): string {
		try { return JSON.stringify(obj, null, 2); }
		catch { return String(obj); }
	}

	function opType(op: string): 'mongo' | 'llm' | 'embed' | 'rerank' {
		if (op.includes('llm_invoke')) return 'llm';
		if (op.includes('embed_for_query')) return 'embed';
		if (op.includes('rerank')) return 'rerank';
		return 'mongo';
	}

	function opDisplayName(op: string): string {
		if (op.includes('$vectorSearch')) return `db.collection.aggregate([$vectorSearch, ...])`;
		if (op.includes('find_one')) return 'db.collection.find_one({...})';
		if (op.includes('update_one')) return 'db.collection.update_one({...})';
		if (op.includes('insert_one')) return 'db.collection.insert_one({...})';
		if (op.includes('aggregate')) return 'db.collection.aggregate([...])';
		if (op.includes('llm_invoke')) return 'ChatVertexAI.ainvoke(prompt)';
		if (op.includes('embed_for_query')) return 'voyageai.embed(text, model="voyage-4-lite")';
		if (op.includes('rerank')) return 'voyageai.rerank(query, docs, model="rerank-2.5")';
		return op;
	}

	const opStyle: Record<string, { badge: string; icon: string }> = {
		mongo:  { badge: 'bg-[#00684A]/10 text-[#00684A] border-[#00684A]/20', icon: '🍃' },
		llm:    { badge: 'bg-violet-50 text-violet-700 border-violet-200',       icon: '✨' },
		embed:  { badge: 'bg-sky-50 text-sky-700 border-sky-200',                icon: '🧬' },
		rerank: { badge: 'bg-orange-50 text-orange-700 border-orange-200',       icon: '🏅' },
	};

	let expandedQueries = $state<Set<string>>(new Set());
	function toggleQuery(key: string) {
		const next = new Set(expandedQueries);
		if (next.has(key)) next.delete(key); else next.add(key);
		expandedQueries = next;
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="fixed inset-0 z-50 flex items-center justify-center"
	onkeydown={(e) => { if (e.key === 'Escape') onclose(); }}
>
	<div class="absolute inset-0 bg-black/60 backdrop-blur-md"></div>

	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="agent-modal relative w-full max-w-[860px] max-h-[94vh] flex flex-col rounded-2xl shadow-2xl overflow-hidden border border-white/10"
		onclick={(e) => e.stopPropagation()}
	>
		<!-- ── HEADER ── -->
		<div class="shrink-0 relative overflow-hidden">
			<div class="absolute inset-0 bg-gradient-to-br from-[#001d3d] via-[#003566] to-[#001d3d]"></div>
			<div class="absolute inset-0 opacity-[0.03]" style="background-image: url('data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2240%22 height=%2240%22><circle cx=%2220%22 cy=%2220%22 r=%221%22 fill=%22white%22/></svg>');"></div>

			<div class="relative px-7 pt-5 pb-5">
				<div class="flex items-start justify-between">
					<div class="flex items-center gap-3">
						<div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#c8a951] to-[#e0c068] flex items-center justify-center shadow-lg shadow-[#c8a951]/20">
							<svg class="w-5 h-5 text-[#001d3d]" fill="currentColor" viewBox="0 0 24 24"><path d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
						</div>
						<div>
							<h2 class="text-base font-bold text-white tracking-tight">Cross-Sell Agent Pipeline</h2>
							<div class="flex items-center gap-2 mt-1">
								<span class="text-[9px] px-2 py-0.5 rounded-full bg-white/10 text-blue-200 font-medium border border-white/10">LangGraph</span>
								<span class="text-[9px] px-2 py-0.5 rounded-full bg-white/10 text-blue-200 font-medium border border-white/10">MongoDB Atlas</span>
								<span class="text-[9px] px-2 py-0.5 rounded-full bg-white/10 text-blue-200 font-medium border border-white/10">Gemini 2.5</span>
								<span class="text-[9px] px-2 py-0.5 rounded-full bg-white/10 text-blue-200 font-medium border border-white/10">Voyage AI</span>
							</div>
						</div>
					</div>
					<button onclick={onclose} class="text-white/40 hover:text-white transition-colors cursor-pointer p-1 -mt-1 -mr-1" aria-label="Close">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
					</button>
				</div>

				<!-- Stats bar -->
				<div class="flex items-center gap-3 mt-4">
					<div class="flex-1 grid grid-cols-5 gap-2">
						<div class="bg-white/[0.07] rounded-lg px-3 py-2 text-center border border-white/[0.06]">
							<div class="text-white text-sm font-bold tabular-nums">{steps.length}</div>
							<div class="text-blue-300/60 text-[8px] uppercase tracking-widest mt-0.5">Nodes</div>
						</div>
						<div class="bg-white/[0.07] rounded-lg px-3 py-2 text-center border border-white/[0.06]">
							<div class="text-white text-sm font-bold tabular-nums">{mongoOps}</div>
							<div class="text-[#4PartsDistributor80]/60 text-[8px] uppercase tracking-widest mt-0.5">DB Ops</div>
						</div>
						<div class="bg-white/[0.07] rounded-lg px-3 py-2 text-center border border-white/[0.06]">
							<div class="text-white text-sm font-bold tabular-nums">{llmCalls}</div>
							<div class="text-violet-300/60 text-[8px] uppercase tracking-widest mt-0.5">LLM</div>
						</div>
						<div class="bg-white/[0.07] rounded-lg px-3 py-2 text-center border border-white/[0.06]">
							<div class="text-white text-sm font-bold tabular-nums">{embedCalls + rerankCalls}</div>
							<div class="text-sky-300/60 text-[8px] uppercase tracking-widest mt-0.5">AI Ops</div>
						</div>
						<div class="bg-white/[0.07] rounded-lg px-3 py-2 text-center border border-white/[0.06]">
							<div class="text-white text-sm font-bold tabular-nums">{fmtMs(totalMs)}</div>
							<div class="text-amber-300/60 text-[8px] uppercase tracking-widest mt-0.5">Total</div>
						</div>
					</div>
				</div>

				<!-- Outcome pills -->
				<div class="flex items-center gap-2 mt-3 flex-wrap">
					<span class="text-[10px] px-2.5 py-1 rounded-full bg-white/[0.08] text-white/80 border border-white/[0.08]">{customerName}</span>
					{#if enrollment.campaign_name}
						<span class="text-[10px] px-2.5 py-1 rounded-full bg-white/[0.08] text-white/80 border border-white/[0.08]">{enrollment.campaign_name}</span>
					{/if}
					{#if result.recommended_channel}
						<span class="text-[10px] px-2.5 py-1 rounded-full bg-white/[0.08] text-white/80 border border-white/[0.08]">{result.recommended_channel.replace(/_/g, ' ')}</span>
					{/if}
					{#if enrollment.enrolled}
						<span class="text-[10px] px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold ml-auto flex items-center gap-1.5">
							<span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
							Enrolled
						</span>
					{/if}
				</div>
			</div>
		</div>

		<!-- ── PIPELINE BODY ── -->
		<div class="flex-1 overflow-y-auto bg-[#f8f9fb]">
			<div class="px-7 py-6">
				{#each steps as step, i}
					{@const c = cfg(step.step)}
					{@const nodeQueries = queriesForNode(step.step)}
					{@const isOk = step.status === 'ok'}
					{@const pct = totalMs > 0 ? (step.duration_ms / totalMs) * 100 : 0}

					{#if i > 0}
						<div class="flex pl-5 h-4">
							<div class="w-px bg-gradient-to-b from-gray-300 to-gray-200"></div>
						</div>
					{/if}

					<div class="flex gap-5">
						<!-- LEFT: Timeline marker -->
						<div class="shrink-0 flex flex-col items-center relative">
							<div class="w-[42px] h-[42px] rounded-[14px] flex items-center justify-center shadow-md relative"
								 style="background: linear-gradient(135deg, {c.accentFrom}, {c.accentTo});">
								<span class="text-white text-[11px] font-black">{String(i + 1).padStart(2, '0')}</span>
							</div>
							{#if i < steps.length - 1}
								<div class="w-px flex-1 bg-gradient-to-b from-gray-300 to-transparent mt-1"></div>
							{/if}
						</div>

						<!-- RIGHT: Content -->
						<div class="flex-1 min-w-0 pb-5">
							<!-- Title + timing -->
							<div class="flex items-center justify-between mb-1">
								<div class="flex items-center gap-2">
									<h3 class="text-[13px] font-bold text-gray-900">{c.label}</h3>
									{#if isOk}
										<span class="w-[6px] h-[6px] rounded-full bg-emerald-500 shadow-sm shadow-emerald-200"></span>
									{:else}
										<span class="w-[6px] h-[6px] rounded-full bg-red-500"></span>
									{/if}
								</div>
								<div class="flex items-center gap-2">
									<div class="w-20 h-[5px] bg-gray-200/70 rounded-full overflow-hidden">
										<div class="h-full rounded-full" style="width: {Math.max(pct, 4)}%; background: linear-gradient(90deg, {c.accentFrom}, {c.accentTo});"></div>
									</div>
									<span class="text-[10px] font-mono text-gray-400 tabular-nums w-10 text-right">{fmtMs(step.duration_ms)}</span>
								</div>
							</div>
							<p class="text-[11px] text-gray-500 leading-relaxed">{c.desc}</p>

							<!-- Tech tags -->
							<div class="flex flex-wrap gap-1.5 mt-2">
								{#each c.tech as t}
									{@const isMongo = t.includes('MongoDB') || t.includes('PyMongo')}
									{@const isLLM = t.includes('Gemini') || t.includes('LangChain')}
									{@const isVoyage = t.includes('Voyage')}
									<span class="text-[9px] px-2 py-[3px] rounded-md font-semibold tracking-wide
										{isMongo ? 'bg-emerald-50 text-emerald-700' : ''}
										{isLLM ? 'bg-violet-50 text-violet-600' : ''}
										{isVoyage ? 'bg-sky-50 text-sky-600' : ''}
										{!isMongo && !isLLM && !isVoyage ? 'bg-amber-50 text-amber-700' : ''}"
									>{t}</span>
								{/each}
							</div>

							<!-- ── QUERY BLOCKS ── -->
							{#if nodeQueries.length > 0}
								<div class="mt-3 space-y-2">
									{#each nodeQueries as q, qi}
										{@const ot = opType(String(q.operation ?? ''))}
										{@const st = opStyle[ot]}
										{@const qKey = `${step.step}-${qi}`}
										{@const isOpen = expandedQueries.has(qKey)}
										{@const hasDetails = !!(q.query || q.pipeline || q.filter || q.projection || q.prompt_length || q.input_length || q.documents_count)}

										<div class="rounded-xl border border-gray-200/80 bg-white shadow-[0_1px_3px_rgba(0,0,0,0.04)] overflow-hidden">
											<!-- Query header (clickable) -->
											<button
												class="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-left transition-colors cursor-pointer hover:bg-gray-50/50"
												onclick={() => hasDetails && toggleQuery(qKey)}
											>
												<span class="text-base leading-none">{st.icon}</span>
												<code class="text-[10px] font-mono font-semibold text-gray-700 flex-1 truncate">{opDisplayName(String(q.operation ?? ''))}</code>
												{#if q.collection}
													<span class="text-[9px] px-2 py-[2px] rounded-md font-bold {st.badge} border shrink-0">{q.collection}</span>
												{/if}
												{#if q.index}
													<span class="text-[9px] px-2 py-[2px] rounded-md font-mono bg-gray-100 text-gray-500 border border-gray-200 shrink-0">{q.index}</span>
												{/if}
												{#if q.model}
													<span class="text-[9px] px-2 py-[2px] rounded-md font-mono bg-violet-50 text-violet-600 border border-violet-200 shrink-0">{q.model}</span>
												{/if}

												<div class="flex items-center gap-1.5 ml-auto shrink-0">
													{#if q.results_count != null}
														<span class="text-[9px] px-2 py-[2px] rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-bold tabular-nums">{q.results_count} docs</span>
													{/if}
													{#if q.matched != null}
														<span class="text-[9px] px-2 py-[2px] rounded-full bg-green-50 text-green-700 border border-green-200 font-bold tabular-nums">{q.matched} matched</span>
													{/if}
													{#if hasDetails}
														<svg class="w-3.5 h-3.5 text-gray-300 transition-transform {isOpen ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7"/></svg>
													{/if}
												</div>
											</button>

											<!-- Expandable detail -->
											{#if isOpen && hasDetails}
												<div class="border-t border-gray-100 bg-[#1e1e2e] text-[11px] font-mono leading-[1.7] overflow-x-auto">
													<div class="px-4 py-3 space-y-3">
														{#if q.query}
															<div>
																<span class="text-gray-500 text-[9px] uppercase tracking-widest">Query Filter</span>
																<pre class="text-[#89dceb] mt-1">{fmtJson(q.query)}</pre>
															</div>
														{/if}
														{#if q.pipeline}
															<div>
																<span class="text-gray-500 text-[9px] uppercase tracking-widest">Aggregation Pipeline</span>
																<pre class="text-[#a6e3a1] mt-1">{fmtJson(q.pipeline)}</pre>
															</div>
														{/if}
														{#if q.filter}
															<div>
																<span class="text-gray-500 text-[9px] uppercase tracking-widest">$vectorSearch Filter</span>
																<pre class="text-[#f9e2af] mt-1">{fmtJson(q.filter)}</pre>
															</div>
														{/if}
														{#if q.projection}
															<div>
																<span class="text-gray-500 text-[9px] uppercase tracking-widest">Projection</span>
																<pre class="text-[#cba6f7] mt-1">{fmtJson(q.projection)}</pre>
															</div>
														{/if}
														{#if q.prompt_length}
															<div class="text-gray-400 flex gap-5">
																<span>prompt_length: <span class="text-[#f5c2e7]">{Number(q.prompt_length).toLocaleString()}</span> chars</span>
																{#if q.response_length}
																	<span>response_length: <span class="text-[#a6e3a1]">{Number(q.response_length).toLocaleString()}</span> chars</span>
																{/if}
																{#if q.lookalikes_analyzed}
																	<span>lookalikes: <span class="text-[#89dceb]">{q.lookalikes_analyzed}</span></span>
																{/if}
															</div>
														{/if}
														{#if q.input_length}
															<div class="text-gray-400">
																input_length: <span class="text-[#89dceb]">{Number(q.input_length).toLocaleString()}</span> chars <span class="text-gray-600">→</span> <span class="text-[#f9e2af]">1024</span>-dim vector
															</div>
														{/if}
														{#if q.documents_count}
															<div class="text-gray-400">
																documents: <span class="text-[#89dceb]">{q.documents_count}</span> <span class="text-gray-600">→</span> top_k: <span class="text-[#a6e3a1]">{q.top_k}</span>
															</div>
														{/if}
														{#if q.customer_id && String(q.operation ?? '').includes('update')}
															<div class="text-gray-400">
																customer: <span class="text-[#89dceb]">"{q.customer_id}"</span> — modified: <span class="text-[#a6e3a1]">{q.modified}</span>
															</div>
														{/if}
														{#if q.inserted_id}
															<div class="text-gray-400">
																_id: <span class="text-[#f9e2af]">ObjectId("{q.inserted_id}")</span>
															</div>
														{/if}
													</div>
												</div>
											{/if}
										</div>
									{/each}
								</div>
							{/if}

							<!-- ── RESULT PANELS ── -->
							{#if step.step === 'analyze_patterns' && step.detail}
								<div class="mt-3 rounded-xl border border-purple-200/60 bg-gradient-to-br from-purple-50/50 to-white p-3.5">
									<div class="text-[9px] text-purple-500 uppercase tracking-widest font-bold mb-1.5">LLM Analysis Output</div>
									<p class="text-[11px] text-gray-600 leading-relaxed line-clamp-5">{step.detail}</p>
								</div>
							{/if}

							{#if step.step === 'vector_search_customers' && result.similar_customers.length > 0}
								<div class="mt-3 rounded-xl border border-cyan-200/60 bg-gradient-to-br from-cyan-50/50 to-white p-3.5">
									<div class="text-[9px] text-cyan-600 uppercase tracking-widest font-bold mb-2">Similar Customers ({result.similar_customers.length})</div>
									<div class="grid grid-cols-2 gap-1.5">
										{#each result.similar_customers as sc}
											<div class="flex items-center justify-between text-[10px] px-2.5 py-1.5 rounded-lg bg-white border border-cyan-100">
												<span class="text-gray-700 font-medium truncate">{sc.name || sc.customer_id}</span>
												<span class="font-mono text-cyan-600 tabular-nums shrink-0 ml-2">{sc.score.toFixed(4)}</span>
											</div>
										{/each}
									</div>
								</div>
							{/if}

							{#if step.step === 'vector_search_campaigns' && result.matched_campaigns.length > 0}
								<div class="mt-3 rounded-xl border border-emerald-200/60 bg-gradient-to-br from-emerald-50/50 to-white p-3.5">
									<div class="text-[9px] text-emerald-600 uppercase tracking-widest font-bold mb-2">Matched Campaigns ({result.matched_campaigns.length})</div>
									{#each result.matched_campaigns.slice(0, 5) as camp, ci}
										<div class="flex items-center gap-2.5 text-[10px] py-1 {ci > 0 ? 'border-t border-emerald-100/60' : ''}">
											<span class="w-5 h-5 rounded-md text-white flex items-center justify-center text-[9px] font-black shrink-0" style="background: linear-gradient(135deg, #10b981, #34d399)">{ci + 1}</span>
											<span class="text-gray-700 font-semibold truncate flex-1">{camp.name}</span>
											<div class="w-14 h-1.5 bg-emerald-100 rounded-full overflow-hidden shrink-0">
												<div class="h-full bg-emerald-500 rounded-full" style="width: {Math.min(camp.rerank_score * 200, 100)}%"></div>
											</div>
											<span class="font-mono text-emerald-700 tabular-nums font-bold w-10 text-right shrink-0">{camp.rerank_score.toFixed(3)}</span>
										</div>
									{/each}
								</div>
							{/if}

							{#if step.step === 'vector_search_content' && result.matched_content.length > 0}
								<div class="mt-3 rounded-xl border border-teal-200/60 bg-gradient-to-br from-teal-50/50 to-white p-3.5">
									<div class="text-[9px] text-teal-600 uppercase tracking-widest font-bold mb-2">Matched Content ({result.matched_content.length})</div>
									{#each result.matched_content.slice(0, 4) as cnt, ci}
										<div class="flex items-center gap-2 text-[10px] py-1 {ci > 0 ? 'border-t border-teal-100/60' : ''}">
											<span class="w-5 h-5 rounded-md text-white flex items-center justify-center text-[9px] font-black shrink-0" style="background: linear-gradient(135deg, #14b8a6, #2dd4bf)">{ci + 1}</span>
											<span class="text-gray-700 font-medium truncate flex-1">{cnt.headline}</span>
											<span class="text-[9px] px-2 py-[2px] rounded-md bg-teal-50 text-teal-700 border border-teal-200 shrink-0">{cnt.channel.replace(/_/g, ' ')}</span>
										</div>
									{/each}
								</div>
							{/if}

							{#if step.step === 'determine_channel' && result.recommended_channel}
								<div class="mt-3 flex items-center gap-3 rounded-xl border border-indigo-200/60 bg-gradient-to-br from-indigo-50/50 to-white p-3.5">
									<span class="text-[9px] text-indigo-500 uppercase tracking-widest font-bold">Selected Channel</span>
									<span class="text-xs font-bold text-white px-3 py-1 rounded-lg shadow-sm" style="background: linear-gradient(135deg, #6366f1, #818cf8)">{result.recommended_channel.replace(/_/g, ' ')}</span>
								</div>
							{/if}

							{#if step.step === 'rerank_results' && result.matched_campaigns.length > 0}
								<div class="mt-3 rounded-xl border border-orange-200/60 bg-gradient-to-br from-orange-50/50 to-white p-3.5">
									<div class="text-[9px] text-orange-600 uppercase tracking-widest font-bold mb-2">Reranked Top 3</div>
									{#each result.matched_campaigns.slice(0, 3) as camp, ci}
										<div class="flex items-center gap-2.5 text-[10px] py-1 {ci > 0 ? 'border-t border-orange-100/60' : ''}">
											<span class="w-5 h-5 rounded-md text-white flex items-center justify-center text-[9px] font-black shrink-0" style="background: linear-gradient(135deg, #f97316, #fb923c)">{ci + 1}</span>
											<span class="text-gray-700 font-semibold truncate flex-1">{camp.name}</span>
											<div class="w-14 h-1.5 bg-orange-100 rounded-full overflow-hidden shrink-0">
												<div class="h-full bg-orange-500 rounded-full" style="width: {Math.min(camp.rerank_score * 200, 100)}%"></div>
											</div>
											<span class="font-mono text-orange-700 tabular-nums font-bold w-10 text-right shrink-0">{camp.rerank_score.toFixed(3)}</span>
										</div>
									{/each}
								</div>
							{/if}

							{#if step.step === 'generate_recommendations' && result.structured_recommendation}
								{@const sr = result.structured_recommendation}
								<div class="mt-3 rounded-xl border border-rose-200/60 bg-gradient-to-br from-rose-50/50 to-white p-3.5">
									<div class="text-[9px] text-rose-500 uppercase tracking-widest font-bold mb-2.5">Structured JSON Output</div>
									<div class="grid grid-cols-2 gap-x-6 gap-y-2 text-[11px]">
										<div><span class="text-gray-400 text-[10px]">Campaign</span><p class="text-gray-800 font-semibold">{sr.primary_campaign_name}</p></div>
										<div><span class="text-gray-400 text-[10px]">Content</span><p class="text-gray-800 font-semibold">{sr.content_headline ?? 'N/A'}</p></div>
										<div><span class="text-gray-400 text-[10px]">Channel</span><p class="text-gray-800 font-semibold">{sr.recommended_channel?.replace(/_/g, ' ')}</p></div>
										<div><span class="text-gray-400 text-[10px]">Conversion Prob.</span><p class="text-gray-800 font-semibold">{((sr.conversion_probability ?? 0) * 100).toFixed(0)}%</p></div>
									</div>
									{#if sr.risk_factors && sr.risk_factors.length > 0}
										<div class="mt-2.5 flex flex-wrap gap-1.5">
											<span class="text-[9px] text-gray-400 uppercase tracking-wider">Risks</span>
											{#each sr.risk_factors as risk}
												<span class="text-[9px] px-2 py-[2px] rounded-md bg-red-50 text-red-600 border border-red-200">{risk}</span>
											{/each}
										</div>
									{/if}
								</div>
							{/if}
						</div>
					</div>
				{/each}

				<!-- ── FINAL ENROLLMENT ── -->
				{#if enrollment.enrolled}
					<div class="flex pl-5 h-5">
						<div class="w-px bg-gradient-to-b from-gray-300 to-emerald-400"></div>
					</div>
					<div class="flex gap-5">
						<div class="shrink-0">
							<div class="w-[42px] h-[42px] rounded-[14px] flex items-center justify-center shadow-md"
								 style="background: linear-gradient(135deg, #16a34a, #4PartsDistributor80);">
								<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
							</div>
						</div>
						<div class="flex-1 p-5 rounded-xl border-2 border-emerald-200 bg-gradient-to-br from-emerald-50/70 to-white shadow-sm shadow-emerald-100/50">
							<h3 class="text-sm font-bold text-emerald-900 mb-3">Customer Enrolled Successfully</h3>
							<div class="grid grid-cols-3 gap-x-5 gap-y-3 text-[11px]">
								<div>
									<span class="text-[9px] text-gray-400 uppercase tracking-widest block mb-0.5">Campaign</span>
									<p class="text-gray-900 font-bold">{enrollment.campaign_name}</p>
								</div>
								<div>
									<span class="text-[9px] text-gray-400 uppercase tracking-widest block mb-0.5">Channel</span>
									<p class="text-gray-900 font-bold">{String(enrollment.channel || '').replace(/_/g, ' ')}</p>
								</div>
								<div>
									<span class="text-[9px] text-gray-400 uppercase tracking-widest block mb-0.5">Conv. Rate</span>
									<p class="text-gray-900 font-bold">{((Number(enrollment.similar_conversion_rate) || 0) * 100).toFixed(0)}%</p>
								</div>
								<div>
									<span class="text-[9px] text-gray-400 uppercase tracking-widest block mb-0.5">Enrollment ID</span>
									<p class="text-gray-600 font-mono text-[10px]">{enrollment.enrollment_id}</p>
								</div>
								<div>
									<span class="text-[9px] text-gray-400 uppercase tracking-widest block mb-0.5">Action ID</span>
									<p class="text-gray-600 font-mono text-[10px]">{enrollment.action_id}</p>
								</div>
								<div>
									<span class="text-[9px] text-gray-400 uppercase tracking-widest block mb-0.5">Content Asset</span>
									<p class="text-gray-600 text-[10px] truncate">{enrollment.content_headline || 'N/A'}</p>
								</div>
							</div>
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- ── FOOTER ── -->
		<div class="shrink-0 px-7 py-3 border-t border-gray-200 bg-white flex items-center justify-between">
			<div class="flex items-center gap-5 text-[10px] text-gray-400 font-medium">
				<span class="flex items-center gap-1.5">🍃 <span class="text-gray-600 font-bold">{mongoOps}</span> MongoDB</span>
				<span class="flex items-center gap-1.5">✨ <span class="text-gray-600 font-bold">{llmCalls}</span> LLM</span>
				<span class="flex items-center gap-1.5">🧬 <span class="text-gray-600 font-bold">{embedCalls}</span> Embed</span>
				<span class="flex items-center gap-1.5">🏅 <span class="text-gray-600 font-bold">{rerankCalls}</span> Rerank</span>
			</div>
			<button onclick={onclose} class="px-5 py-2 bg-[#003b73] text-white rounded-xl text-xs hover:bg-[#004e99] cursor-pointer font-semibold transition-all shadow-sm shadow-[#003b73]/20 active:scale-[0.98]">
				Done
			</button>
		</div>
	</div>
</div>

<style>
	.agent-modal {
		background: white;
		box-shadow:
			0 0 0 1px rgba(0,0,0,0.05),
			0 4px 6px -1px rgba(0,0,0,0.1),
			0 20px 40px -4px rgba(0,0,0,0.2),
			0 0 80px -10px rgba(0,59,115,0.15);
	}
</style>
