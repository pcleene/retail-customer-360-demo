<script lang="ts">
	import { searchCustomers, generateRecommendation, type SearchFilters, type SearchResult, type RecommendationResult } from '$lib/api';
	import AgentFlowPopup from '$lib/components/AgentFlowPopup.svelte';

	let query = $state('');
	let results = $state<SearchResult | null>(null);
	let loading = $state(false);
	let selectedIds = $state<Set<string>>(new Set());
	let bulkLoading = $state(false);
	let agentResult = $state<RecommendationResult | null>(null);
	let agentCustomerName = $state('');

	// ── Scoring criteria (drawer → compound.must, boosts score) ──
	let selSegments = $state<Set<string>>(new Set());
	let selTiers = $state<Set<string>>(new Set());
	let selEntities = $state<Set<string>>(new Set());
	let selStates = $state<Set<string>>(new Set());
	let selGenders = $state<Set<string>>(new Set());
	let selEthnicities = $state<Set<string>>(new Set());
	let scoreMin = $state<number | null>(null);
	let scoreMax = $state<number | null>(null);
	let churnMin = $state<number | null>(null);
	let churnMax = $state<number | null>(null);
	let ltvMin = $state<number | null>(null);
	let ltvMax = $state<number | null>(null);

	// ── Facet hard filters (sidebar clicks → compound.filter, hard exclusion) ──
	let facetSegments = $state<Set<string>>(new Set());
	let facetTiers = $state<Set<string>>(new Set());
	let facetEntities = $state<Set<string>>(new Set());
	let facetStates = $state<Set<string>>(new Set());
	let facetGenders = $state<Set<string>>(new Set());
	let facetEthnicities = $state<Set<string>>(new Set());

	// ── UI state ──
	let drawerOpen = $state(false);

	const ALL_SEGMENTS = ['retail_only', 'credit_only', 'bank_only', 'retail_credit', 'retail_bank', 'credit_bank', 'tri_entity'];
	const ALL_TIERS = ['Basic', 'Silver', 'Gold', 'Platinum'];
	const ALL_ENTITIES = ['RetailGroup Co', 'RetailGroup Credit', 'RetailGroup Bank'];
	const ALL_GENDERS = ['male', 'female'];
	const ALL_ETHNICITIES = ['malay', 'chinese', 'indian', 'indigenous'];

	const suggestions = [
		'High-value platinum customers in Kuala Lumpur',
		'Tri-entity members with high churn risk',
		'Gold tier retail customers spending on electronics',
		'Credit card holders with expiring loyalty points',
		'Young professionals in Selangor with bank accounts',
		'Chinese female customers with high cross-sell score',
		'Malay families in Johor with credit products',
	];

	function toggle(set: Set<string>, value: string): Set<string> {
		const next = new Set(set);
		if (next.has(value)) next.delete(value);
		else next.add(value);
		return next;
	}

	const scoringCriteriaCount = $derived(
		selSegments.size + selTiers.size + selEntities.size + selStates.size +
		selGenders.size + selEthnicities.size +
		(scoreMin != null ? 1 : 0) + (scoreMax != null ? 1 : 0) +
		(churnMin != null ? 1 : 0) + (churnMax != null ? 1 : 0) +
		(ltvMin != null ? 1 : 0) + (ltvMax != null ? 1 : 0)
	);

	const facetFilterCount = $derived(
		facetSegments.size + facetTiers.size + facetEntities.size + facetStates.size +
		facetGenders.size + facetEthnicities.size
	);

	async function search(opts?: { cursor?: string; page?: number }) {
		loading = true;
		try {
			const filters: SearchFilters = {
				query: query || undefined,
				segments: [...selSegments],
				tiers: [...selTiers],
				entities: [...selEntities],
				states: [...selStates],
				genders: [...selGenders],
				ethnicities: [...selEthnicities],
				cross_sell_score_min: scoreMin,
				cross_sell_score_max: scoreMax,
				churn_risk_min: churnMin,
				churn_risk_max: churnMax,
				ltv_min: ltvMin,
				ltv_max: ltvMax,
				facet_segments: [...facetSegments],
				facet_tiers: [...facetTiers],
				facet_entities: [...facetEntities],
				facet_states: [...facetStates],
				facet_genders: [...facetGenders],
				facet_ethnicities: [...facetEthnicities],
				page_size: 30,
				cursor: opts?.cursor || undefined,
				page: opts?.page || undefined,
			};
			const newResults = await searchCustomers(filters);
			if (opts?.cursor || opts?.page) {
				// Append to existing results for "Load More"
				newResults.customers = [...(results?.customers || []), ...newResults.customers];
				newResults.total = newResults.customers.length;
				// Keep facets from the first page
				if (results?.facets) newResults.facets = results.facets;
			}
			results = newResults;
		} catch (e) {
			console.error('Search failed', e);
		} finally {
			loading = false;
		}
	}

	function submitSuggestion(text: string) {
		query = text;
		search();
	}

	function applyAndSearch() {
		drawerOpen = false;
		search();
	}

	function clearScoringCriteria() {
		selSegments = new Set();
		selTiers = new Set();
		selEntities = new Set();
		selStates = new Set();
		selGenders = new Set();
		selEthnicities = new Set();
		scoreMin = scoreMax = churnMin = churnMax = ltvMin = ltvMax = null;
	}

	function clearFacetFilters() {
		facetSegments = new Set();
		facetTiers = new Set();
		facetEntities = new Set();
		facetStates = new Set();
		facetGenders = new Set();
		facetEthnicities = new Set();
		search();
	}

	function toggleFacet(category: string, value: string) {
		if (category === 'tiers') facetTiers = toggle(facetTiers, value);
		else if (category === 'segments') facetSegments = toggle(facetSegments, value);
		else if (category === 'states') facetStates = toggle(facetStates, value);
		else if (category === 'entities') facetEntities = toggle(facetEntities, value);
		else if (category === 'genders') facetGenders = toggle(facetGenders, value);
		else if (category === 'ethnicities') facetEthnicities = toggle(facetEthnicities, value);
		search();
	}

	function toggleSelect(id: string) {
		const next = new Set(selectedIds);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		selectedIds = next;
	}

	function toggleSelectAll() {
		if (!results?.customers) return;
		const allIds = results.customers.map(c => c.customer_id);
		const allSelected = allIds.every(id => selectedIds.has(id));
		if (allSelected) {
			selectedIds = new Set();
		} else {
			selectedIds = new Set(allIds);
		}
	}

	const allSelected = $derived(
		(results?.customers?.length ?? 0) > 0 &&
		results!.customers.every(c => selectedIds.has(c.customer_id))
	);

	let bulkProgress = $state(0);
	let bulkTotal = $state(0);

	async function bulkRecommend() {
		bulkLoading = true;
		const ids = [...selectedIds];
		bulkTotal = ids.length;
		bulkProgress = 0;
		let lastResult: RecommendationResult | null = null;
		let lastId = '';
		try {
			for (const id of ids) {
				lastId = id;
				bulkProgress++;
				try {
					lastResult = await generateRecommendation(id);
				} catch (err) {
					console.error(`Recommendation failed for ${id}`, err);
				}
			}
			if (lastResult) {
				const cust = results?.customers.find(c => c.customer_id === lastId);
				agentCustomerName = cust?.unified_profile?.name || lastId;
				agentResult = lastResult;
			}
			selectedIds = new Set();
		} finally {
			bulkLoading = false;
			bulkProgress = 0;
			bulkTotal = 0;
		}
	}

	const tierBadge: Record<string, string> = {
		Basic: 'bg-gray-100 text-gray-600',
		Silver: 'bg-slate-100 text-slate-700',
		Gold: 'bg-amber-50 text-amber-700',
		Platinum: 'bg-violet-50 text-violet-700',
	};

	const searchMethodLabel: Record<string, string> = {
		rankFusion: '$rankFusion',
		vectorSearch: '$vectorSearch',
		textSearch: 'Atlas Search',
		structured: 'Atlas Search',
	};
	const searchMethodColor: Record<string, string> = {
		rankFusion: 'bg-purple-100 text-purple-700 border-purple-200',
		vectorSearch: 'bg-blue-100 text-blue-700 border-blue-200',
		textSearch: 'bg-sky-100 text-sky-700 border-sky-200',
		structured: 'bg-gray-100 text-gray-600 border-gray-200',
	};

	const entityColor: Record<string, string> = {
		'RetailGroup Co': 'border-blue-300 bg-blue-50 text-blue-700',
		'RetailGroup Credit': 'border-emerald-300 bg-emerald-50 text-emerald-700',
		'RetailGroup Bank': 'border-violet-300 bg-violet-50 text-violet-700',
	};

	const segmentLabel = (s: string) => s.replace(/_/g, ' ');
	const genderLabel = (g: string) => g.charAt(0).toUpperCase() + g.slice(1);
	const ethnicityLabel = (e: string) => e.charAt(0).toUpperCase() + e.slice(1);
</script>

<div class="p-6 space-y-5">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h2 class="text-2xl font-bold text-gray-800">Client / Segment Search</h2>
			<p class="text-xs text-gray-400 mt-0.5">Scoring criteria boost relevance. Facet sidebar narrows results.</p>
		</div>
		{#if results?.search_method}
			<span class={`text-xs px-3 py-1 rounded-full font-medium border ${searchMethodColor[results.search_method] || 'bg-gray-100 text-gray-700 border-gray-200'}`}>
				{searchMethodLabel[results.search_method] || results.search_method}
			</span>
		{/if}
	</div>

	<!-- ━━━ Search Bar + Criteria Button ━━━ -->
	<div class="relative">
		<div class="flex gap-2">
			<div class="flex-1 relative">
				<svg class="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
				<input
					bind:value={query}
					placeholder="Search by name, city, tier, category, credit product, or natural language..."
					class="w-full pl-10 pr-10 py-2.5 border border-gray-200 rounded-xl bg-gray-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#003b73]/20 focus:border-[#003b73] transition-all"
					onkeydown={(e) => { if (e.key === 'Enter') search(); }}
				/>
				{#if query}
					<button onclick={() => { query = ''; results = null; }} class="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 cursor-pointer" aria-label="Clear">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
					</button>
				{/if}
			</div>
			<button
				onclick={() => drawerOpen = !drawerOpen}
				class="px-4 py-2.5 border rounded-xl flex items-center gap-2 transition-all cursor-pointer
					{drawerOpen ? 'border-[#003b73] bg-[#003b73]/5 text-[#003b73]' : 'border-gray-200 text-gray-500 hover:border-gray-300 hover:text-gray-700'}"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
				<span class="text-sm font-medium">Criteria</span>
				{#if scoringCriteriaCount > 0}
					<span class="text-[10px] px-1.5 py-0.5 rounded-full bg-[#003b73] text-white font-bold min-w-[18px] text-center">{scoringCriteriaCount}</span>
				{/if}
			</button>
			<button onclick={() => search()} disabled={loading} class="px-6 py-2.5 bg-[#003b73] text-white rounded-xl hover:bg-[#004e99] transition-colors cursor-pointer font-medium disabled:opacity-50">
				{loading ? 'Searching...' : 'Search'}
			</button>
		</div>

		<!-- ━━━ Criteria Drawer ━━━ -->
		{#if drawerOpen}
			<div class="absolute left-0 right-0 top-full mt-2 z-30 bg-white border border-gray-200 rounded-2xl shadow-xl p-5 animate-in">
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-sm font-bold text-gray-700">Segmentation Criteria</h3>
					<div class="flex items-center gap-3">
						{#if scoringCriteriaCount > 0}
							<button onclick={clearScoringCriteria} class="text-xs text-gray-400 hover:text-red-500 cursor-pointer transition-colors">Clear all</button>
						{/if}
						<button onclick={() => drawerOpen = false} class="text-gray-400 hover:text-gray-600 cursor-pointer">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
						</button>
					</div>
				</div>
				<p class="text-[10px] text-gray-400 -mt-2 mb-4">These criteria <strong>boost matching customers' scores</strong> — non-matching docs can still appear if they match the NL query.</p>

				<div class="grid grid-cols-6 gap-5">
					<!-- Tier -->
					<div>
						<div class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Tier</div>
						<div class="space-y-1">
							{#each ALL_TIERS as t}
								<label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer hover:bg-gray-50 rounded px-1.5 py-1 -mx-1.5 transition-colors">
									<input type="checkbox" checked={selTiers.has(t)} onchange={() => selTiers = toggle(selTiers, t)} class="rounded border-gray-300 text-[#003b73] focus:ring-[#003b73]/30" />
									{t}
								</label>
							{/each}
						</div>
					</div>

					<!-- Segment -->
					<div>
						<div class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Segment</div>
						<div class="space-y-1 max-h-48 overflow-y-auto">
							{#each ALL_SEGMENTS as s}
								<label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer hover:bg-gray-50 rounded px-1.5 py-1 -mx-1.5 transition-colors">
									<input type="checkbox" checked={selSegments.has(s)} onchange={() => selSegments = toggle(selSegments, s)} class="rounded border-gray-300 text-[#003b73] focus:ring-[#003b73]/30" />
									{segmentLabel(s)}
								</label>
							{/each}
						</div>
					</div>

					<!-- Entity -->
					<div>
						<div class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Entity</div>
						<div class="space-y-1">
							{#each ALL_ENTITIES as e}
								<label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer hover:bg-gray-50 rounded px-1.5 py-1 -mx-1.5 transition-colors">
									<input type="checkbox" checked={selEntities.has(e)} onchange={() => selEntities = toggle(selEntities, e)} class="rounded border-gray-300 text-[#003b73] focus:ring-[#003b73]/30" />
									{e}
								</label>
							{/each}
						</div>
					</div>

					<!-- Gender -->
					<div>
						<div class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Gender</div>
						<div class="space-y-1">
							{#each ALL_GENDERS as g}
								<label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer hover:bg-gray-50 rounded px-1.5 py-1 -mx-1.5 transition-colors">
									<input type="checkbox" checked={selGenders.has(g)} onchange={() => selGenders = toggle(selGenders, g)} class="rounded border-gray-300 text-[#003b73] focus:ring-[#003b73]/30" />
									{genderLabel(g)}
								</label>
							{/each}
						</div>
					</div>

					<!-- Ethnicity -->
					<div>
						<div class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Ethnicity</div>
						<div class="space-y-1">
							{#each ALL_ETHNICITIES as e}
								<label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer hover:bg-gray-50 rounded px-1.5 py-1 -mx-1.5 transition-colors">
									<input type="checkbox" checked={selEthnicities.has(e)} onchange={() => selEthnicities = toggle(selEthnicities, e)} class="rounded border-gray-300 text-[#003b73] focus:ring-[#003b73]/30" />
									{ethnicityLabel(e)}
								</label>
							{/each}
						</div>
					</div>

					<!-- State -->
					<div>
						<div class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">State</div>
						<div class="space-y-1 max-h-48 overflow-y-auto">
							{#each Object.entries(results?.facets?.states || {}).sort((a, b) => b[1] - a[1]) as [st]}
								<label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer hover:bg-gray-50 rounded px-1.5 py-1 -mx-1.5 transition-colors">
									<input type="checkbox" checked={selStates.has(st)} onchange={() => selStates = toggle(selStates, st)} class="rounded border-gray-300 text-[#003b73] focus:ring-[#003b73]/30" />
									{st}
								</label>
							{/each}
							{#if !results?.facets?.states || Object.keys(results.facets.states).length === 0}
								<p class="text-[10px] text-gray-400 italic">Run a search first to see states</p>
							{/if}
						</div>
					</div>
				</div>

				<!-- Score Ranges -->
				<div class="mt-5 pt-4 border-t border-gray-100">
					<div class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-3">Score Ranges <span class="normal-case font-normal text-gray-400">(gradient scoring via Atlas Search <code>near</code> + hard cutoffs)</span></div>
					<div class="grid grid-cols-3 gap-5">
						<div>
							<span class="text-xs text-gray-600 block mb-1.5">Cross-sell Score</span>
							<div class="flex gap-1.5 items-center">
								<input bind:value={scoreMin} type="number" step="0.1" min="0" max="1" placeholder="Min" class="w-20 text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#003b73]/30 bg-gray-50/50" />
								<span class="text-gray-300 text-xs">to</span>
								<input bind:value={scoreMax} type="number" step="0.1" min="0" max="1" placeholder="Max" class="w-20 text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#003b73]/30 bg-gray-50/50" />
							</div>
						</div>
						<div>
							<span class="text-xs text-gray-600 block mb-1.5">Churn Risk</span>
							<div class="flex gap-1.5 items-center">
								<input bind:value={churnMin} type="number" step="0.1" min="0" max="1" placeholder="Min" class="w-20 text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#003b73]/30 bg-gray-50/50" />
								<span class="text-gray-300 text-xs">to</span>
								<input bind:value={churnMax} type="number" step="0.1" min="0" max="1" placeholder="Max" class="w-20 text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#003b73]/30 bg-gray-50/50" />
							</div>
						</div>
						<div>
							<span class="text-xs text-gray-600 block mb-1.5">LTV (RM)</span>
							<div class="flex gap-1.5 items-center">
								<input bind:value={ltvMin} type="number" step="1000" min="0" placeholder="Min" class="w-20 text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#003b73]/30 bg-gray-50/50" />
								<span class="text-gray-300 text-xs">to</span>
								<input bind:value={ltvMax} type="number" step="1000" min="0" placeholder="Max" class="w-20 text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#003b73]/30 bg-gray-50/50" />
							</div>
						</div>
					</div>
				</div>

				<!-- Apply button -->
				<div class="mt-5 flex justify-end">
					<button onclick={applyAndSearch} class="px-6 py-2 bg-[#003b73] text-white rounded-xl hover:bg-[#004e99] transition-colors cursor-pointer font-medium text-sm">
						Apply & Search
					</button>
				</div>
			</div>
		{/if}
	</div>

	<!-- Suggestion Chips -->
	{#if !results}
		<div class="flex flex-wrap gap-2">
			{#each suggestions as sug}
				<button
					onclick={() => submitSuggestion(sug)}
					class="text-xs px-3.5 py-1.5 rounded-full border border-gray-200 text-gray-500 hover:border-[#003b73] hover:text-[#003b73] hover:bg-blue-50/50 transition-all cursor-pointer"
				>{sug}</button>
			{/each}
		</div>
	{/if}

	<!-- Active scoring criteria pills -->
	{#if scoringCriteriaCount > 0 && results}
		<div class="flex flex-wrap gap-1.5 items-center">
			<span class="text-[10px] text-gray-400 uppercase tracking-wider mr-1">Scoring:</span>
			{#each [...selTiers] as t}
				<span class="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1">
					{t}
					<button onclick={() => { selTiers = toggle(selTiers, t); search(); }} class="hover:text-red-500 cursor-pointer">&times;</button>
				</span>
			{/each}
			{#each [...selEntities] as e}
				<span class="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1">
					{e}
					<button onclick={() => { selEntities = toggle(selEntities, e); search(); }} class="hover:text-red-500 cursor-pointer">&times;</button>
				</span>
			{/each}
			{#each [...selSegments] as s}
				<span class="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 border border-gray-200 flex items-center gap-1">
					{segmentLabel(s)}
					<button onclick={() => { selSegments = toggle(selSegments, s); search(); }} class="hover:text-red-500 cursor-pointer">&times;</button>
				</span>
			{/each}
			{#each [...selGenders] as g}
				<span class="text-[10px] px-2 py-0.5 rounded-full bg-pink-50 text-pink-700 border border-pink-200 flex items-center gap-1">
					{genderLabel(g)}
					<button onclick={() => { selGenders = toggle(selGenders, g); search(); }} class="hover:text-red-500 cursor-pointer">&times;</button>
				</span>
			{/each}
			{#each [...selEthnicities] as e}
				<span class="text-[10px] px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 border border-teal-200 flex items-center gap-1">
					{ethnicityLabel(e)}
					<button onclick={() => { selEthnicities = toggle(selEthnicities, e); search(); }} class="hover:text-red-500 cursor-pointer">&times;</button>
				</span>
			{/each}
			{#each [...selStates] as st}
				<span class="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 border border-gray-200 flex items-center gap-1">
					{st}
					<button onclick={() => { selStates = toggle(selStates, st); search(); }} class="hover:text-red-500 cursor-pointer">&times;</button>
				</span>
			{/each}
			{#if scoreMin != null || scoreMax != null}
				<span class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">XS: {scoreMin ?? '0'}-{scoreMax ?? '1'}</span>
			{/if}
			{#if churnMin != null || churnMax != null}
				<span class="text-[10px] px-2 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-200">Churn: {churnMin ?? '0'}-{churnMax ?? '1'}</span>
			{/if}
			{#if ltvMin != null || ltvMax != null}
				<span class="text-[10px] px-2 py-0.5 rounded-full bg-green-50 text-green-700 border border-green-200">LTV: {ltvMin ? `RM ${ltvMin.toLocaleString()}` : '0'}-{ltvMax ? `RM ${ltvMax.toLocaleString()}` : ''}</span>
			{/if}
		</div>
	{/if}

	<div class="flex gap-6">
		<!-- ━━━ Facet Sidebar ━━━ -->
		{#if results}
			<aside class="w-56 shrink-0">
				<div class="sticky top-6 space-y-5">
					<!-- Facet: Tier -->
					{#if results.facets?.tiers && Object.keys(results.facets.tiers).length > 0}
						<div>
							<div class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Tier</div>
							{#each Object.entries(results.facets.tiers).sort((a, b) => b[1] - a[1]) as [value, count]}
								<button
									class="flex justify-between w-full text-sm py-1.5 rounded-lg px-2.5 transition-all cursor-pointer
										{facetTiers.has(value) ? 'bg-[#003b73]/5 text-[#003b73] font-semibold' : 'text-gray-700 hover:bg-gray-50'}"
									onclick={() => toggleFacet('tiers', value)}
								>
									<span>{value}</span>
									<span class="text-xs text-gray-400 tabular-nums">{count.toLocaleString()}</span>
								</button>
							{/each}
						</div>
					{/if}

					<!-- Facet: Segment -->
					{#if results.facets?.segments && Object.keys(results.facets.segments).length > 0}
						<div>
							<div class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Segment</div>
							{#each Object.entries(results.facets.segments).sort((a, b) => b[1] - a[1]) as [value, count]}
								<button
									class="flex justify-between w-full text-sm py-1.5 rounded-lg px-2.5 transition-all cursor-pointer
										{facetSegments.has(value) ? 'bg-[#003b73]/5 text-[#003b73] font-semibold' : 'text-gray-700 hover:bg-gray-50'}"
									onclick={() => toggleFacet('segments', value)}
								>
									<span>{segmentLabel(value)}</span>
									<span class="text-xs text-gray-400 tabular-nums">{count.toLocaleString()}</span>
								</button>
							{/each}
						</div>
					{/if}

					<!-- Facet: Entity -->
					{#if results.facets?.entities && Object.keys(results.facets.entities).length > 0}
						<div>
							<div class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Entity</div>
							{#each Object.entries(results.facets.entities).sort((a, b) => b[1] - a[1]) as [value, count]}
								<button
									class="flex justify-between w-full text-sm py-1.5 rounded-lg px-2.5 transition-all cursor-pointer
										{facetEntities.has(value) ? 'bg-[#003b73]/5 text-[#003b73] font-semibold' : 'text-gray-700 hover:bg-gray-50'}"
									onclick={() => toggleFacet('entities', value)}
								>
									<span>{value}</span>
									<span class="text-xs text-gray-400 tabular-nums">{count.toLocaleString()}</span>
								</button>
							{/each}
						</div>
					{/if}

					<!-- Facet: Gender -->
					{#if results.facets?.genders && Object.keys(results.facets.genders).length > 0}
						<div>
							<div class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Gender</div>
							{#each Object.entries(results.facets.genders).sort((a, b) => b[1] - a[1]) as [value, count]}
								<button
									class="flex justify-between w-full text-sm py-1.5 rounded-lg px-2.5 transition-all cursor-pointer
										{facetGenders.has(value) ? 'bg-[#003b73]/5 text-[#003b73] font-semibold' : 'text-gray-700 hover:bg-gray-50'}"
									onclick={() => toggleFacet('genders', value)}
								>
									<span>{genderLabel(value)}</span>
									<span class="text-xs text-gray-400 tabular-nums">{count.toLocaleString()}</span>
								</button>
							{/each}
						</div>
					{/if}

					<!-- Facet: Ethnicity -->
					{#if results.facets?.ethnicities && Object.keys(results.facets.ethnicities).length > 0}
						<div>
							<div class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Ethnicity</div>
							{#each Object.entries(results.facets.ethnicities).sort((a, b) => b[1] - a[1]) as [value, count]}
								<button
									class="flex justify-between w-full text-sm py-1.5 rounded-lg px-2.5 transition-all cursor-pointer
										{facetEthnicities.has(value) ? 'bg-[#003b73]/5 text-[#003b73] font-semibold' : 'text-gray-700 hover:bg-gray-50'}"
									onclick={() => toggleFacet('ethnicities', value)}
								>
									<span>{ethnicityLabel(value)}</span>
									<span class="text-xs text-gray-400 tabular-nums">{count.toLocaleString()}</span>
								</button>
							{/each}
						</div>
					{/if}

					<!-- Facet: State -->
					{#if results.facets?.states && Object.keys(results.facets.states).length > 0}
						<div>
							<div class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">State</div>
							<div class="max-h-52 overflow-y-auto">
								{#each Object.entries(results.facets.states).sort((a, b) => b[1] - a[1]) as [value, count]}
									<button
										class="flex justify-between w-full text-sm py-1.5 rounded-lg px-2.5 transition-all cursor-pointer
											{facetStates.has(value) ? 'bg-[#003b73]/5 text-[#003b73] font-semibold' : 'text-gray-700 hover:bg-gray-50'}"
										onclick={() => toggleFacet('states', value)}
									>
										<span>{value}</span>
										<span class="text-xs text-gray-400 tabular-nums">{count.toLocaleString()}</span>
									</button>
								{/each}
							</div>
						</div>
					{/if}

					{#if facetFilterCount > 0}
						<button onclick={clearFacetFilters} class="text-xs text-[#003b73] hover:underline cursor-pointer">
							Clear facet filters
						</button>
					{/if}

					<!-- Search method -->
					<div class="text-[10px] text-gray-400 pt-2 border-t border-gray-100">
						Search via: <span class="font-mono">{results.search_method}</span>
					</div>
				</div>
			</aside>
		{/if}

		<!-- ━━━ Results ━━━ -->
		<div class="flex-1 min-w-0">
			{#if selectedIds.size > 0}
				<div class="mb-3 flex items-center gap-3 p-3 bg-blue-50 rounded-xl text-sm border border-blue-100">
					<span class="font-medium text-[#003b73]">{selectedIds.size} selected</span>
					<button
						onclick={bulkRecommend}
						disabled={bulkLoading}
						class="px-4 py-1.5 bg-[#003b73] text-white rounded-lg text-xs hover:bg-[#004e99] cursor-pointer disabled:opacity-50 transition-colors font-medium"
					>
						{bulkLoading ? `Processing ${bulkProgress}/${bulkTotal}...` : 'Generate Recommendations'}
					</button>
					<button onclick={() => selectedIds = new Set()} class="text-xs text-gray-500 hover:text-gray-700 cursor-pointer ml-auto">Clear</button>
				</div>
			{/if}

			<!-- Facet filter pills -->
			{#if facetFilterCount > 0}
				<div class="flex flex-wrap gap-1.5 mb-3 items-center">
					<span class="text-[10px] text-gray-400 uppercase tracking-wider mr-1">Filtering:</span>
					{#each [...facetTiers] as t}
						<span class="text-[10px] px-2 py-0.5 rounded-full bg-[#003b73]/10 text-[#003b73] border border-[#003b73]/20 flex items-center gap-1 font-medium">
							{t}
							<button onclick={() => toggleFacet('tiers', t)} class="hover:text-red-500 cursor-pointer">&times;</button>
						</span>
					{/each}
					{#each [...facetSegments] as s}
						<span class="text-[10px] px-2 py-0.5 rounded-full bg-[#003b73]/10 text-[#003b73] border border-[#003b73]/20 flex items-center gap-1 font-medium">
							{segmentLabel(s)}
							<button onclick={() => toggleFacet('segments', s)} class="hover:text-red-500 cursor-pointer">&times;</button>
						</span>
					{/each}
					{#each [...facetEntities] as e}
						<span class="text-[10px] px-2 py-0.5 rounded-full bg-[#003b73]/10 text-[#003b73] border border-[#003b73]/20 flex items-center gap-1 font-medium">
							{e}
							<button onclick={() => toggleFacet('entities', e)} class="hover:text-red-500 cursor-pointer">&times;</button>
						</span>
					{/each}
					{#each [...facetGenders] as g}
						<span class="text-[10px] px-2 py-0.5 rounded-full bg-pink-100 text-pink-700 border border-pink-200 flex items-center gap-1 font-medium">
							{genderLabel(g)}
							<button onclick={() => toggleFacet('genders', g)} class="hover:text-red-500 cursor-pointer">&times;</button>
						</span>
					{/each}
					{#each [...facetEthnicities] as e}
						<span class="text-[10px] px-2 py-0.5 rounded-full bg-teal-100 text-teal-700 border border-teal-200 flex items-center gap-1 font-medium">
							{ethnicityLabel(e)}
							<button onclick={() => toggleFacet('ethnicities', e)} class="hover:text-red-500 cursor-pointer">&times;</button>
						</span>
					{/each}
					{#each [...facetStates] as st}
						<span class="text-[10px] px-2 py-0.5 rounded-full bg-[#003b73]/10 text-[#003b73] border border-[#003b73]/20 flex items-center gap-1 font-medium">
							{st}
							<button onclick={() => toggleFacet('states', st)} class="hover:text-red-500 cursor-pointer">&times;</button>
						</span>
					{/each}
				</div>
			{/if}

			{#if loading}
				<div class="py-16 text-center">
					<div class="animate-pulse flex flex-col items-center gap-3">
						<div class="w-10 h-10 rounded-full bg-gray-200"></div>
						<div class="h-3 w-40 bg-gray-200 rounded"></div>
						<div class="h-2 w-24 bg-gray-100 rounded"></div>
					</div>
				</div>
			{:else if results}
				<div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
					<table class="w-full text-sm">
						<thead>
							<tr class="text-left text-[10px] text-gray-400 border-b border-gray-100 bg-gray-50/80 uppercase tracking-wider">
								<th class="py-2.5 pl-3 w-8">
									<input
										type="checkbox"
										checked={allSelected}
										onchange={toggleSelectAll}
										class="rounded border-gray-300 text-[#003b73] focus:ring-[#003b73]/30 cursor-pointer"
										title="Select all"
									/>
								</th>
								<th class="py-2.5 font-medium">Name</th>
								<th class="py-2.5 font-medium">Tier</th>
								<th class="py-2.5 font-medium">Segment</th>
								<th class="py-2.5 font-medium">Location</th>
								<th class="py-2.5 font-medium">Entities</th>
								<th class="py-2.5 text-right font-medium">LTV</th>
								<th class="py-2.5 text-right font-medium">XS</th>
								<th class="py-2.5 text-right font-medium">Churn</th>
								<th class="py-2.5 text-right pr-3 font-medium">Score</th>
							</tr>
						</thead>
						<tbody>
							{#each results.customers as c}
								{@const ltv = c.cross_entity_metrics?.total_ltv || 0}
								{@const xs = c.cross_entity_metrics?.cross_sell_score || 0}
								{@const churn = c.cross_entity_metrics?.churn_risk || 0}
								<tr class="border-b border-gray-50 hover:bg-gray-50/50 transition-colors group">
									<td class="py-2.5 pl-3">
										<input
											type="checkbox"
											checked={selectedIds.has(c.customer_id)}
											onchange={() => toggleSelect(c.customer_id)}
											class="rounded border-gray-300 opacity-40 group-hover:opacity-100 transition-opacity"
										/>
									</td>
									<td class="py-2.5">
										<a href="/customer/{c.customer_id}" class="text-[#003b73] hover:underline font-medium text-sm">{c.unified_profile?.name || c.customer_id}</a>
										<div class="flex items-center gap-1.5 mt-0.5">
											<span class="text-[10px] text-gray-400 font-mono">{c.customer_id}</span>
											{#if c.unified_profile?.ethnicity}
												<span class="text-[9px] px-1.5 py-0 rounded bg-gray-50 text-gray-400 border border-gray-100">{c.unified_profile.ethnicity}</span>
											{/if}
											{#if c.unified_profile?.gender}
												<span class="text-[9px] px-1.5 py-0 rounded bg-gray-50 text-gray-400 border border-gray-100">{c.unified_profile.gender}</span>
											{/if}
										</div>
									</td>
									<td class="py-2.5">
										<span class={`text-[10px] px-2 py-0.5 rounded-full font-medium ${tierBadge[c.tier] || 'bg-gray-100 text-gray-600'}`}>{c.tier}</span>
									</td>
									<td class="py-2.5 text-gray-500 text-xs">{segmentLabel(c.segment || '')}</td>
									<td class="py-2.5 text-xs">
										<span class="text-gray-700">{c.unified_profile?.address?.city || ''}</span>
										{#if c.unified_profile?.address?.state}
											<span class="text-gray-400 block text-[10px]">{c.unified_profile.address.state}</span>
										{/if}
									</td>
									<td class="py-2.5">
										<div class="flex flex-wrap gap-0.5">
											{#each (c.entities || []) as ent}
												<span class={`text-[9px] px-1.5 py-0 rounded border ${entityColor[ent] || 'bg-gray-50 text-gray-500 border-gray-200'}`}>{ent.replace('RetailGroup ', '')}</span>
											{/each}
										</div>
									</td>
									<td class="py-2.5 text-right font-medium tabular-nums">RM {ltv.toLocaleString(undefined, {maximumFractionDigits: 0})}</td>
									<td class="py-2.5 text-right font-mono text-xs tabular-nums text-gray-500">{xs.toFixed(2)}</td>
									<td class="py-2.5 text-right font-mono text-xs tabular-nums" class:text-red-600={churn > 0.5} class:text-gray-500={churn <= 0.5}>{churn.toFixed(2)}</td>
									<td class="py-2.5 text-right pr-3">
										{#if c.rank_fusion_score != null}
											<span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-100">{(c.rank_fusion_score * 1000).toFixed(1)}</span>
										{:else if c.score != null}
											<span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-50 text-sky-700 border border-sky-100">{c.score.toFixed(2)}</span>
										{:else}
											<span class="text-[10px] text-gray-300">--</span>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>

				<!-- Pagination -->
			{#if results.pagination.hasMore}
				<div class="mt-4 text-center">
					<button
						onclick={() => {
							const p = results?.pagination;
							if (!p) return;
							if (p.nextCursor) search({ cursor: p.nextCursor });
							else if (p.nextPage) search({ page: p.nextPage });
						}}
						class="px-6 py-2 text-sm rounded-xl border border-gray-200 text-gray-600 hover:border-[#003b73] hover:text-[#003b73] hover:bg-blue-50/50 transition-all cursor-pointer"
					>
						Load more results
					</button>
				</div>
				{/if}
			{:else}
				<div class="py-20 text-center">
					<div class="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-[#003b73]/10 to-[#c8a951]/10 flex items-center justify-center mb-4">
						<svg class="w-8 h-8 text-[#003b73]/60" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
					</div>
					<p class="text-gray-700 font-semibold">Search 50K customers</p>
					<p class="text-sm text-gray-400 mt-1 max-w-md mx-auto">Search by name, city, tier, shopping category, credit product, or natural language. Scoring criteria <em>boost</em> relevance. Facet sidebar <em>narrows</em> results.</p>
				</div>
			{/if}
		</div>
	</div>
</div>

{#if agentResult}
	<AgentFlowPopup
		result={agentResult}
		customerName={agentCustomerName}
		onclose={() => agentResult = null}
	/>
{/if}

<style>
	.animate-in {
		animation: slideDown 0.2s ease-out;
	}
	@keyframes slideDown {
		from { opacity: 0; transform: translateY(-8px); }
		to { opacity: 1; transform: translateY(0); }
	}
</style>
