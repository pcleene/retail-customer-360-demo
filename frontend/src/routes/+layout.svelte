<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import ArchitectureModal from '$lib/components/ArchitectureModal.svelte';
	import QueryInspector from '$lib/components/QueryInspector.svelte';

	let { children } = $props();

	const nav = [
		{ href: '/', label: 'Dashboard', icon: '◈' },
		{ href: '/search', label: 'Client Search', icon: '⌕' },
		{ href: '/campaigns', label: 'Campaigns', icon: '▤' },
		{ href: '/copilot', label: 'Co-pilot', icon: '◉' },
		{ href: '/insights', label: 'Insights', icon: '◎' },
	];

	function isActive(href: string): boolean {
		const path = page.url.pathname;
		if (href === '/') return path === '/';
		return path === href || path.startsWith(href + '/');
	}
</script>

<svelte:head>
	<title>Retail Customer 360 — Customer 360 Platform</title>
</svelte:head>

<div class="flex h-screen bg-gray-50">
	<!-- Sidebar -->
	<nav class="w-56 bg-[#003b73] text-white flex flex-col shrink-0">
		<div class="p-4 border-b border-white/10">
			<div class="flex items-center gap-2">
				<div class="w-8 h-8 rounded bg-[#c8a951] flex items-center justify-center text-[#003b73] font-black text-sm">A</div>
				<div>
					<h1 class="text-lg font-bold tracking-wide leading-tight">Retail Customer 360</h1>
					<p class="text-[10px] text-white/50 leading-tight">Customer 360 Platform</p>
				</div>
			</div>
		</div>
		<div class="flex-1 py-2">
			{#each nav as item}
				<a
					href={item.href}
					class="flex items-center gap-3 px-4 py-2.5 text-sm transition-colors
						{isActive(item.href) ? 'bg-white/15 text-white border-r-2 border-[#c8a951]' : 'text-white/70 hover:bg-white/10 hover:text-white'}"
				>
					<span class="text-lg w-6 text-center">{item.icon}</span>
					{item.label}
				</a>
			{/each}
		</div>
		<div class="p-4 border-t border-white/10">
			<div class="flex items-center gap-2 mb-2">
				<div class="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
				<span class="text-xs text-white/60">Connected</span>
			</div>
			<p class="text-[10px] text-white/30">MongoDB Atlas + Gemini 2.5 + Voyage AI</p>
		</div>
	</nav>

	<!-- Main -->
	<main class="flex-1 overflow-auto">
		{@render children()}
	</main>
</div>

<ArchitectureModal />
<QueryInspector />
