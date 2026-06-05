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
		height = '200px',
		horizontal = false
	}: {
		labels: string[];
		datasets: Dataset[];
		height?: string;
		horizontal?: boolean;
	} = $props();

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;

	function createChart() {
		if (chart) chart.destroy();
		if (!canvas) return;

		chart = new Chart(canvas, {
			type: 'bar',
			data: {
				labels,
				datasets: datasets.map((ds) => ({
					label: ds.label,
					data: ds.data,
					backgroundColor: ds.color + 'cc',
					borderColor: ds.color,
					borderWidth: 1,
					borderRadius: 4
				}))
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				indexAxis: horizontal ? 'y' : 'x',
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
						grid: { display: horizontal },
						ticks: { font: { size: 10 }, maxRotation: 45 }
					},
					y: {
						grid: { display: !horizontal, color: '#e5e7eb' },
						ticks: { font: { size: 10 } }
					}
				}
			}
		});
	}

	$effect(() => {
		labels;
		datasets;
		horizontal;
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
