<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { getCampaign, getCampaignEnrollments, type Campaign, type CampaignEnrollment } from '$lib/api';
	import BarChart from '$lib/components/charts/BarChart.svelte';

	let campaign = $state<Campaign | null>(null);
	let enrollments = $state<CampaignEnrollment[]>([]);
	let loading = $state(true);
	let showReason = $state<string | null>(null);

	const campaignId = $derived(page.params.id!);

	onMount(async () => {
		try {
			const [c, e] = await Promise.all([
				getCampaign(campaignId),
				getCampaignEnrollments(campaignId),
			]);
			campaign = c;
			enrollments = e;
		} finally {
			loading = false;
		}
	});

	const typeColors: Record<string, string> = {
		cross_sell: 'bg-blue-50 text-blue-700 border-blue-200',
		upsell: 'bg-emerald-50 text-emerald-700 border-emerald-200',
		retention: 'bg-amber-50 text-amber-700 border-amber-200',
		reactivation: 'bg-red-50 text-red-700 border-red-200',
		loyalty_upgrade: 'bg-violet-50 text-violet-700 border-violet-200',
	};

	const entityBg: Record<string, string> = {
		'RetailGroup Co': 'from-blue-500 to-blue-600',
		'RetailGroup Credit': 'from-emerald-500 to-emerald-600',
		'RetailGroup Bank': 'from-violet-500 to-violet-600',
	};

	// Channel performance chart data
	const channelChartData = $derived(() => {
		if (!campaign?.performance.by_channel) return null;
		const ch = campaign.performance.by_channel;
		return {
			labels: ch.map(c => c.channel.replace(/_/g, ' ')),
			datasets: [
				{ label: 'Sent', data: ch.map(c => c.sent), color: '#94a3b8' },
				{ label: 'Opened', data: ch.map(c => c.opened), color: '#003b73' },
				{ label: 'Clicked', data: ch.map(c => c.clicked), color: '#c8a951' },
				{ label: 'Converted', data: ch.map(c => c.converted), color: '#10b981' },
			],
		};
	});
</script>

{#if loading}
	<div class="flex items-center justify-center h-64">
		<div class="animate-pulse flex flex-col items-center gap-3">
			<div class="w-10 h-10 rounded-full bg-gray-200"></div>
			<div class="h-4 w-48 bg-gray-200 rounded"></div>
		</div>
	</div>
{:else if campaign}
	<!-- Campaign Header -->
	<div class="bg-gradient-to-r {entityBg[campaign.entity] || 'from-gray-500 to-gray-600'} px-6 pt-5 pb-14 -mx-6 -mt-6">
		<div class="max-w-7xl mx-auto">
			<a href="/campaigns" class="text-sm text-white/70 hover:text-white transition-colors inline-flex items-center gap-1 mb-3">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
				All Campaigns
			</a>
			<div class="flex items-start justify-between">
				<div>
					<div class="flex items-center gap-2">
						<h1 class="text-2xl font-bold text-white">{campaign.name}</h1>
						<span class={`text-xs px-2.5 py-0.5 rounded-full border font-medium ${typeColors[campaign.type] || 'bg-gray-100 text-gray-700'}`}>{campaign.type.replace(/_/g, ' ')}</span>
						<span class="text-xs px-2.5 py-0.5 rounded-full border {campaign.status === 'active' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-gray-100 text-gray-600 border-gray-200'}">{campaign.status}</span>
					</div>
					<p class="text-white/80 text-sm mt-1 max-w-2xl">{campaign.description}</p>
				</div>
				<div class="text-right">
					<p class="text-3xl font-bold text-white">RM{campaign.budget_myr.toLocaleString()}</p>
					<p class="text-white/60 text-xs">Budget</p>
				</div>
			</div>
		</div>
	</div>

	<!-- Floating KPI Cards -->
	<div class="max-w-7xl mx-auto -mt-8 px-6 mb-6">
		<div class="grid grid-cols-5 gap-4">
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
				<p class="text-xs text-gray-500 font-medium">Enrollments</p>
				<p class="text-2xl font-bold text-[#003b73] mt-1">{campaign.performance.enrollment_count}</p>
			</div>
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
				<p class="text-xs text-gray-500 font-medium">Conversion Rate</p>
				<p class="text-2xl font-bold text-emerald-600 mt-1">{(campaign.performance.conversion_rate * 100).toFixed(1)}%</p>
			</div>
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
				<p class="text-xs text-gray-500 font-medium">Revenue</p>
				<p class="text-2xl font-bold text-[#c8a951] mt-1">RM{campaign.performance.total_revenue_myr.toLocaleString()}</p>
			</div>
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
				<p class="text-xs text-gray-500 font-medium">Avg LTV Uplift</p>
				<p class="text-2xl font-bold text-violet-600 mt-1">RM{campaign.performance.avg_ltv_uplift.toLocaleString()}</p>
			</div>
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
				<p class="text-xs text-gray-500 font-medium">Est. Audience</p>
				<p class="text-2xl font-bold text-gray-700 mt-1">{campaign.targeting.estimated_audience_size.toLocaleString()}</p>
			</div>
		</div>
	</div>

	<div class="max-w-7xl mx-auto px-6 pb-8 space-y-6">
		<div class="grid grid-cols-2 gap-6">
			<!-- Campaign Details -->
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
				<h3 class="text-sm font-semibold text-gray-700 mb-4">Campaign Details</h3>
				<div class="space-y-4">
					<div class="grid grid-cols-2 gap-3">
						<div>
							<p class="text-xs text-gray-400">Entity</p>
							<p class="text-sm font-medium text-gray-700">{campaign.entity}</p>
						</div>
						<div>
							<p class="text-xs text-gray-400">Period</p>
							<p class="text-sm font-medium text-gray-700">{campaign.start_date.slice(0, 10)} - {campaign.end_date.slice(0, 10)}</p>
						</div>
					</div>
					<div>
						<p class="text-xs text-gray-400 mb-1.5">Offer</p>
						<div class="border border-gray-100 rounded-lg p-3 bg-gray-50/50">
							<p class="text-sm font-medium text-gray-700">{campaign.offer.headline}</p>
							<p class="text-xs text-gray-500 mt-1">{campaign.offer.value_proposition}</p>
							<p class="text-xs text-gray-400 mt-1">Product: {campaign.offer.product} &middot; CTA: {campaign.offer.cta}</p>
						</div>
					</div>
					<div>
						<p class="text-xs text-gray-400 mb-1.5">Targeting</p>
						<div class="flex flex-wrap gap-1.5">
							{#each campaign.targeting.segment_criteria as crit}
								<span class="text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-700">{crit.replace(/_/g, ' ')}</span>
							{/each}
							{#each campaign.targeting.behavior_criteria as crit}
								<span class="text-xs px-2 py-0.5 rounded bg-amber-50 text-amber-700">{crit.replace(/_/g, ' ')}</span>
							{/each}
						</div>
					</div>
				</div>
			</div>

			<!-- Channel Performance Chart -->
			<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
				<h3 class="text-sm font-semibold text-gray-700 mb-4">Channel Performance</h3>
				{#if channelChartData()}
					<BarChart labels={channelChartData()!.labels} datasets={channelChartData()!.datasets} height="240px" />
				{:else}
					<p class="text-sm text-gray-400 py-8 text-center">No channel data</p>
				{/if}
			</div>
		</div>

		<!-- Enrolled Customers -->
		<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
			<h3 class="text-sm font-semibold text-gray-700 mb-4">Auto-enrolled Customers ({enrollments.length})</h3>
			{#if enrollments.length === 0}
				<div class="py-8 text-center">
					<div class="w-12 h-12 mx-auto rounded-full bg-gray-100 flex items-center justify-center mb-3">
						<svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
					</div>
					<p class="text-sm text-gray-400">No customers enrolled yet. Run the cross-sell agent to auto-enroll.</p>
				</div>
			{:else}
				<div class="overflow-x-auto">
					<table class="w-full text-sm">
						<thead>
							<tr class="text-left text-xs text-gray-500 border-b border-gray-100">
								<th class="py-2.5 font-medium">Customer</th>
								<th class="py-2.5 font-medium">Tier</th>
								<th class="py-2.5 font-medium">Segment</th>
								<th class="py-2.5 font-medium text-right">LTV</th>
								<th class="py-2.5 font-medium">Enrolled</th>
								<th class="py-2.5 font-medium"></th>
							</tr>
						</thead>
						<tbody>
							{#each enrollments as e}
								{@const ac = (e.active_campaigns?.[0] || e) as Record<string, any>}
								<tr class="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
									<td class="py-2.5">
										<a href="/customer/{e.customer_id}" class="text-[#003b73] hover:underline font-medium">{e.customer_name || e.name || e.customer_id}</a>
									</td>
									<td class="py-2.5">{e.tier || ''}</td>
									<td class="py-2.5 text-gray-600 text-xs">{(e.segment || '').replace(/_/g, ' ')}</td>
									<td class="py-2.5 text-right font-medium">RM{(e.ltv_myr || 0).toLocaleString()}</td>
									<td class="py-2.5 text-xs text-gray-500">{(ac.enrolled_date || '').slice(0, 10)}</td>
									<td class="py-2.5">
										<button
											onclick={() => showReason = showReason === e.customer_id ? null : e.customer_id}
											class="text-xs text-[#003b73] hover:underline cursor-pointer"
										>Why enrolled?</button>
									</td>
								</tr>
								{#if showReason === e.customer_id}
									<tr>
										<td colspan="6" class="pb-3">
											<div class="p-4 bg-blue-50/50 rounded-lg text-sm space-y-2 border border-blue-100">
												<div>
													<p class="text-xs font-medium text-gray-500">Targeting Match</p>
													<p class="text-gray-700">{ac.reason || ac.reasoning || 'N/A'}</p>
												</div>
												{#if ac.content_headline}
													<div>
														<p class="text-xs font-medium text-gray-500">Content</p>
														<p class="text-gray-700">{ac.content_headline}</p>
													</div>
												{/if}
												<div class="flex gap-4">
													<div>
														<p class="text-xs font-medium text-gray-500">Expected LTV Uplift</p>
														<p class="text-gray-700 font-medium">RM{(ac.expected_ltv_uplift || 0).toLocaleString()}</p>
													</div>
													{#if ac.recommended_channel}
														<div>
															<p class="text-xs font-medium text-gray-500">Channel</p>
															<p class="text-gray-700">{ac.recommended_channel.replace(/_/g, ' ')}</p>
														</div>
													{/if}
												</div>
											</div>
										</td>
									</tr>
								{/if}
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</div>
	</div>
{:else}
	<div class="flex items-center justify-center h-64">
		<div class="text-center">
			<p class="text-lg text-gray-500">Campaign not found</p>
			<a href="/campaigns" class="text-sm text-[#003b73] hover:underline mt-2 inline-block">Back to campaigns</a>
		</div>
	</div>
{/if}
