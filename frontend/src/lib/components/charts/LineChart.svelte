<script lang="ts">
	import { onDestroy } from 'svelte';
	import { Chart, registerables } from 'chart.js';

	Chart.register(...registerables);

	interface Dataset {
		label: string;
		data: number[];
		color: string;
	}

	let {
		labels,
		datasets,
		height = '200px'
	}: {
		labels: string[];
		datasets: Dataset[];
		height?: string;
	} = $props();

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;

	function createChart() {
		if (chart) chart.destroy();
		if (!canvas) return;

		chart = new Chart(canvas, {
			type: 'line',
			data: {
				labels,
				datasets: datasets.map((ds) => ({
					label: ds.label,
					data: ds.data,
					borderColor: ds.color,
					backgroundColor: ds.color + '20',
					borderWidth: 2,
					fill: true,
					tension: 0.3,
					pointRadius: 3,
					pointHoverRadius: 5
				}))
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				interaction: {
					intersect: false,
					mode: 'index'
				},
				plugins: {
					legend: {
						display: datasets.length > 1,
						position: 'top',
						labels: {
							boxWidth: 12,
							padding: 8,
							font: { size: 11 }
						}
					}
				},
				scales: {
					x: {
						grid: { display: false },
						ticks: { font: { size: 10 }, maxRotation: 45 }
					},
					y: {
						grid: { color: '#e5e7eb' },
						ticks: { font: { size: 10 } }
					}
				}
			}
		});
	}

	$effect(() => {
		// Track reactive dependencies
		labels;
		datasets;
		createChart();
	});

	onDestroy(() => {
		if (chart) chart.destroy();
	});
</script>

<div class="chart-container" style="height: {height};">
	<canvas bind:this={canvas}></canvas>
</div>

<style>
	.chart-container {
		position: relative;
		width: 100%;
	}
</style>
