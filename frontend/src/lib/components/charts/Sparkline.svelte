<script lang="ts">
	import { onDestroy } from 'svelte';
	import { Chart, registerables } from 'chart.js';

	Chart.register(...registerables);

	let {
		data,
		color = '#003b73',
		width = '100px',
		height = '30px'
	}: {
		data: number[];
		color?: string;
		width?: string;
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
				labels: data.map((_, i) => String(i)),
				datasets: [
					{
						data,
						borderColor: color,
						backgroundColor: color + '20',
						borderWidth: 1.5,
						fill: true,
						tension: 0.4,
						pointRadius: 0,
						pointHoverRadius: 0
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { display: false },
					tooltip: { enabled: false }
				},
				scales: {
					x: { display: false },
					y: { display: false }
				},
				elements: {
					line: { borderJoinStyle: 'round' }
				},
				animation: { duration: 300 }
			}
		});
	}

	$effect(() => {
		data;
		color;
		createChart();
	});

	onDestroy(() => {
		if (chart) chart.destroy();
	});
</script>

<div class="sparkline-container" style="width: {width}; height: {height};">
	<canvas bind:this={canvas}></canvas>
</div>

<style>
	.sparkline-container {
		position: relative;
		display: inline-block;
	}
</style>
