<script lang="ts">
	import { onMount } from 'svelte';
	import { getDashboardKPIs, type DashboardKPIs, type Signal } from '$lib/api';
	import DoughnutChart from '$lib/components/charts/DoughnutChart.svelte';
	import BarChart from '$lib/components/charts/BarChart.svelte';
	import Sparkline from '$lib/components/charts/Sparkline.svelte';

	let kpis = $state<DashboardKPIs | null>(null);
	let loading = $state(true);
	let signals = $state<Signal[]>([]);
	let simulating = $state(false);

	let eventSource: EventSource | null = null;

	onMount(() => {
		(async () => {
			try {
				kpis = await getDashboardKPIs();
				signals = kpis.recent_signals || [];
			} catch (e) {
				console.error('Failed to load KPIs', e);
			} finally {
				loading = false;
			}
		})();

		try {
			eventSource = new EventSource('http://localhost:8000/api/signals/stream');
			eventSource.onmessage = (event) => {
				const signal = JSON.parse(event.data);
				signals = [signal, ...signals.slice(0, 19)];
			};
		} catch {
			// SSE not available yet
		}

		return () => eventSource?.close();
	});

	function fmtNum(n: number): string {
		if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
		if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
		return n.toString();
	}

	function fmtPct(n: number): string {
		return `${(n * 100).toFixed(1)}%`;
	}

	async function startSimulator() {
		simulating = true;
		try {
			await fetch('http://localhost:8000/api/signals/simulate', { method: 'POST' });
		} catch {
			// ignore
		}
	}

	// Chart data
	const segmentData = $derived(() => {
		if (!kpis) return { labels: [], data: [], colors: [] };
		const entries = Object.entries(kpis.customers_by_segment).sort((a, b) => b[1] - a[1]);
		const colors = ['#003b73', '#c8a951', '#0ea5e9', '#8b5cf6', '#ec4899', '#f97316', '#14b8a6'];
		return {
			labels: entries.map(([k]) => k.replace(/_/g, ' ')),
			data: entries.map(([, v]) => v),
			colors: entries.map((_, i) => colors[i % colors.length]),
		};
	});

	const tierData = $derived(() => {
		if (!kpis) return { labels: [], datasets: [] };
		const tierOrder = ['Basic', 'Silver', 'Gold', 'Platinum'];
		const entries = tierOrder.filter(t => kpis!.customers_by_tier[t]);
		return {
			labels: entries,
			datasets: [{ label: 'Customers', data: entries.map(t => kpis!.customers_by_tier[t]), color: '#003b73' }],
		};
	});

	const xsChurnData = $derived(() => {
		if (!kpis) return { labels: [], datasets: [] };
		const tierOrder = ['Basic', 'Silver', 'Gold', 'Platinum'];
		const entries = tierOrder.filter(t => kpis!.avg_cross_sell_by_tier[t] !== undefined);
		return {
			labels: entries,
			datasets: [
				{ label: 'Avg Cross-sell', data: entries.map(t => kpis!.avg_cross_sell_by_tier[t]), color: '#003b73' },
				{ label: 'Avg Churn Risk', data: entries.map(t => kpis!.avg_churn_by_tier[t] ?? 0), color: '#dc2626' },
			],
		};
	});

	const ltvData = $derived(() => {
		if (!kpis) return { labels: [], datasets: [] };
		const entries = Object.entries(kpis.avg_ltv_by_segment).sort((a, b) => b[1] - a[1]);
		return {
			labels: entries.map(([k]) => k.replace(/_/g, ' ')),
			datasets: [{ label: 'Avg LTV (RM)', data: entries.map(([, v]) => Math.round(v)), color: '#c8a951' }],
		};
	});
</script>

<div class="p-6 space-y-6">
	<div class="flex items-center justify-between">
		<h2 class="text-2xl font-bold text-gray-800">Dashboard</h2>
		<span class="text-xs text-gray-400">Retail Customer 360 Customer Intelligence</span>
	</div>

	{#if loading}
		<div class="flex items-center justify-center h-64">
			<div class="animate-pulse flex flex-col items-center gap-3">
				<div class="w-10 h-10 rounded-full bg-gray-200"></div>
				<div class="h-4 w-40 bg-gray-200 rounded"></div>
			</div>
		</div>
	{:else if kpis}
		<!-- KPI Cards -->
		<div class="grid grid-cols-4 gap-4">
			<div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
				<div class="flex items-center justify-between">
					<p class="text-xs text-gray-500 font-medium">Total Customers</p>
					<div class="w-8 h-8 rounded-lg bg-[#003b73]/10 flex items-center justify-center">
						<svg class="w-4 h-4 text-[#003b73]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
					</div>
				</div>
				<p class="text-3xl font-bold text-[#003b73] mt-2">{fmtNum(kpis.total_customers)}</p>
			</div>
			<div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
				<div class="flex items-center justify-between">
					<p class="text-xs text-gray-500 font-medium">Cross-sell Opportunities</p>
					<div class="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
						<svg class="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path></svg>
					</div>
				</div>
				<p class="text-3xl font-bold text-emerald-600 mt-2">{fmtNum(kpis.total_opportunities)}</p>
				<p class="text-xs text-gray-400 mt-1">score >= 0.6</p>
			</div>
			<div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
				<div class="flex items-center justify-between">
					<p class="text-xs text-gray-500 font-medium">Active Campaigns</p>
					<div class="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center">
						<svg class="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"></path></svg>
					</div>
				</div>
				<p class="text-3xl font-bold text-[#c8a951] mt-2">{kpis.active_campaigns}</p>
			</div>
			<div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
				<div class="flex items-center justify-between">
					<p class="text-xs text-gray-500 font-medium">Avg Conversion Rate</p>
					<div class="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
						<svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
					</div>
				</div>
				<p class="text-3xl font-bold text-blue-600 mt-2">{fmtPct(kpis.avg_conversion_rate)}</p>
			</div>
		</div>

		<!-- Charts Row -->
		<div class="grid grid-cols-3 gap-6">
			<!-- Segment Distribution -->
			<div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
				<h3 class="text-sm font-semibold text-gray-700 mb-4">Customer Segments</h3>
				{#if segmentData().labels.length > 0}
					<DoughnutChart labels={segmentData().labels} data={segmentData().data} colors={segmentData().colors} height="230px" />
				{/if}
			</div>

			<!-- Customers by Tier -->
			<div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
				<h3 class="text-sm font-semibold text-gray-700 mb-4">Customers by Tier</h3>
				{#if tierData().labels.length > 0}
					<BarChart labels={tierData().labels} datasets={tierData().datasets} height="230px" />
				{/if}
			</div>

			<!-- Cross-sell vs Churn by Tier -->
			<div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
				<h3 class="text-sm font-semibold text-gray-700 mb-4">Cross-sell vs Churn by Tier</h3>
				{#if xsChurnData().labels.length > 0}
					<BarChart labels={xsChurnData().labels} datasets={xsChurnData().datasets} height="230px" />
				{/if}
			</div>
		</div>

		<!-- LTV by Segment -->
		<div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
			<h3 class="text-sm font-semibold text-gray-700 mb-4">Average LTV by Segment</h3>
			{#if ltvData().labels.length > 0}
				<BarChart labels={ltvData().labels} datasets={ltvData().datasets} height="200px" horizontal={true} />
			{/if}
		</div>

		<!-- Real-time Signal Feed -->
		<div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
			<div class="flex items-center justify-between mb-4">
				<div class="flex items-center gap-2">
					<h3 class="text-sm font-semibold text-gray-700">Real-time Signals</h3>
					{#if simulating}
						<span class="relative flex h-2 w-2">
							<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
							<span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
						</span>
					{/if}
				</div>
				<button
					onclick={startSimulator}
					disabled={simulating}
					class="text-xs px-4 py-1.5 rounded-lg bg-[#003b73] text-white hover:bg-[#004e99] disabled:opacity-50 transition-colors cursor-pointer flex items-center gap-1.5"
				>
					{#if simulating}
						<svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
						Streaming...
					{:else}
						Start Demo Signals
					{/if}
				</button>
			</div>
			{#if signals.length === 0}
				<div class="py-8 text-center">
					<div class="w-12 h-12 mx-auto rounded-full bg-gray-100 flex items-center justify-center mb-3">
						<svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
					</div>
					<p class="text-sm text-gray-400">No signals yet. Click "Start Demo Signals" to see real-time events.</p>
				</div>
			{:else}
				<div class="space-y-1 max-h-72 overflow-auto">
					{#each signals as signal, i}
						<div class="flex items-center gap-3 py-2 px-3 rounded-lg text-sm hover:bg-gray-50 transition-colors {i === 0 ? 'bg-blue-50/50' : ''}">
							<span class="w-2 h-2 rounded-full shrink-0" class:bg-red-500={signal.score > 0.7} class:bg-amber-400={signal.score > 0.4 && signal.score <= 0.7} class:bg-emerald-500={signal.score <= 0.4}></span>
							<a href="/customer/{signal.customer_id}" class="text-[#003b73] hover:underline font-mono text-xs font-medium">{signal.customer_id}</a>
							<span class="text-gray-600">{signal.signal_type.replace(/_/g, ' ')}</span>
							<span class="text-xs font-mono text-gray-400 ml-auto">{signal.score.toFixed(2)}</span>
							<span class="text-xs text-gray-400">{signal.created_at?.slice(11, 19)}</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>
