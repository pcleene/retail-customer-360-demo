<script lang="ts">
	import { onDestroy } from 'svelte';
	import { Chart, registerables } from 'chart.js';

	Chart.register(...registerables);

	let {
		labels,
		data,
		colors,
		height = '200px'
	}: {
		labels: string[];
		data: number[];
		colors: string[];
		height?: string;
	} = $props();

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;

	function createChart() {
		if (chart) chart.destroy();
		if (!canvas) return;

		chart = new Chart(canvas, {
			type: 'doughnut',
			data: {
				labels,
				datasets: [
					{
						data,
						backgroundColor: colors,
						borderColor: '#ffffff',
						borderWidth: 2,
						hoverOffset: 6
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				cutout: '55%',
				plugins: {
					legend: {
						display: true,
						position: 'right',
						labels: {
							boxWidth: 12,
							padding: 8,
							font: { size: 11 },
							usePointStyle: true,
							pointStyle: 'circle'
						}
					}
				}
			}
		});
	}

	$effect(() => {
		labels;
		data;
		colors;
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
