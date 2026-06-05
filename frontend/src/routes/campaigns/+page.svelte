<script lang="ts">
	import { onMount } from 'svelte';
	import { getCampaigns, type Campaign } from '$lib/api';

	let campaigns = $state<Campaign[]>([]);
	let loading = $state(true);
	let filter = $state<string | null>(null);

	onMount(async () => {
		try {
			campaigns = await getCampaigns();
		} finally {
			loading = false;
		}
	});

	const filtered = $derived(
		filter ? campaigns.filter((c) => c.type === filter) : campaigns
	);

	const types = ['cross_sell', 'upsell', 'retention', 'reactivation', 'loyalty_upgrade'];

	const typeColors: Record<string, string> = {
		cross_sell: 'bg-blue-100 text-blue-800',
		upsell: 'bg-green-100 text-green-800',
		retention: 'bg-yellow-100 text-yellow-800',
		reactivation: 'bg-red-100 text-red-800',
		loyalty_upgrade: 'bg-purple-100 text-purple-800',
	};
</script>

<div class="p-6 space-y-4">
	<h2 class="text-2xl font-bold text-gray-800">Smart Campaign Lists</h2>

	<!-- Type Filter -->
	<div class="flex gap-2">
		<button
			onclick={() => (filter = null)}
			class="px-3 py-1 text-xs rounded-full cursor-pointer {filter === null ? 'bg-[#003b73] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
		>All</button>
		{#each types as t}
			<button
				onclick={() => (filter = t)}
				class="px-3 py-1 text-xs rounded-full cursor-pointer {filter === t ? 'bg-[#003b73] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
			>{t.replace(/_/g, ' ')}</button>
		{/each}
	</div>

	{#if loading}
		<div class="py-12 text-center text-gray-400">Loading campaigns...</div>
	{:else}
		<div class="grid gap-4">
			{#each filtered as c}
				<a href="/campaigns/{c.campaign_id}" class="block bg-white rounded-lg shadow-sm p-5 border border-gray-100 hover:border-[#003b73]/30 transition-colors">
					<div class="flex items-start justify-between">
						<div class="flex-1">
							<div class="flex items-center gap-2">
								<h3 class="font-semibold text-gray-800">{c.name}</h3>
								<span class={`text-xs px-2 py-0.5 rounded ${typeColors[c.type] || 'bg-gray-100'}`}>{c.type.replace(/_/g, ' ')}</span>
								<span class="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">{c.entity}</span>
								<span class="text-xs px-2 py-0.5 rounded {c.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}">{c.status}</span>
							</div>
							<p class="text-sm text-gray-500 mt-1">{c.description}</p>
							<div class="flex gap-4 mt-2 text-xs text-gray-400">
								<span>{c.start_date.slice(0, 10)} → {c.end_date.slice(0, 10)}</span>
								<span>Budget: RM{c.budget_myr.toLocaleString()}</span>
							</div>
						</div>
						<div class="text-right ml-4 shrink-0">
							<p class="text-2xl font-bold text-[#003b73]">{c.performance.enrollment_count}</p>
							<p class="text-xs text-gray-500">enrollments</p>
							<p class="text-sm font-medium text-green-600 mt-1">{(c.performance.conversion_rate * 100).toFixed(1)}%</p>
							<p class="text-xs text-gray-500">conversion</p>
						</div>
					</div>
				</a>
			{/each}
		</div>
	{/if}
</div>
