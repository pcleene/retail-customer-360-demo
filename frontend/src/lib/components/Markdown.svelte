<script lang="ts">
	import { marked } from 'marked';

	interface Props {
		content: string;
	}

	let { content }: Props = $props();

	marked.setOptions({
		gfm: true,
		breaks: true,
	});

	function renderMarkdown(text: string): string {
		if (!text) return '';
		return marked.parse(text) as string;
	}
</script>

<div class="prose prose-sm max-w-none">
	{@html renderMarkdown(content)}
</div>

<style>
	.prose :global(h1) { font-size: 1.25rem; font-weight: 700; margin: 0.75rem 0 0.5rem; }
	.prose :global(h2) { font-size: 1.125rem; font-weight: 700; margin: 0.75rem 0 0.5rem; }
	.prose :global(h3) { font-size: 1rem; font-weight: 600; margin: 0.5rem 0 0.25rem; }
	.prose :global(p) { margin: 0.375rem 0; line-height: 1.6; }
	.prose :global(ul), .prose :global(ol) { margin: 0.375rem 0; padding-left: 1.25rem; }
	.prose :global(li) { margin: 0.125rem 0; line-height: 1.5; }
	.prose :global(li::marker) { color: #94a3b8; }
	.prose :global(strong) { font-weight: 600; }
	.prose :global(em) { font-style: italic; }
	.prose :global(code) {
		font-size: 0.8em;
		background: rgba(0,0,0,0.06);
		padding: 0.15em 0.35em;
		border-radius: 0.25rem;
		font-family: 'SF Mono', 'Fira Code', monospace;
	}
	.prose :global(pre) {
		background: #1e293b;
		color: #a5f3fc;
		padding: 0.75rem 1rem;
		border-radius: 0.5rem;
		overflow-x: auto;
		margin: 0.5rem 0;
		font-size: 0.8em;
		line-height: 1.5;
	}
	.prose :global(pre code) {
		background: none;
		padding: 0;
		color: inherit;
	}
	.prose :global(table) {
		width: 100%;
		border-collapse: collapse;
		margin: 0.5rem 0;
		font-size: 0.85em;
	}
	.prose :global(th) {
		background: #f1f5f9;
		font-weight: 600;
		text-align: left;
		padding: 0.4rem 0.75rem;
		border-bottom: 2px solid #e2e8f0;
	}
	.prose :global(td) {
		padding: 0.35rem 0.75rem;
		border-bottom: 1px solid #f1f5f9;
	}
	.prose :global(tr:hover td) {
		background: #f8fafc;
	}
	.prose :global(blockquote) {
		border-left: 3px solid #cbd5e1;
		padding-left: 0.75rem;
		margin: 0.5rem 0;
		color: #64748b;
		font-style: italic;
	}
	.prose :global(hr) {
		border: none;
		border-top: 1px solid #e2e8f0;
		margin: 0.75rem 0;
	}
	.prose :global(a) {
		color: #2563eb;
		text-decoration: underline;
		text-decoration-color: #93c5fd;
	}
</style>
