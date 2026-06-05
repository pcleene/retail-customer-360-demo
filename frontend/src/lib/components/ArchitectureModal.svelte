<script lang="ts">
	let open = $state(false);
	let activeLayer = $state<string | null>(null);
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && (open = false)} />

<!-- Floating trigger -->
<button
	onclick={() => (open = true)}
	class="fixed bottom-6 right-6 z-40 w-12 h-12 rounded-full shadow-lg hover:shadow-xl
		transition-all flex items-center justify-center cursor-pointer group"
	style="background: linear-gradient(135deg, #003b73 0%, #0a5298 100%); border: 1px solid rgba(255,255,255,0.15);"
	title="Retail Customer 360 Architecture"
>
	<svg class="w-5 h-5 text-white/80 group-hover:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
		<path stroke-linecap="round" stroke-linejoin="round" d="M2.25 7.125C2.25 6.504 2.754 6 3.375 6h6c.621 0 1.125.504 1.125 1.125v3.75c0 .621-.504 1.125-1.125 1.125h-6a1.125 1.125 0 0 1-1.125-1.125v-3.75ZM14.25 8.625c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v8.25c0 .621-.504 1.125-1.125 1.125h-5.25a1.125 1.125 0 0 1-1.125-1.125v-8.25ZM3.75 16.125c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v2.25c0 .621-.504 1.125-1.125 1.125h-5.25a1.125 1.125 0 0 1-1.125-1.125v-2.25Z" />
	</svg>
</button>

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center p-4"
		style="background: rgba(0,0,0,0.7); backdrop-filter: blur(8px);"
		onclick={() => (open = false)}
		onkeydown={(e) => e.key === 'Escape' && (open = false)}
	>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="w-full max-w-6xl max-h-[92vh] overflow-auto rounded-2xl shadow-2xl"
			style="background: linear-gradient(160deg, #0c1222 0%, #111827 40%, #0f172a 100%); border: 1px solid rgba(255,255,255,0.06);"
			onclick={(e) => e.stopPropagation()}
			onkeydown={() => {}}
			role="dialog"
			tabindex="-1"
		>
			<!-- Header -->
			<div class="relative px-8 pt-8 pb-6">
				<div class="absolute inset-0 opacity-30" style="background: radial-gradient(ellipse at 30% 0%, rgba(0,59,115,0.4) 0%, transparent 60%), radial-gradient(ellipse at 70% 0%, rgba(200,169,81,0.15) 0%, transparent 50%);"></div>
				<div class="relative flex items-center justify-between">
					<div class="flex items-center gap-4">
						<div class="w-12 h-12 rounded-xl flex items-center justify-center" style="background: linear-gradient(135deg, #003b73 0%, #0a5298 100%); box-shadow: 0 0 20px rgba(0,59,115,0.4);">
							<span class="text-[#c8a951] font-black text-lg">A</span>
						</div>
						<div>
							<h2 class="text-xl font-bold text-white tracking-wide">Retail Customer 360 Architecture</h2>
							<p class="text-xs text-gray-500 mt-0.5">Customer Intelligence Platform — Full Technical Stack</p>
						</div>
					</div>
					<button
						onclick={() => (open = false)}
						class="w-9 h-9 rounded-lg flex items-center justify-center text-gray-500 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
						aria-label="Close architecture modal"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
					</button>
				</div>
			</div>

			<div class="px-8 pb-8 space-y-3">

				<!-- === LAYER 1: FRONTEND === -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="rounded-xl p-5 transition-all duration-300 cursor-pointer"
					style="background: linear-gradient(135deg, rgba(200,169,81,0.06) 0%, rgba(200,169,81,0.02) 100%); border: 1px solid rgba(200,169,81,{activeLayer === 'frontend' ? '0.3' : '0.1'});"
					onmouseenter={() => (activeLayer = 'frontend')}
					onmouseleave={() => (activeLayer = null)}
				>
					<div class="flex items-center gap-3 mb-4">
						<div class="w-7 h-7 rounded-lg flex items-center justify-center" style="background: rgba(200,169,81,0.15);">
							<svg class="w-3.5 h-3.5 text-[#c8a951]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0V12a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 12V5.25" /></svg>
						</div>
						<span class="text-xs font-semibold text-[#c8a951] uppercase tracking-wider">Frontend Layer</span>
						<div class="flex-1 h-px" style="background: linear-gradient(90deg, rgba(200,169,81,0.2) 0%, transparent 100%);"></div>
					</div>
					<div class="grid grid-cols-5 gap-3">
						{#each [
							{ name: 'Dashboard', desc: 'KPIs + Charts + SSE', icon: '◈' },
							{ name: 'Client Search', desc: '$rankFusion hybrid', icon: '⌕' },
							{ name: 'Campaigns', desc: 'Smart CRM enrollment', icon: '▤' },
							{ name: 'Co-pilot', desc: 'MCP agent chat', icon: '◉' },
							{ name: 'Insights', desc: 'RBAC analytics', icon: '◎' },
						] as item}
							<div class="rounded-lg px-3 py-2.5 text-center" style="background: rgba(200,169,81,0.05); border: 1px solid rgba(200,169,81,0.08);">
								<div class="text-lg mb-0.5">{item.icon}</div>
								<div class="text-[11px] font-medium text-gray-300">{item.name}</div>
								<div class="text-[9px] text-gray-600 mt-0.5">{item.desc}</div>
							</div>
						{/each}
					</div>
					<div class="flex items-center gap-4 mt-3">
						{#each ['SvelteKit 5', 'Svelte 5 Runes', 'Tailwind CSS v4', 'Chart.js', 'TypeScript', 'SSE Streaming'] as tech}
							<span class="text-[9px] px-2 py-0.5 rounded-full text-[#c8a951]/70" style="background: rgba(200,169,81,0.06); border: 1px solid rgba(200,169,81,0.1);">{tech}</span>
						{/each}
					</div>
				</div>

				<!-- Flow connector -->
				<div class="flex justify-center">
					<div class="flex flex-col items-center gap-0.5">
						<div class="w-px h-4" style="background: linear-gradient(180deg, rgba(200,169,81,0.3) 0%, rgba(96,165,250,0.3) 100%);"></div>
						<svg class="w-3 h-3 text-blue-400/40" fill="currentColor" viewBox="0 0 24 24"><path d="M12 16l-6-6h12z"/></svg>
					</div>
				</div>

				<!-- === LAYER 2: BACKEND + AI === -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="rounded-xl p-5 transition-all duration-300 cursor-pointer"
					style="background: linear-gradient(135deg, rgba(59,130,246,0.06) 0%, rgba(139,92,246,0.04) 100%); border: 1px solid rgba(96,165,250,{activeLayer === 'backend' ? '0.3' : '0.1'});"
					onmouseenter={() => (activeLayer = 'backend')}
					onmouseleave={() => (activeLayer = null)}
				>
					<!-- Backend header -->
					<div class="flex items-center gap-3 mb-4">
						<div class="w-7 h-7 rounded-lg flex items-center justify-center" style="background: rgba(59,130,246,0.15);">
							<svg class="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 0 1-3-3m3 3a3 3 0 1 0 0 6h13.5a3 3 0 1 0 0-6m-16.5-3a3 3 0 0 1 3-3h13.5a3 3 0 0 1 3 3m-19.5 0a4.5 4.5 0 0 1 .9-2.7L5.737 5.1a3.375 3.375 0 0 1 2.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 0 1 .9 2.7m0 0a3 3 0 0 1-3 3m0 3h.008v.008h-.008v-.008Zm0-6h.008v.008h-.008v-.008Zm-3 6h.008v.008h-.008v-.008Zm0-6h.008v.008h-.008v-.008Z" /></svg>
						</div>
						<span class="text-xs font-semibold text-blue-400 uppercase tracking-wider">Backend + AI Agents</span>
						<span class="text-[9px] px-2 py-0.5 rounded-full text-blue-300/60" style="background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.15);">FastAPI · port 8000</span>
						<div class="flex-1 h-px" style="background: linear-gradient(90deg, rgba(59,130,246,0.2) 0%, transparent 100%);"></div>
					</div>

					<!-- 3 Agent cards -->
					<div class="grid grid-cols-3 gap-3 mb-4">
						<!-- Agent 1: Co-pilot -->
						<div class="rounded-lg p-3.5" style="background: linear-gradient(135deg, rgba(139,92,246,0.08) 0%, rgba(139,92,246,0.03) 100%); border: 1px solid rgba(139,92,246,0.12);">
							<div class="flex items-center gap-2 mb-2.5">
								<div class="w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold" style="background: rgba(139,92,246,0.2); color: #a78bfa;">1</div>
								<span class="text-[11px] font-semibold text-purple-300">MCP Co-pilot</span>
							</div>
							<div class="space-y-1.5 text-[10px] text-gray-500">
								<div class="flex items-center gap-1.5">
									<div class="w-1 h-1 rounded-full bg-purple-500/50"></div>
									<span>mongodb-mcp-server</span>
								</div>
								<div class="flex items-center gap-1.5">
									<div class="w-1 h-1 rounded-full bg-purple-500/50"></div>
									<span>React Agent (Gemini)</span>
								</div>
								<div class="flex items-center gap-1.5">
									<div class="w-1 h-1 rounded-full bg-purple-500/50"></div>
									<span>MongoDBSaver checkpoints</span>
								</div>
								<div class="flex items-center gap-1.5">
									<div class="w-1 h-1 rounded-full bg-purple-500/50"></div>
									<span>MongoDBStore memory</span>
								</div>
							</div>
						</div>

						<!-- Agent 2: Cross-sell -->
						<div class="rounded-lg p-3.5" style="background: linear-gradient(135deg, rgba(59,130,246,0.08) 0%, rgba(59,130,246,0.03) 100%); border: 1px solid rgba(59,130,246,0.12);">
							<div class="flex items-center gap-2 mb-2.5">
								<div class="w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold" style="background: rgba(59,130,246,0.2); color: #60a5fa;">2</div>
								<span class="text-[11px] font-semibold text-blue-300">Cross-sell Agent</span>
							</div>
							<div class="text-[10px] text-gray-500 mb-2">12-node LangGraph</div>
							<div class="flex flex-wrap gap-1">
								{#each ['classify', 'fetch', 'analyze', 'vector×3', 'similar', 'channel', 'rerank', 'generate', 'execute'] as node}
									<span class="text-[8px] px-1.5 py-0.5 rounded" style="background: rgba(59,130,246,0.1); color: #93c5fd; border: 1px solid rgba(59,130,246,0.1);">{node}</span>
								{/each}
							</div>
						</div>

						<!-- Agent 3: Insights -->
						<div class="rounded-lg p-3.5" style="background: linear-gradient(135deg, rgba(16,185,129,0.08) 0%, rgba(16,185,129,0.03) 100%); border: 1px solid rgba(16,185,129,0.12);">
							<div class="flex items-center gap-2 mb-2.5">
								<div class="w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold" style="background: rgba(16,185,129,0.2); color: #34d399;">3</div>
								<span class="text-[11px] font-semibold text-emerald-300">Product Insights</span>
							</div>
							<div class="text-[10px] text-gray-500 mb-2">9-node LangGraph + RBAC</div>
							<div class="flex flex-wrap gap-1">
								{#each ['rbac', 'classify', 'build_agg', 'run_agg', 'realtime', 'vector', 'rerank', 'insights', 'format'] as node}
									<span class="text-[8px] px-1.5 py-0.5 rounded" style="background: rgba(16,185,129,0.1); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.1);">{node}</span>
								{/each}
							</div>
						</div>
					</div>

					<!-- AI/ML + Streaming row -->
					<div class="grid grid-cols-3 gap-3">
						<div class="rounded-lg px-3.5 py-3" style="background: rgba(251,191,36,0.04); border: 1px solid rgba(251,191,36,0.1);">
							<div class="text-[10px] font-semibold text-amber-300/80 mb-1.5">Voyage AI</div>
							<div class="space-y-1 text-[9px] text-gray-500">
								<div>voyage-3-large <span class="text-amber-400/50">1024d</span></div>
								<div>voyage-3-lite <span class="text-amber-400/50">512d</span></div>
								<div>rerank-2 <span class="text-amber-400/50">relevance</span></div>
							</div>
						</div>
						<div class="rounded-lg px-3.5 py-3" style="background: rgba(96,165,250,0.04); border: 1px solid rgba(96,165,250,0.1);">
							<div class="text-[10px] font-semibold text-blue-300/80 mb-1.5">Gemini 2.5 Flash</div>
							<div class="space-y-1 text-[9px] text-gray-500">
								<div>Vertex AI platform</div>
								<div>Agent reasoning LLM</div>
								<div>Pattern analysis</div>
							</div>
						</div>
						<div class="rounded-lg px-3.5 py-3" style="background: rgba(244,114,182,0.04); border: 1px solid rgba(244,114,182,0.1);">
							<div class="text-[10px] font-semibold text-pink-300/80 mb-1.5">Kafka + ASP</div>
							<div class="space-y-1 text-[9px] text-gray-500">
								<div>event_ingest.js</div>
								<div>cross_sell_trigger.js</div>
								<div>loyalty_aggregator.js</div>
								<div>realtime_kpis.js</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Flow connector -->
				<div class="flex justify-center">
					<div class="flex flex-col items-center gap-0.5">
						<div class="w-px h-4" style="background: linear-gradient(180deg, rgba(96,165,250,0.3) 0%, rgba(0,168,74,0.3) 100%);"></div>
						<svg class="w-3 h-3 text-emerald-400/40" fill="currentColor" viewBox="0 0 24 24"><path d="M12 16l-6-6h12z"/></svg>
					</div>
				</div>

				<!-- === LAYER 3: MONGODB ATLAS === -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="rounded-xl p-5 transition-all duration-300 cursor-pointer"
					style="background: linear-gradient(135deg, rgba(0,168,74,0.06) 0%, rgba(0,168,74,0.02) 100%); border: 1px solid rgba(0,168,74,{activeLayer === 'data' ? '0.3' : '0.1'});"
					onmouseenter={() => (activeLayer = 'data')}
					onmouseleave={() => (activeLayer = null)}
				>
					<div class="flex items-center gap-3 mb-4">
						<div class="w-7 h-7 rounded-lg flex items-center justify-center" style="background: rgba(0,168,74,0.15);">
							<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none">
								<path d="M12.514 2.156c-.372-.618-.98-.618-1.352 0L8.16 7.36c-.248.413-.248 1.084 0 1.497l3.003 5.002c.372.618.98.618 1.352 0l3.003-5.002c.248-.413.248-1.084 0-1.497l-3.003-5.205Z" fill="#00a84a" opacity="0.8"/>
								<path d="M12 14.5v7.5M12 14.5c-1 0-5-2-5-6s4-7.5 5-8.5c1 1 5 4.5 5 8.5s-4 6-5 6Z" stroke="#00a84a" stroke-width="1.2" fill="none"/>
							</svg>
						</div>
						<span class="text-xs font-semibold uppercase tracking-wider" style="color: #00a84a;">MongoDB Atlas</span>
						<span class="text-[9px] px-2 py-0.5 rounded-full" style="background: rgba(0,168,74,0.1); border: 1px solid rgba(0,168,74,0.15); color: rgba(0,168,74,0.6);">Single Database — Zero Sync</span>
						<div class="flex-1 h-px" style="background: linear-gradient(90deg, rgba(0,168,74,0.2) 0%, transparent 100%);"></div>
					</div>

					<div class="grid grid-cols-2 gap-4">
						<!-- Collections -->
						<div>
							<div class="text-[10px] font-medium text-gray-400 mb-2 uppercase tracking-wider">Collections</div>
							<div class="space-y-1.5">
								{#each [
									{ name: 'customers', meta: '50K docs · 10K embeddings' },
									{ name: 'products', meta: '430K docs · 10K embeddings' },
									{ name: 'transactions', meta: '2M docs' },
									{ name: 'campaigns', meta: '30 docs · all embedded' },
									{ name: 'content_assets', meta: '~120 docs' },
									{ name: 'stores', meta: '50 docs · GeoJSON' },
									{ name: 'cross_sell_signals', meta: 'streaming' },
									{ name: 'realtime_kpis', meta: 'ASP output' },
									{ name: 'agent_memories', meta: 'LangGraph store' },
								] as col}
									<div class="flex items-center justify-between py-1 px-2 rounded" style="background: rgba(0,168,74,0.03);">
										<span class="text-[10px] font-mono" style="color: #4PartsDistributor80;">{col.name}</span>
										<span class="text-[9px] text-gray-600">{col.meta}</span>
									</div>
								{/each}
							</div>
						</div>

						<!-- Search Features -->
						<div>
							<div class="text-[10px] font-medium text-gray-400 mb-2 uppercase tracking-wider">Search & Processing Features</div>
							<div class="space-y-2">
								{#each [
									{ name: '$rankFusion', desc: 'Hybrid search (text + vector)', color: '#c084fc' },
									{ name: '$vectorSearch', desc: 'Semantic search (1024d Voyage AI)', color: '#60a5fa' },
									{ name: 'Atlas Search', desc: 'Full-text with facets', color: '#34d399' },
									{ name: 'Aggregation Pipelines', desc: '$group, $addFields, $ifNull', color: '#fb923c' },
									{ name: 'Change Streams', desc: 'Real-time events → SSE', color: '#f472b6' },
									{ name: 'Atlas Stream Processing', desc: '$tumblingWindow aggregations', color: '#a78bfa' },
									{ name: 'MongoDBSaver / Store', desc: 'Agent checkpoints + memory', color: '#2dd4bf' },
									{ name: '2dsphere Index', desc: 'Geospatial queries', color: '#fbbf24' },
								] as feat}
									<div class="flex items-start gap-2">
										<div class="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style="background: {feat.color};"></div>
										<div>
											<span class="text-[10px] font-semibold" style="color: {feat.color};">{feat.name}</span>
											<span class="text-[9px] text-gray-600 ml-1">{feat.desc}</span>
										</div>
									</div>
								{/each}
							</div>
						</div>
					</div>
				</div>

				<!-- === REPLACES SECTION === -->
				<div class="rounded-xl p-5" style="background: linear-gradient(135deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0.01) 100%); border: 1px solid rgba(255,255,255,0.05);">
					<div class="text-center mb-5">
						<span class="text-xs font-semibold text-gray-400 uppercase tracking-widest">One Platform, Zero Sync</span>
					</div>
					<div class="grid grid-cols-2 gap-6">
						<!-- Old stack -->
						<div class="text-center">
							<div class="text-[10px] font-medium text-red-400/60 uppercase tracking-wider mb-3">Traditional Stack</div>
							<div class="space-y-1.5">
								{#each [
									'AlloyDB — relational queries',
									'PGVector — vector search',
									'Elasticsearch — full-text search',
									'Redis — session & memory store',
									'Kafka Connect — data sync',
									'Separate ETL pipelines',
								] as item}
									<div class="flex items-center gap-2 justify-center">
										<svg class="w-3 h-3 text-red-500/40 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12"/></svg>
										<span class="text-[10px] text-gray-600 line-through">{item}</span>
									</div>
								{/each}
							</div>
						</div>
						<!-- Divider -->

						<!-- New stack -->
						<div class="text-center">
							<div class="text-[10px] font-medium uppercase tracking-wider mb-3" style="color: #00a84a;">Retail Customer 360 Stack</div>
							<div class="space-y-1.5">
								{#each [
									'$rankFusion — hybrid search',
									'$vectorSearch — semantic 1024d',
									'Atlas Search — full-text + facets',
									'MongoDBSaver/Store — agent memory',
									'Change Streams — real-time events',
									'ASP — stream processing (no ETL)',
								] as item}
									<div class="flex items-center gap-2 justify-center">
										<svg class="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" style="color: #00a84a;"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5"/></svg>
										<span class="text-[10px] font-medium" style="color: rgba(0,168,74,0.8);">{item}</span>
									</div>
								{/each}
							</div>
						</div>
					</div>
				</div>

				<!-- === 8 DEMO NARRATIVES === -->
				<div class="rounded-xl p-5" style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);">
					<div class="flex items-center gap-3 mb-4">
						<span class="text-xs font-semibold text-gray-400 uppercase tracking-wider">8 Demo Narratives</span>
						<div class="flex-1 h-px" style="background: rgba(255,255,255,0.06);"></div>
					</div>
					<div class="grid grid-cols-4 gap-2">
						{#each [
							{ n: 1, title: 'MCP Co-pilot', desc: 'Zero custom code, MCP tools', color: '#a78bfa' },
							{ n: 2, title: 'Real-time', desc: 'Kafka → ASP → signal → agent', color: '#f472b6' },
							{ n: 3, title: 'CRM Profile', desc: '12-node reasoning pipeline', color: '#60a5fa' },
							{ n: 4, title: '$rankFusion', desc: 'Hybrid search with score', color: '#c084fc' },
							{ n: 5, title: 'Smart Campaigns', desc: 'Auto-enrollment + why', color: '#34d399' },
							{ n: 6, title: 'One Platform', desc: 'Full pipeline in MongoDB', color: '#2dd4bf' },
							{ n: 7, title: 'RBAC', desc: 'Supplier sees only their data', color: '#fb923c' },
							{ n: 8, title: 'Voyage 4', desc: 'Embeddings + reranking', color: '#fbbf24' },
						] as item}
							<div class="rounded-lg px-3 py-2.5 flex items-start gap-2.5" style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);">
								<div
									class="w-5 h-5 rounded shrink-0 flex items-center justify-center text-[9px] font-bold"
									style="background: {item.color}20; color: {item.color}; border: 1px solid {item.color}30;"
								>{item.n}</div>
								<div>
									<div class="text-[10px] font-semibold" style="color: {item.color};">{item.title}</div>
									<div class="text-[9px] text-gray-600 mt-0.5">{item.desc}</div>
								</div>
							</div>
						{/each}
					</div>
				</div>

			</div>
		</div>
	</div>
{/if}

<style>
	@keyframes arch-glow {
		0%, 100% { opacity: 0.4; }
		50% { opacity: 0.8; }
	}
</style>
