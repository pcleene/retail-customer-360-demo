<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import {
		getCustomer,
		getCustomerTransactions,
		generateRecommendation,
		type Customer,
		type Transaction,
		type RecommendationResult,
	} from '$lib/api';
	import LineChart from '$lib/components/charts/LineChart.svelte';
	import RadarChart from '$lib/components/charts/RadarChart.svelte';
	import DoughnutChart from '$lib/components/charts/DoughnutChart.svelte';
	import Sparkline from '$lib/components/charts/Sparkline.svelte';

	let customer = $state<Customer | null>(null);
	let transactions = $state<Transaction[]>([]);
	let loading = $state(true);
	let recommending = $state(false);
	let recommendation = $state<RecommendationResult | null>(null);
	let showReason = $state<string | null>(null);
	let activeTab = $state<'overview' | 'entities' | 'interactions' | 'campaigns'>('overview');

	const customerId = $derived(page.params.id!);

	onMount(async () => {
		try {
			const [c, t] = await Promise.all([
				getCustomer(customerId),
				getCustomerTransactions(customerId),
			]);
			customer = c;
			transactions = t;
		} catch (e) {
			console.error(e);
		} finally {
			loading = false;
		}
	});

	async function runAgent() {
		recommending = true;
		try {
			recommendation = await generateRecommendation(customerId);
			customer = await getCustomer(customerId);
		} finally {
			recommending = false;
		}
	}

	const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
	function monthLabel(ym: string) {
		const m = parseInt(ym.slice(5), 10);
		return MONTHS[m - 1] ?? ym.slice(5);
	}

	const tierColors: Record<string, string> = {
		Basic: 'bg-gray-100 text-gray-600 border-gray-200',
		Silver: 'bg-slate-100 text-slate-700 border-slate-200',
		Gold: 'bg-amber-50 text-amber-700 border-amber-200',
		Platinum: 'bg-violet-50 text-violet-700 border-violet-200',
	};

	const entityIcons: Record<string, string> = {
		'RetailGroup Co': 'M3 3h18v18H3V3zm2 2v14h14V5H5z',
		'RetailGroup Credit': 'M3 10h18v8a2 2 0 01-2 2H5a2 2 0 01-2-2v-8zm0-4a2 2 0 012-2h14a2 2 0 012 2v2H3V6z',
		'RetailGroup Bank': 'M12 2L2 7v2h20V7L12 2zM4 11v7h3v-7H4zm5 0v7h3v-7H9zm5 0v7h3v-7h-3zm5 0v7h3v-7h-3zM2 20v2h20v-2H2z',
	};

	const entityBg: Record<string, string> = {
		'RetailGroup Co': 'from-blue-500 to-blue-600',
		'RetailGroup Credit': 'from-emerald-500 to-emerald-600',
		'RetailGroup Bank': 'from-violet-500 to-violet-600',
	};

	const spendTrendLabels = $derived(
		customer?.cross_entity_metrics.monthly_spend_trend?.map(t => monthLabel(t.month)) ?? []
	);
	const spendTrendData = $derived(
		customer?.cross_entity_metrics.monthly_spend_trend?.map(t => Math.round(t.value)) ?? []
	);
	const ltvTrendLabels = $derived(
		customer?.cross_entity_metrics.ltv_trend?.map(t => monthLabel(t.month)) ?? []
	);
	const ltvTrendData = $derived(
		customer?.cross_entity_metrics.ltv_trend?.map(t => Math.round(t.value)) ?? []
	);

	const channelLabels = $derived(
		Object.keys(customer?.interaction_history.channel_engagement_rates ?? {}).map(c => c.replace(/_/g, ' '))
	);
	const channelOpenRates = $derived(
		Object.values(customer?.interaction_history.channel_engagement_rates ?? {}).map(c => Math.round(c.open_rate * 100))
	);
	const channelCtr = $derived(
		Object.values(customer?.interaction_history.channel_engagement_rates ?? {}).map(c => Math.round(c.ctr * 100))
	);
	const channelConversion = $derived(
		Object.values(customer?.interaction_history.channel_engagement_rates ?? {}).map(c => Math.round(c.conversion_rate * 100))
	);

	const categoryBreakdown = $derived(() => {
		const counts: Record<string, number> = {};
		for (const tx of transactions) {
			for (const item of tx.items) {
				counts[item.category] = (counts[item.category] || 0) + item.line_total;
			}
		}
		const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 6);
		return {
			labels: sorted.map(([k]) => k.replace(/_/g, ' ')),
			data: sorted.map(([, v]) => Math.round(v)),
			colors: ['#003b73', '#c8a951', '#0ea5e9', '#8b5cf6', '#ec4899', '#f97316'],
		};
	});

	function pct(val: number) { return Math.round(val * 100); }
	function formatRM(val: number, decimals = 0) {
		return `RM ${val.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
	}
	function formatCurrency(val: number) {
		return val >= 1000 ? `RM ${(val / 1000).toFixed(1)}k` : `RM ${Math.round(val)}`;
	}
	function riskColor(val: number) {
		if (val >= 0.7) return 'text-red-600';
		if (val >= 0.4) return 'text-amber-600';
		return 'text-emerald-600';
	}
	function riskBg(val: number) {
		if (val >= 0.7) return '#dc2626';
		if (val >= 0.4) return '#d97706';
		return '#16a34a';
	}
	function scoreColor(val: number) {
		if (val >= 0.7) return 'text-emerald-600';
		if (val >= 0.4) return 'text-[#003b73]';
		return 'text-gray-500';
	}
	function langLabel(code: string) {
		const map: Record<string, string> = { en: 'English', ms: 'Bahasa Melayu', zh: 'Chinese', ta: 'Tamil' };
		return map[code] || code;
	}
	function age(dob: string) {
		if (!dob) return '';
		const born = new Date(dob);
		const now = new Date();
		let y = now.getFullYear() - born.getFullYear();
		if (now.getMonth() < born.getMonth() || (now.getMonth() === born.getMonth() && now.getDate() < born.getDate())) y--;
		return `${y}`;
	}
	function fdate(s: string | undefined | null) {
		if (!s) return '—';
		return s.slice(0, 10);
	}
	function safe(s: string | undefined | null) { return s ?? ''; }
	function utilPct(outstanding: number, limit: number) { return limit ? (outstanding / limit) * 100 : 0; }
</script>

{#if loading}
	<div class="flex items-center justify-center h-96">
		<div class="animate-pulse flex flex-col items-center gap-3">
			<div class="w-16 h-16 rounded-full bg-gray-200"></div>
			<div class="h-4 w-48 bg-gray-200 rounded"></div>
			<div class="h-3 w-32 bg-gray-100 rounded"></div>
		</div>
	</div>
{:else if customer}
	{@const profile = customer.unified_profile}
	{@const metrics = customer.cross_entity_metrics}

	<!-- ════════ HEADER ════════ -->
	<div class="bg-gradient-to-br from-[#003b73] via-[#004e99] to-[#00376a] px-8 pt-10 pb-16 -mx-6 -mt-6">
		<div class="max-w-7xl mx-auto">
			<div class="flex items-start gap-6">
				<!-- Avatar -->
				<div class="w-16 h-16 rounded-2xl bg-white/15 backdrop-blur-sm flex items-center justify-center text-white text-2xl font-bold shrink-0 ring-2 ring-white/20">
					{profile.name.charAt(0)}
				</div>

				<!-- Info -->
				<div class="flex-1 min-w-0">
					<!-- Row 1: Name + tier -->
					<div class="flex items-center gap-3 mb-2">
						<h1 class="text-2xl font-bold text-white tracking-tight">{profile.name}</h1>
						<span class="text-xs px-3 py-0.5 rounded-full border font-semibold {tierColors[customer.tier]}">{customer.tier}</span>
					</div>

					<!-- Row 2: Key demographics -->
					<div class="flex items-center gap-2 text-blue-200/80 text-sm mb-3">
						<span>{customer.customer_id}</span>
						<span class="text-blue-300/30">|</span>
						<span>{safe(profile.address.city)}, {safe(profile.address.state)}</span>
						{#if profile.address.postcode}
							<span class="text-blue-300/30">|</span>
							<span>{profile.address.postcode}</span>
						{/if}
						{#if profile.date_of_birth}
							<span class="text-blue-300/30">|</span>
							<span>{age(profile.date_of_birth)} years old</span>
						{/if}
					</div>

					<!-- Row 3: Tags -->
					<div class="flex items-center gap-2 flex-wrap">
						{#if profile.gender}
							<span class="text-[11px] px-2.5 py-1 rounded-md bg-white/10 text-blue-100 border border-white/10 capitalize font-medium">{profile.gender}</span>
						{/if}
						{#if profile.ethnicity}
							<span class="text-[11px] px-2.5 py-1 rounded-md bg-white/10 text-blue-100 border border-white/10 capitalize font-medium">{profile.ethnicity}</span>
						{/if}
						<span class="text-[11px] px-2.5 py-1 rounded-md bg-white/10 text-blue-100 border border-white/10 capitalize font-medium">{safe(customer.segment).replace(/_/g, ' ')}</span>
						{#each customer.entities as ent}
							<span class="text-[11px] px-2.5 py-1 rounded-md bg-white/10 text-blue-100 border border-white/10 font-medium">{ent}</span>
						{/each}
						{#if profile.contact?.communication_preferences?.preferred_language}
							<span class="text-[11px] px-2.5 py-1 rounded-md bg-white/8 text-blue-200/60 border border-white/8 font-medium">{langLabel(profile.contact.communication_preferences.preferred_language)}</span>
						{/if}
					</div>
				</div>

				<!-- LTV -->
				<div class="text-right shrink-0 pl-6">
					<div class="text-3xl font-bold text-white tracking-tight">{formatRM(metrics.total_ltv)}</div>
					<p class="text-blue-200/50 text-xs mt-1 font-medium uppercase tracking-wider">Lifetime Value</p>
					{#if ltvTrendData.length > 2}
						<div class="mt-2 flex justify-end"><Sparkline data={ltvTrendData} color="#ffffff" width="100px" height="24px" /></div>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<!-- ════════ KPI CARDS ════════ -->
	<div class="max-w-7xl mx-auto -mt-9 px-8 mb-8">
		<div class="grid grid-cols-4 gap-4">
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
				<p class="text-[11px] text-gray-400 font-medium uppercase tracking-wider">Cross-sell Score</p>
				<p class="text-2xl font-bold mt-2 {scoreColor(metrics.cross_sell_score)}">{pct(metrics.cross_sell_score)}%</p>
				<div class="w-full bg-gray-100 rounded-full h-1.5 mt-3">
					<div class="h-1.5 rounded-full bg-[#003b73] transition-all" style="width: {pct(metrics.cross_sell_score)}%"></div>
				</div>
			</div>
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
				<p class="text-[11px] text-gray-400 font-medium uppercase tracking-wider">Churn Risk</p>
				<p class="text-2xl font-bold mt-2 {riskColor(metrics.churn_risk)}">{pct(metrics.churn_risk)}%</p>
				<div class="w-full bg-gray-100 rounded-full h-1.5 mt-3">
					<div class="h-1.5 rounded-full transition-all" style="width: {pct(metrics.churn_risk)}%; background: {riskBg(metrics.churn_risk)}"></div>
				</div>
			</div>
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
				<p class="text-[11px] text-gray-400 font-medium uppercase tracking-wider">Member Since</p>
				<p class="text-2xl font-bold mt-2 text-gray-800">{fdate(customer.join_date)}</p>
				<p class="text-[11px] text-gray-400 mt-2">Last visit {fdate(customer.last_visit)}</p>
			</div>
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
				<p class="text-[11px] text-gray-400 font-medium uppercase tracking-wider">Active Campaigns</p>
				<p class="text-2xl font-bold mt-2 text-[#003b73]">{customer.active_campaigns.length}</p>
				<p class="text-[11px] text-gray-400 mt-2">{customer.entities.length} entities linked</p>
			</div>
		</div>
	</div>

	<!-- ════════ TABS ════════ -->
	<div class="max-w-7xl mx-auto px-8">
		<nav class="flex gap-1 border-b border-gray-200 mb-8">
			{#each [
				{ id: 'overview' as const, label: 'Overview' },
				{ id: 'entities' as const, label: 'Entity Profiles' },
				{ id: 'interactions' as const, label: 'Interactions' },
				{ id: 'campaigns' as const, label: 'Campaigns & AI' },
			] as tab}
				<button
					onclick={() => activeTab = tab.id}
					class="px-5 pb-3 text-sm font-medium border-b-2 transition-colors cursor-pointer {activeTab === tab.id ? 'border-[#003b73] text-[#003b73]' : 'border-transparent text-gray-400 hover:text-gray-600'}"
				>{tab.label}</button>
			{/each}
		</nav>
	</div>

	<div class="max-w-7xl mx-auto px-8 pb-12 space-y-6">

		<!-- ═══════════════════ OVERVIEW TAB ═══════════════════ -->
		{#if activeTab === 'overview'}

			<!-- Personal Info + Contact Card -->
			<div class="grid grid-cols-3 gap-6">
				<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
					<h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Personal Information</h3>
					<div class="space-y-3">
						<div class="flex justify-between">
							<span class="text-sm text-gray-500">Full Name</span>
							<span class="text-sm font-medium text-gray-800">{profile.name}</span>
						</div>
						{#if profile.date_of_birth}
							<div class="flex justify-between">
								<span class="text-sm text-gray-500">Date of Birth</span>
								<span class="text-sm font-medium text-gray-800">{fdate(profile.date_of_birth)} ({age(profile.date_of_birth)}y)</span>
							</div>
						{/if}
						{#if profile.gender}
							<div class="flex justify-between">
								<span class="text-sm text-gray-500">Gender</span>
								<span class="text-sm font-medium text-gray-800 capitalize">{profile.gender}</span>
							</div>
						{/if}
						{#if profile.ethnicity}
							<div class="flex justify-between">
								<span class="text-sm text-gray-500">Ethnicity</span>
								<span class="text-sm font-medium text-gray-800 capitalize">{profile.ethnicity}</span>
							</div>
						{/if}
						{#if profile.ic_number}
							<div class="flex justify-between">
								<span class="text-sm text-gray-500">IC Number</span>
								<span class="text-sm font-medium text-gray-800 font-mono">{profile.ic_number}</span>
							</div>
						{/if}
						<div class="flex justify-between">
							<span class="text-sm text-gray-500">Location</span>
							<span class="text-sm font-medium text-gray-800">{safe(profile.address.city)}, {safe(profile.address.state)}</span>
						</div>
					</div>
				</div>

				<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
					<h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Contact Details</h3>
					<div class="space-y-3">
						{#if profile.contact?.email}
							<div class="flex items-center gap-3">
								<div class="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
									<svg class="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
								</div>
								<div>
									<p class="text-[11px] text-gray-400">Email</p>
									<p class="text-sm text-gray-700">{profile.contact.email}</p>
								</div>
							</div>
						{/if}
						{#if profile.contact?.phone}
							<div class="flex items-center gap-3">
								<div class="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
									<svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"></path></svg>
								</div>
								<div>
									<p class="text-[11px] text-gray-400">Phone</p>
									<p class="text-sm text-gray-700">{profile.contact.phone}</p>
								</div>
							</div>
						{/if}
						{#if profile.contact?.channel_opt_ins?.length > 0}
							<div class="pt-2">
								<p class="text-[11px] text-gray-400 mb-2">Channel Opt-ins</p>
								<div class="flex flex-wrap gap-1.5">
									{#each profile.contact.channel_opt_ins as opt}
										<span class="text-[11px] px-2 py-0.5 rounded-full {opt.opted_in ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' : 'bg-red-50 text-red-500 border border-red-200'} capitalize">
											{safe(opt.channel).replace(/_/g, ' ')}{opt.opted_in ? '' : ' (out)'}
										</span>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				</div>

				<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
					<h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Communication Preferences</h3>
					{#if profile.contact?.communication_preferences}
						{@const prefs = profile.contact.communication_preferences}
						<div class="space-y-3">
							<div class="flex justify-between">
								<span class="text-sm text-gray-500">Language</span>
								<span class="text-sm font-medium text-gray-800">{langLabel(prefs.preferred_language)}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-sm text-gray-500">Best contact time</span>
								<span class="text-sm font-medium text-gray-800 capitalize">{prefs.preferred_contact_time}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-sm text-gray-500">Quiet hours</span>
								<span class="text-sm font-medium text-gray-800">{prefs.quiet_hours_start} – {prefs.quiet_hours_end}</span>
							</div>
							{#if prefs.do_not_disturb}
								<div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-50 border border-red-200">
									<svg class="w-4 h-4 text-red-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path></svg>
									<span class="text-sm font-medium text-red-600">Do Not Disturb</span>
								</div>
							{/if}
						</div>
					{:else}
						<p class="text-sm text-gray-300">No preferences set</p>
					{/if}
				</div>
			</div>

			<!-- Spend Trend + Category Breakdown -->
			<div class="grid grid-cols-5 gap-6">
				<div class="col-span-3 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
					<h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-5">Monthly Spending Trend</h3>
					{#if spendTrendLabels.length > 0}
						<LineChart labels={spendTrendLabels} datasets={[{ label: 'Monthly Spend (RM)', data: spendTrendData, color: '#003b73' }]} height="200px" />
					{:else}
						<div class="flex items-center justify-center h-[200px] text-sm text-gray-300">No spend data</div>
					{/if}
				</div>
				<div class="col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
					<h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-5">Spending by Category</h3>
					{#if categoryBreakdown().labels.length > 0}
						<DoughnutChart labels={categoryBreakdown().labels} data={categoryBreakdown().data} colors={categoryBreakdown().colors} height="200px" />
					{:else}
						<div class="flex items-center justify-center h-[200px] text-sm text-gray-300">No transactions</div>
					{/if}
				</div>
			</div>

			<!-- Channel Engagement + Brand Journey -->
			<div class="grid grid-cols-2 gap-6">
				<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
					<h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-5">Channel Engagement</h3>
					{#if channelLabels.length > 0}
						<RadarChart labels={channelLabels} datasets={[
							{ label: 'Open Rate %', data: channelOpenRates, color: '#003b73' },
							{ label: 'CTR %', data: channelCtr, color: '#c8a951' },
							{ label: 'Conversion %', data: channelConversion, color: '#0ea5e9' },
						]} height="240px" />
					{:else}
						<div class="flex items-center justify-center h-[240px] text-sm text-gray-300">No channel data</div>
					{/if}
				</div>

				<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
					<h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-5">Brand Journey</h3>
					<div class="relative pl-6 max-h-[260px] overflow-y-auto">
						<div class="absolute left-[9px] top-2 bottom-2 w-px bg-gray-200"></div>
						{#each customer.brand_journey as m}
							{@const color = m.entity === 'RetailGroup Co' ? '#3b82f6' : m.entity === 'RetailGroup Credit' ? '#10b981' : '#8b5cf6'}
							<div class="relative flex items-start gap-3 py-2.5 group">
								<div class="absolute left-[-15px] mt-1.5 w-2.5 h-2.5 rounded-full border-2 bg-white z-10 group-hover:scale-125 transition-transform" style="border-color: {color}"></div>
								<div class="flex-1 min-w-0">
									<p class="text-sm text-gray-700 capitalize">{safe(m.event).replace(/_/g, ' ')}</p>
									<p class="text-xs text-gray-400 mt-0.5">
										<span class="inline-block w-1.5 h-1.5 rounded-full mr-1 align-middle" style="background: {color}"></span>
										{m.entity} · {fdate(m.date)}
									</p>
								</div>
							</div>
						{/each}
					</div>
				</div>
			</div>

			<!-- LTV Trend -->
			{#if ltvTrendLabels.length > 0}
				<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
					<h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-5">Lifetime Value Trend</h3>
					<LineChart labels={ltvTrendLabels} datasets={[{ label: 'LTV (RM)', data: ltvTrendData, color: '#c8a951' }]} height="160px" />
				</div>
			{/if}

			<!-- Recent Transactions -->
			{#if transactions.length > 0}
				<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
					<div class="flex items-center justify-between mb-5">
						<h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Recent Transactions</h3>
						<span class="text-[11px] text-gray-400">{transactions.length} total</span>
					</div>
					<div class="overflow-x-auto">
						<table class="w-full text-sm border-collapse">
							<thead>
								<tr class="text-[10px] text-gray-400 uppercase tracking-wider border-b border-gray-100">
									<th class="py-2.5 pr-4 text-left font-medium">Date</th>
									<th class="py-2.5 pr-4 text-left font-medium">Entity</th>
									<th class="py-2.5 pr-4 text-left font-medium">Store</th>
									<th class="py-2.5 pr-4 text-left font-medium">Items</th>
									<th class="py-2.5 pr-4 text-right font-medium">Total</th>
									<th class="py-2.5 text-left font-medium">Payment</th>
								</tr>
							</thead>
							<tbody>
								{#each transactions.slice(0, 15) as tx}
									<tr class="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
										<td class="py-3 pr-4 text-gray-500 tabular-nums text-xs">{fdate(tx.date)}</td>
										<td class="py-3 pr-4">
											<span class="text-[11px] px-2 py-0.5 rounded-md font-medium {tx.entity === 'RetailGroup Co' ? 'bg-blue-50 text-blue-700' : tx.entity === 'RetailGroup Credit' ? 'bg-emerald-50 text-emerald-700' : 'bg-violet-50 text-violet-700'}">{tx.entity}</span>
										</td>
										<td class="py-3 pr-4 text-gray-500 text-xs font-mono">{tx.store_id}</td>
										<td class="py-3 pr-4 text-gray-500 text-xs truncate max-w-[220px]">{tx.items.map(i => i.subcategory).join(', ')}</td>
										<td class="py-3 pr-4 text-right font-semibold text-gray-800 tabular-nums">{formatRM(tx.total_myr, 2)}</td>
										<td class="py-3 text-gray-400 text-xs capitalize">{safe(tx.payment_method).replace(/_/g, ' ') || '—'}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			{/if}

		<!-- ═══════════════════ ENTITIES TAB ═══════════════════ -->
		{:else if activeTab === 'entities'}

			<!-- ──── Cross-entity Summary ──── -->
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
				<h3 class="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-5">Cross-Entity Overview</h3>
				<div class="flex items-center justify-center gap-12">
					{#each ['RetailGroup Co', 'RetailGroup Credit', 'RetailGroup Bank'] as ent}
						{@const active = customer.entities.includes(ent)}
						{@const color = ent === 'RetailGroup Co' ? '#3b82f6' : ent === 'RetailGroup Credit' ? '#10b981' : '#8b5cf6'}
						<div class="text-center {active ? '' : 'opacity-30'}">
							<div class="w-14 h-14 mx-auto rounded-2xl flex items-center justify-center mb-2 transition-all" style="background: {active ? color + '10' : '#f3f4f6'}">
								<svg class="w-6 h-6" style="color: {active ? color : '#9ca3af'}" fill="currentColor" viewBox="0 0 24 24"><path d={entityIcons[ent]}></path></svg>
							</div>
							<p class="text-xs font-semibold {active ? 'text-gray-700' : 'text-gray-400'}">{ent}</p>
							<p class="text-[10px] mt-0.5 font-medium {active ? 'text-emerald-600' : 'text-amber-500'}">{active ? 'Active' : 'Opportunity'}</p>
						</div>
						{#if ent !== 'RetailGroup Bank'}
							<div class="w-12 border-t-2 {customer.entities.includes(ent) ? 'border-gray-200' : 'border-dashed border-gray-100'}"></div>
						{/if}
					{/each}
				</div>
			</div>

			<!-- ──── RetailGroup Co ──── -->
			{@const co = customer.entity_profiles?.RetailGroup_co}
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
				<div class="flex items-center gap-3.5 px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-blue-50/80 to-white">
					<div class="w-10 h-10 rounded-xl bg-blue-500 flex items-center justify-center shadow-sm shadow-blue-200">
						<svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24"><path d={entityIcons['RetailGroup Co']}></path></svg>
					</div>
					<div class="flex-1">
						<h3 class="text-sm font-semibold text-gray-800">RetailGroup Co</h3>
						<p class="text-[11px] text-gray-400">Retail & Loyalty</p>
					</div>
					{#if customer.entities.includes('RetailGroup Co')}
						<span class="text-[10px] px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 font-semibold">Active</span>
					{/if}
					{#if co}<span class="text-[11px] text-gray-400">Member since {fdate(co.member_since)}</span>{/if}
				</div>
				{#if co}
					<div class="p-6">
						<div class="grid grid-cols-5 gap-6 mb-6">
							<div class="text-center">
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-1.5">Points Balance</p>
								<p class="text-2xl font-bold text-blue-600">{(co.points_balance ?? 0).toLocaleString()}</p>
							</div>
							<div class="text-center">
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-1.5">Expiring Soon</p>
								<p class="text-2xl font-bold text-amber-500">{(co.points_expiring_soon?.amount ?? 0).toLocaleString()}</p>
								{#if co.points_expiring_soon?.expiry_date}
									<p class="text-[10px] text-gray-400 mt-0.5">by {fdate(co.points_expiring_soon.expiry_date)}</p>
								{/if}
							</div>
							<div class="text-center">
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-1.5">Avg Basket</p>
								<p class="text-2xl font-bold text-gray-800">{formatRM(co.avg_basket_myr)}</p>
							</div>
							<div class="text-center">
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-1.5">Visits / Month</p>
								<p class="text-2xl font-bold text-gray-800">{Math.round(co.visit_frequency_monthly * 10) / 10}</p>
							</div>
							<div class="text-center">
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-1.5">Lifetime Visits</p>
								<p class="text-2xl font-bold text-gray-800">{(co.lifetime_visits ?? 0).toLocaleString()}</p>
							</div>
						</div>
						<div class="grid grid-cols-2 gap-6 pt-5 border-t border-gray-100">
							<div>
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-3">Top Categories</p>
								<div class="flex flex-wrap gap-2">
									{#each co.top_categories ?? [] as cat}
										<span class="text-xs px-3 py-1.5 bg-blue-50 text-blue-600 rounded-lg capitalize font-medium">{safe(cat).replace(/_/g, ' ')}</span>
									{/each}
								</div>
								{#if co.last_purchase_date}
									<p class="text-[11px] text-gray-400 mt-4">Last purchase <span class="font-medium text-gray-600">{fdate(co.last_purchase_date)}</span></p>
								{/if}
							</div>
							<div>
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-3">Preferred Stores</p>
								{#if co.preferred_stores?.length > 0}
									<div class="space-y-2">
										{#each co.preferred_stores.slice(0, 4) as store}
											<div class="flex items-center gap-3 text-xs">
												<span class="font-mono font-semibold text-gray-700 w-24 shrink-0">{store.store_id}</span>
												<span class="text-gray-400">{store.visit_count} visits</span>
												<span class="text-gray-300">·</span>
												<span class="text-gray-400">avg {formatRM(store.avg_basket_at_store_myr)}</span>
												{#if store.last_visit}
													<span class="text-gray-300">·</span>
													<span class="text-gray-400">last {fdate(store.last_visit)}</span>
												{/if}
											</div>
										{/each}
									</div>
								{:else}
									<p class="text-xs text-gray-300">No store data</p>
								{/if}
							</div>
						</div>
					</div>
				{:else}
					<div class="px-6 py-12 text-center">
						{#if customer.entities.includes('RetailGroup Co')}
							<p class="text-sm text-gray-400">Profile data unavailable</p>
						{:else}
							<p class="text-sm text-gray-400">Not enrolled · <span class="text-amber-500 font-medium">Cross-sell opportunity</span></p>
						{/if}
					</div>
				{/if}
			</div>

			<!-- ──── RetailGroup Credit ──── -->
			{@const credit = customer.entity_profiles?.RetailGroup_credit}
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
				<div class="flex items-center gap-3.5 px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-emerald-50/80 to-white">
					<div class="w-10 h-10 rounded-xl bg-emerald-500 flex items-center justify-center shadow-sm shadow-emerald-200">
						<svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24"><path d={entityIcons['RetailGroup Credit']}></path></svg>
					</div>
					<div class="flex-1">
						<h3 class="text-sm font-semibold text-gray-800">RetailGroup Credit</h3>
						<p class="text-[11px] text-gray-400">Financial Services</p>
					</div>
					{#if customer.entities.includes('RetailGroup Credit')}
						<span class="text-[10px] px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 font-semibold">Active</span>
					{/if}
					{#if credit}<span class="text-[11px] text-gray-400">Member since {fdate(credit.member_since)}</span>{/if}
				</div>
				{#if credit}
					<div class="p-6">
						<div class="grid grid-cols-4 gap-6 mb-6">
							<div class="text-center">
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-1.5">Credit Limit</p>
								<p class="text-2xl font-bold text-emerald-600">{formatCurrency(credit.total_credit_limit_myr)}</p>
							</div>
							<div class="text-center">
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-1.5">Outstanding</p>
								<p class="text-2xl font-bold text-gray-800">{formatCurrency(credit.total_outstanding_myr)}</p>
							</div>
							<div class="text-center">
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-1.5">Payment Score</p>
								<p class="text-2xl font-bold text-gray-800">{pct(credit.payment_history_score)}%</p>
							</div>
							<div>
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-2 text-center">Utilization</p>
								<div class="w-full bg-gray-100 rounded-full h-2.5">
									<div class="h-2.5 rounded-full transition-all" style="width: {Math.min(utilPct(credit.total_outstanding_myr, credit.total_credit_limit_myr), 100)}%; background: {utilPct(credit.total_outstanding_myr, credit.total_credit_limit_myr) > 80 ? '#dc2626' : utilPct(credit.total_outstanding_myr, credit.total_credit_limit_myr) > 50 ? '#d97706' : '#10b981'}"></div>
								</div>
								<p class="text-center text-xs font-bold mt-1.5 text-gray-600">{Math.round(utilPct(credit.total_outstanding_myr, credit.total_credit_limit_myr))}%</p>
							</div>
						</div>

						{#if credit.products?.length > 0}
							<div class="pt-5 border-t border-gray-100">
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-4">Credit Products</p>
								<div class="overflow-x-auto">
									<table class="w-full text-sm">
										<thead>
											<tr class="text-[10px] text-gray-400 uppercase tracking-wider border-b border-gray-100">
												<th class="pb-2.5 pr-4 text-left font-medium">Product</th>
												<th class="pb-2.5 pr-4 text-left font-medium">Type</th>
												<th class="pb-2.5 pr-4 text-right font-medium">Limit</th>
												<th class="pb-2.5 pr-4 text-right font-medium">Outstanding</th>
												<th class="pb-2.5 pr-4 text-center font-medium">Utilization</th>
												<th class="pb-2.5 pr-4 text-right font-medium">APR</th>
												<th class="pb-2.5 pr-4 text-right font-medium">Monthly</th>
												<th class="pb-2.5 text-center font-medium">Status</th>
											</tr>
										</thead>
										<tbody>
											{#each credit.products as prod}
												<tr class="border-b border-gray-50">
													<td class="py-3 pr-4 font-semibold text-gray-700">{prod.product_name}</td>
													<td class="py-3 pr-4 text-gray-400 text-xs capitalize">{safe(prod.product_type).replace(/_/g, ' ')}</td>
													<td class="py-3 pr-4 text-right tabular-nums text-gray-600">{formatRM(prod.limit_myr)}</td>
													<td class="py-3 pr-4 text-right tabular-nums text-gray-600">{formatRM(prod.outstanding_myr)}</td>
													<td class="py-3 pr-4">
														<div class="flex items-center gap-2">
															<div class="flex-1 bg-gray-100 rounded-full h-1.5">
																<div class="h-1.5 rounded-full transition-all" style="width: {prod.utilization_pct}%; background: {prod.utilization_pct > 80 ? '#dc2626' : prod.utilization_pct > 50 ? '#d97706' : '#10b981'}"></div>
															</div>
															<span class="text-xs font-semibold text-gray-600 tabular-nums w-8 text-right">{Math.round(prod.utilization_pct)}%</span>
														</div>
													</td>
													<td class="py-3 pr-4 text-right tabular-nums text-gray-500 text-xs">{prod.interest_rate_pct?.toFixed(1) ?? '—'}%</td>
													<td class="py-3 pr-4 text-right tabular-nums text-gray-600 text-xs">{prod.monthly_payment_myr ? formatRM(Math.round(prod.monthly_payment_myr)) : '—'}</td>
													<td class="py-3 text-center">
														<span class="text-[10px] px-2 py-0.5 rounded-full font-medium {prod.status === 'active' ? 'bg-emerald-50 text-emerald-600' : 'bg-gray-100 text-gray-400'}">{prod.status}</span>
													</td>
												</tr>
											{/each}
										</tbody>
									</table>
								</div>
							</div>
						{/if}
					</div>
				{:else}
					<div class="px-6 py-12 text-center">
						{#if customer.entities.includes('RetailGroup Credit')}
							<p class="text-sm text-gray-400">Profile data unavailable</p>
						{:else}
							<p class="text-sm text-gray-400">Not enrolled · <span class="text-amber-500 font-medium">Cross-sell opportunity</span></p>
						{/if}
					</div>
				{/if}
			</div>

			<!-- ──── RetailGroup Bank ──── -->
			{@const bank = customer.entity_profiles?.RetailGroup_bank}
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
				<div class="flex items-center gap-3.5 px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-violet-50/80 to-white">
					<div class="w-10 h-10 rounded-xl bg-violet-500 flex items-center justify-center shadow-sm shadow-violet-200">
						<svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24"><path d={entityIcons['RetailGroup Bank']}></path></svg>
					</div>
					<div class="flex-1">
						<h3 class="text-sm font-semibold text-gray-800">RetailGroup Bank</h3>
						<p class="text-[11px] text-gray-400">Digital Banking</p>
					</div>
					{#if customer.entities.includes('RetailGroup Bank')}
						<span class="text-[10px] px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 font-semibold">Active</span>
					{/if}
					{#if bank}<span class="text-[11px] text-gray-400">Member since {fdate(bank.member_since)}</span>{/if}
				</div>
				{#if bank}
					<div class="p-6">
						<div class="grid grid-cols-4 gap-6">
							<div class="text-center">
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-1.5">Balance</p>
								<p class="text-2xl font-bold text-violet-600">{formatCurrency(bank.balance_myr)}</p>
							</div>
							<div class="text-center">
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-1.5">Account Type</p>
								<p class="text-2xl font-bold text-gray-800 capitalize">{bank.account_type}</p>
							</div>
							<div>
								<p class="text-[10px] text-gray-400 font-medium uppercase tracking-wider mb-2 text-center">Digital Engagement</p>
								<div class="w-full bg-gray-100 rounded-full h-2.5">
									<div class="h-2.5 rounded-full bg-violet-500 transition-all" style="width: {bank.digital_engagement_score * 100}%"></div>
								</div>
								<p class="text-center text-xs font-bold mt-1.5 text-gray-600">{pct(bank.digital_engagement_score)}%</p>
							</div>
							<div class="flex items-center justify-center">
								<div class="flex items-center gap-2.5 px-4 py-2.5 rounded-lg {bank.has_debit_card ? 'bg-violet-50 border border-violet-100' : 'bg-gray-50 border border-gray-100'}">
									{#if bank.has_debit_card}
										<svg class="w-4 h-4 text-violet-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path></svg>
										<span class="text-sm font-medium text-violet-700">Debit Card Active</span>
									{:else}
										<svg class="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>
										<span class="text-sm font-medium text-gray-500">No Debit Card</span>
									{/if}
								</div>
							</div>
						</div>
					</div>
				{:else}
					<div class="px-6 py-12 text-center">
						{#if customer.entities.includes('RetailGroup Bank')}
							<p class="text-sm text-gray-400">Profile data unavailable</p>
						{:else}
							<p class="text-sm text-gray-400">Not enrolled · <span class="text-amber-500 font-medium">Cross-sell opportunity</span></p>
						{/if}
					</div>
				{/if}
			</div>

		<!-- ═══════════════════ INTERACTIONS TAB ═══════════════════ -->
		{:else if activeTab === 'interactions'}
			<div class="grid grid-cols-2 gap-6">
				<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
					<h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-5">Channel Performance</h3>
					{#if channelLabels.length > 0}
						<RadarChart labels={channelLabels} datasets={[
							{ label: 'Open Rate %', data: channelOpenRates, color: '#003b73' },
							{ label: 'CTR %', data: channelCtr, color: '#c8a951' },
							{ label: 'Conversion %', data: channelConversion, color: '#10b981' },
						]} height="260px" />
					{:else}
						<div class="flex items-center justify-center h-[260px] text-sm text-gray-300">No channel data</div>
					{/if}
				</div>

				<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
					<h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-5">Engagement by Channel</h3>
					<div class="space-y-3">
						{#each Object.entries(customer.interaction_history.channel_engagement_rates) as [channel, rates]}
							<div class="border border-gray-100 rounded-lg p-3.5">
								<div class="flex items-center justify-between mb-2.5">
									<p class="text-sm font-semibold text-gray-700 capitalize">{channel.replace(/_/g, ' ')}</p>
									<span class="text-[10px] text-gray-400 font-medium">{rates.total_sent?.toLocaleString() ?? '—'} sent</span>
								</div>
								<div class="grid grid-cols-3 gap-3">
									<div><p class="text-[11px] text-gray-400">Open Rate</p><p class="text-sm font-bold text-[#003b73]">{pct(rates.open_rate)}%</p></div>
									<div><p class="text-[11px] text-gray-400">CTR</p><p class="text-sm font-bold text-[#c8a951]">{pct(rates.ctr)}%</p></div>
									<div><p class="text-[11px] text-gray-400">Conversion</p><p class="text-sm font-bold text-emerald-600">{pct(rates.conversion_rate)}%</p></div>
								</div>
							</div>
						{/each}
					</div>
				</div>
			</div>

			<!-- Support Interactions -->
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
				<h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-5">Support Interactions</h3>
				{#if customer.interaction_history.support_interactions.length > 0}
					<div class="space-y-1">
						{#each customer.interaction_history.support_interactions.slice(0, 10) as si}
							<div class="flex items-start gap-3 py-3 border-b border-gray-50 last:border-0">
								<span class="text-xs text-gray-400 w-20 shrink-0 tabular-nums mt-0.5">{fdate(si.date)}</span>
								<span class="text-[11px] px-2 py-0.5 rounded-md bg-gray-100 text-gray-600 w-20 text-center shrink-0 capitalize font-medium">{safe(si.channel).replace(/_/g, ' ')}</span>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2">
										<span class="text-sm text-gray-700 font-medium capitalize">{safe(si.category).replace(/_/g, ' ')}</span>
										{#if si.subcategory}
											<span class="text-[10px] text-gray-400 capitalize">· {safe(si.subcategory).replace(/_/g, ' ')}</span>
										{/if}
									</div>
									{#if si.notes}
										<p class="text-xs text-gray-400 mt-0.5 line-clamp-1">{si.notes}</p>
									{/if}
								</div>
								<span class="text-[11px] px-2 py-0.5 rounded-md shrink-0 font-medium {si.sentiment === 'positive' ? 'bg-emerald-50 text-emerald-600' : si.sentiment === 'negative' ? 'bg-red-50 text-red-500' : 'bg-gray-50 text-gray-400'}">{si.sentiment || 'neutral'}</span>
								{#if si.resolution}
									<span class="text-[11px] text-gray-400 capitalize shrink-0">{si.resolution}</span>
								{/if}
								{#if si.resolution_time_minutes}
									<span class="text-[10px] text-gray-400 shrink-0 tabular-nums font-mono">{si.resolution_time_minutes}m</span>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-gray-300 py-8 text-center">No support interactions recorded</p>
				{/if}
			</div>

			<!-- Marketing Interactions -->
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
				<h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-5">Marketing Interactions</h3>
				{#if customer.interaction_history.marketing_interactions.length > 0}
					<div class="overflow-x-auto">
						<table class="w-full text-xs border-collapse">
							<thead>
								<tr class="text-[10px] text-gray-400 uppercase tracking-wider border-b border-gray-100">
									<th class="py-2.5 pr-3 text-left font-medium">Sent</th>
									<th class="py-2.5 pr-3 text-left font-medium">Channel</th>
									<th class="py-2.5 pr-3 text-left font-medium">Campaign</th>
									<th class="py-2.5 pr-3 text-center font-medium">Opened</th>
									<th class="py-2.5 pr-3 text-center font-medium">Clicked</th>
									<th class="py-2.5 pr-3 text-center font-medium">Converted</th>
									<th class="py-2.5 text-right font-medium">Revenue</th>
								</tr>
							</thead>
							<tbody>
								{#each customer.interaction_history.marketing_interactions.slice(0, 15) as mi}
									<tr class="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
										<td class="py-2 pr-3 text-gray-400 tabular-nums">{fdate(mi.sent_at)}</td>
										<td class="py-2 pr-3 capitalize font-medium">{safe(mi.channel).replace(/_/g, ' ')}</td>
										<td class="py-2 pr-3 text-gray-500 font-mono">{mi.campaign_id}</td>
										<td class="py-2 pr-3 text-center">{mi.opened_at ? '✓' : '—'}</td>
										<td class="py-2 pr-3 text-center">{mi.clicked_at ? '✓' : '—'}</td>
										<td class="py-2 pr-3 text-center">{mi.converted_at ? '✓' : '—'}</td>
										<td class="py-2 text-right font-semibold tabular-nums {mi.revenue_attributed_myr > 0 ? 'text-emerald-600' : 'text-gray-300'}">
											{mi.revenue_attributed_myr > 0 ? formatRM(Math.round(mi.revenue_attributed_myr)) : '—'}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else}
					<p class="text-sm text-gray-300 py-8 text-center">No marketing interactions recorded</p>
				{/if}
			</div>

		<!-- ═══════════════════ CAMPAIGNS TAB ═══════════════════ -->
		{:else if activeTab === 'campaigns'}
			<div class="flex items-center justify-between">
				<div>
					<h3 class="text-lg font-semibold text-gray-800">Campaign Enrollments</h3>
					<p class="text-sm text-gray-400 mt-0.5">AI-powered cross-sell recommendations</p>
				</div>
				<button
					onclick={runAgent}
					disabled={recommending}
					class="px-5 py-2.5 text-sm bg-[#003b73] text-white rounded-lg hover:bg-[#004e99] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-sm"
				>
					{#if recommending}
						<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
						Running Agent...
					{:else}
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
						Generate Recommendation
					{/if}
				</button>
			</div>

			{#if customer.active_campaigns.length === 0 && !recommendation}
				<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
					<div class="w-16 h-16 mx-auto rounded-2xl bg-gray-50 flex items-center justify-center mb-4">
						<svg class="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"></path></svg>
					</div>
					<p class="text-gray-600 font-medium">No active campaigns</p>
					<p class="text-sm text-gray-400 mt-1">Click "Generate Recommendation" to run the cross-sell agent</p>
				</div>
			{:else}
				<div class="space-y-4">
					{#each customer.active_campaigns as ac}
						<div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
							<div class="p-5">
								<div class="flex items-start justify-between">
									<div class="flex-1">
										<div class="flex items-center gap-2">
											<h4 class="font-semibold text-gray-800">{ac.campaign_name}</h4>
											<span class="text-[10px] px-2.5 py-0.5 rounded-full font-medium {ac.status === 'enrolled' ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' : ac.status === 'converted' ? 'bg-blue-50 text-blue-600 border border-blue-200' : 'bg-gray-100 text-gray-500'}">{ac.status}</span>
											{#if ac.enrolled_by}
												<span class="text-[10px] px-2 py-0.5 rounded-md bg-gray-100 text-gray-400 capitalize font-medium">{ac.enrolled_by}</span>
											{/if}
										</div>
										<p class="text-xs text-gray-400 mt-1">{ac.campaign_id} · {safe(ac.recommended_channel).replace(/_/g, ' ')}</p>
									</div>
									<div class="text-right">
										<p class="text-lg font-bold text-emerald-600">+{formatRM(Math.round(ac.expected_ltv_uplift))}</p>
										<p class="text-[11px] text-gray-400">LTV uplift</p>
									</div>
								</div>
								<div class="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-gray-100">
									<div><p class="text-[11px] text-gray-400">Enrolled</p><p class="text-sm font-medium text-gray-700">{fdate(ac.enrolled_date)}</p></div>
									<div><p class="text-[11px] text-gray-400">Conversion Rate</p><p class="text-sm font-medium text-gray-700">{pct(ac.similar_customer_conversion_rate)}%</p></div>
									<div><p class="text-[11px] text-gray-400">Content</p><p class="text-sm font-medium text-gray-700 truncate">{ac.content_headline || '—'}</p></div>
									<div>
										<p class="text-[11px] text-gray-400">Revenue Realized</p>
										<p class="text-sm font-medium {ac.revenue_realized_myr > 0 ? 'text-emerald-600' : 'text-gray-400'}">
											{ac.revenue_realized_myr > 0 ? formatRM(Math.round(ac.revenue_realized_myr)) : '—'}
										</p>
									</div>
								</div>
							</div>
							<button
								onclick={() => showReason = showReason === ac.campaign_id ? null : ac.campaign_id}
								class="w-full px-5 py-2.5 bg-gray-50 border-t border-gray-100 text-xs text-[#003b73] hover:bg-gray-100 transition-colors cursor-pointer font-medium flex items-center justify-center gap-1.5"
							>
								<svg class="w-3.5 h-3.5 transition-transform {showReason === ac.campaign_id ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
								{showReason === ac.campaign_id ? 'Hide' : 'Show'} AI Reasoning
							</button>
							{#if showReason === ac.campaign_id}
								<div class="px-5 py-4 bg-blue-50/50 border-t border-blue-100">
									<p class="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{ac.reasoning}</p>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}

			{#if recommendation}
				<div class="bg-white rounded-xl shadow-sm border-2 border-[#003b73]/20 overflow-hidden">
					<div class="bg-[#003b73]/5 px-5 py-3.5 border-b border-[#003b73]/10 flex items-center gap-2">
						<svg class="w-4 h-4 text-[#003b73]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path></svg>
						<h3 class="text-sm font-semibold text-[#003b73]">Agent Recommendation</h3>
						<span class="text-xs text-gray-400 ml-auto">{recommendation.mode} · {recommendation.queries_executed.length} queries</span>
					</div>
					<div class="p-6 space-y-5">
						<div>
							<p class="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Pattern Analysis</p>
							<p class="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{recommendation.pattern_analysis}</p>
						</div>
						{#if recommendation.similar_customers.length > 0}
							<div>
								<p class="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Similar Customers</p>
								<div class="flex flex-wrap gap-1.5">
									{#each recommendation.similar_customers as sc}
										<a href="/customer/{sc.customer_id}" class="text-xs px-3 py-1 rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors font-medium">{sc.name} ({pct(sc.score)}%)</a>
									{/each}
								</div>
							</div>
						{/if}
						<div class="grid grid-cols-2 gap-6">
							<div>
								<p class="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Matched Campaigns</p>
								{#each recommendation.matched_campaigns as mc}
									<div class="flex items-center justify-between text-sm py-1.5"><span class="text-gray-700">{mc.name}</span><span class="text-xs font-mono text-gray-400">{mc.rerank_score.toFixed(2)}</span></div>
								{/each}
							</div>
							<div>
								<p class="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Matched Content</p>
								{#each recommendation.matched_content as mc}
									<div class="flex items-center justify-between text-sm py-1.5"><span class="text-gray-700 truncate">{mc.headline}</span><span class="text-xs text-gray-400 shrink-0 ml-2">{mc.channel}</span></div>
								{/each}
							</div>
						</div>
						<div class="pt-4 border-t border-gray-100">
							<p class="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Recommendation</p>
							<p class="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{recommendation.recommendation}</p>
						</div>
						{#if recommendation.recommended_channel}
							<div class="flex items-center gap-2"><span class="text-xs text-gray-400">Best channel:</span><span class="text-xs px-2.5 py-0.5 rounded-full bg-[#003b73] text-white font-medium capitalize">{safe(recommendation.recommended_channel).replace(/_/g, ' ')}</span></div>
						{/if}
					</div>
				</div>
			{/if}
		{/if}
	</div>
{:else}
	<div class="flex items-center justify-center h-96">
		<div class="text-center">
			<p class="text-lg text-gray-400">Customer not found</p>
			<a href="/search" class="text-sm text-[#003b73] hover:underline mt-2 inline-block">Back to search</a>
		</div>
	</div>
{/if}

{/if}














