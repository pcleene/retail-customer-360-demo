export interface QueryEntry {
	collection: string;
	operation: string;
	args: unknown;
	result?: unknown;
	duration_ms: number;
	ts: number;
	endpoint: string;
}

class QueryLogStore {
	entries = $state<QueryEntry[]>([]);

	push(queries: QueryEntry[], endpoint: string) {
		const enriched = queries.map((q) => ({ ...q, endpoint }));
		this.entries = enriched;
	}

	clear() {
		this.entries = [];
	}

	get count() {
		return this.entries.length;
	}
}

export const queryLog = new QueryLogStore();
