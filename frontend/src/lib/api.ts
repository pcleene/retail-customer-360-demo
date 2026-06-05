import { queryLog } from '$lib/stores/queryLog.svelte';

const BASE = 'http://localhost:8000/api';

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
	const res = await fetch(`${BASE}${path}`, {
		headers: { 'Content-Type': 'application/json' },
		...options,
	});
	if (!res.ok) throw new Error(`API error: ${res.status}`);
	const data = await res.json();

	if (data && typeof data === 'object' && !Array.isArray(data) && '_queries' in data) {
		const queries = data._queries;
		delete data._queries;
		if (Array.isArray(queries) && queries.length > 0) {
			queryLog.push(queries, path);
		}
	}

	return data as T;
}

// Dashboard
export function getDashboardKPIs() {
	return fetchJSON<DashboardKPIs>('/dashboard/kpis');
}

// Customers
export function searchCustomers(filters: SearchFilters) {
	return fetchJSON<SearchResult>('/customers/search', {
		method: 'POST',
		body: JSON.stringify(filters),
	});
}

export function getCustomer(id: string) {
	return fetchJSON<Customer>(`/customers/${id}`);
}

export function getCustomerTransactions(id: string, limit = 50) {
	return fetchJSON<Transaction[]>(`/customers/${id}/transactions?limit=${limit}`);
}

export function generateRecommendation(customerId: string) {
	return fetchJSON<RecommendationResult>(`/customers/${customerId}/recommend`, {
		method: 'POST',
	});
}

// Campaigns
export function getCampaigns(status?: string) {
	const qs = status ? `?status=${status}` : '';
	return fetchJSON<Campaign[]>(`/campaigns/${qs}`);
}

export function getCampaign(id: string) {
	return fetchJSON<Campaign>(`/campaigns/${id}`);
}

export function getCampaignEnrollments(id: string) {
	return fetchJSON<CampaignEnrollment[]>(`/campaigns/${id}/enrollments`);
}

// Insights
export function askInsights(question: string, role = 'internal_staff', sessionId = 'default', userId = 'anonymous') {
	return fetchJSON<InsightsResult>('/insights/ask', {
		method: 'POST',
		body: JSON.stringify({ question, role, session_id: sessionId, user_id: userId }),
	});
}

export function getInsightsHistory(sessionId: string) {
	return fetchJSON<ConversationMessage[]>(`/insights/history/${sessionId}`);
}

export function getInsightsConversations(userId?: string) {
	const qs = userId ? `?user_id=${userId}` : '';
	return fetchJSON<ConversationSummary[]>(`/insights/conversations${qs}`);
}

export function getInsightsMemories(userId: string) {
	return fetchJSON<MemoryItem[]>(`/insights/memories/${userId}`);
}

export function getInsightsStats() {
	return fetchJSON<AgentStats>('/insights/stats');
}

// Copilot
export function askCopilot(question: string, sessionId = 'default', userId = 'anonymous') {
	return fetchJSON<CopilotResult>('/copilot/ask', {
		method: 'POST',
		body: JSON.stringify({ question, session_id: sessionId, user_id: userId }),
	});
}

export function getCopilotHistory(sessionId: string) {
	return fetchJSON<ConversationMessage[]>(`/copilot/history/${sessionId}`);
}

export function getCopilotConversations(userId?: string) {
	const qs = userId ? `?user_id=${userId}` : '';
	return fetchJSON<ConversationSummary[]>(`/copilot/conversations${qs}`);
}

export function getCopilotMemories(userId: string) {
	return fetchJSON<MemoryItem[]>(`/copilot/memories/${userId}`);
}

export function getCopilotStats() {
	return fetchJSON<AgentStats>('/copilot/stats');
}

// Shared: users
export function getAppUsers() {
	return fetchJSON<AppUser[]>('/copilot/users');
}

// --- Types ---

// Geo / Address
export interface GeoJSONPoint {
	type: string;
	coordinates: number[]; // [lng, lat]
}

export interface Address {
	street: string;
	city: string;
	state: string;
	postcode: string;
	location: GeoJSONPoint | null;
}

// Contact
export interface ChannelOptIn {
	channel: string;
	opted_in: boolean;
	opted_in_date: string;
}

export interface CommunicationPreferences {
	preferred_language: string;
	quiet_hours_start: string;
	quiet_hours_end: string;
	preferred_contact_time: string;
	do_not_disturb: boolean;
}

export interface ContactInfo {
	email: string;
	phone: string;
	channel_opt_ins: ChannelOptIn[];
	channel_opt_outs: string[];
	communication_preferences: CommunicationPreferences;
}

// Unified Profile
export interface UnifiedProfile {
	name: string;
	ethnicity: string;
	ic_number: string;
	date_of_birth: string;
	gender: string;
	contact: ContactInfo;
	address: Address;
}

// Entity Profiles
export interface PointsExpiry {
	amount: number;
	expiry_date: string;
}

export interface PreferredStore {
	store_id: string;
	visit_count: number;
	avg_basket_at_store_myr: number;
	last_visit: string;
}

export interface CreditProduct {
	product_code: string;
	product_type: string;
	product_name: string;
	issued_date: string;
	outstanding_myr: number;
	limit_myr: number;
	utilization_pct: number;
	monthly_payment_myr: number;
	interest_rate_pct: number;
	tenure_months: number | null;
	status: string;
}

export interface RetailGroupCoProfile {
	member_since: string;
	points_balance: number;
	points_expiring_soon: PointsExpiry;
	preferred_stores: PreferredStore[];
	top_categories: string[];
	avg_basket_myr: number;
	visit_frequency_monthly: number;
	lifetime_visits: number;
	last_purchase_date: string;
}

export interface RetailGroupCreditProfile {
	member_since: string;
	products: CreditProduct[];
	payment_history_score: number;
	total_credit_limit_myr: number;
	total_outstanding_myr: number;
}

export interface RetailGroupBankProfile {
	member_since: string;
	account_type: string;
	balance_myr: number;
	has_debit_card: boolean;
	digital_engagement_score: number;
}

export interface EntityProfiles {
	RetailGroup_co: RetailGroupCoProfile | null;
	RetailGroup_credit: RetailGroupCreditProfile | null;
	RetailGroup_bank: RetailGroupBankProfile | null;
}

// Cross-Entity Metrics
export interface TrendPoint {
	month: string;
	value: number;
}

export interface CrossEntityMetrics {
	total_ltv: number;
	cross_sell_score: number;
	churn_risk: number;
	ltv_trend: TrendPoint[];
	monthly_spend_trend: TrendPoint[];
}

// Interaction History
export interface ChannelEngagementRate {
	open_rate: number;
	ctr: number;
	conversion_rate: number;
	total_sent: number;
	last_engaged_at: string;
}

export interface SupportInteraction {
	ticket_id: string;
	date: string;
	channel: string;
	agent_id: string;
	category: string;
	subcategory: string;
	sentiment: string;
	resolution: string;
	resolution_time_minutes: number;
	notes: string;
}

export interface MarketingInteraction {
	campaign_id: string;
	content_id: string;
	channel: string;
	sent_at: string;
	opened_at: string | null;
	clicked_at: string | null;
	converted_at: string | null;
	revenue_attributed_myr: number;
}

export interface InteractionHistory {
	support_interactions: SupportInteraction[];
	marketing_interactions: MarketingInteraction[];
	channel_engagement_rates: Record<string, ChannelEngagementRate>;
}

// Brand Journey
export interface BrandJourneyMilestone {
	entity: string;
	event: string;
	date: string;
}

// Active Campaigns
export interface ActiveCampaign {
	campaign_id: string;
	campaign_name: string;
	enrollment_id: string;
	enrolled_date: string;
	enrolled_by: string;
	signal_id: string | null;
	content_asset_id: string | null;
	content_headline: string | null;
	recommended_channel: string;
	reasoning: string;
	similar_customer_conversion_rate: number;
	expected_ltv_uplift: number;
	similar_customers_sampled: string[];
	status: string;
	converted_at: string | null;
	revenue_realized_myr: number;
}

// Customer (full profile)
export interface Customer {
	customer_id: string;
	unified_profile: UnifiedProfile;
	segment: string;
	tier: string;
	entities: string[];
	entity_profiles: EntityProfiles;
	cross_entity_metrics: CrossEntityMetrics;
	primary_store_id: string;
	join_date: string;
	last_visit: string;
	brand_journey: BrandJourneyMilestone[];
	interaction_history: InteractionHistory;
	active_campaigns: ActiveCampaign[];
}

// Customer Summary (search results — projected from nested schema)
export interface CustomerSummary {
	customer_id: string;
	unified_profile: {
		name: string;
		address: { state: string; city: string };
		ethnicity?: string;
		gender?: string;
	};
	segment: string;
	tier: string;
	cross_entity_metrics: { total_ltv: number; cross_sell_score: number; churn_risk: number };
	entities: string[];
	primary_store_id?: string;
	join_date?: string;
	last_visit?: string;
	rank_fusion_score?: number;
	score?: number;
}

// Search
export interface SearchFilters {
	query?: string;
	// Scoring criteria (drawer → compound.must, boosts score)
	segments?: string[];
	tiers?: string[];
	states?: string[];
	entities?: string[];
	genders?: string[];
	ethnicities?: string[];
	// Range scoring + hard cutoffs (drawer → compound.should near + compound.filter range)
	churn_risk_min?: number | null;
	churn_risk_max?: number | null;
	cross_sell_score_min?: number | null;
	cross_sell_score_max?: number | null;
	ltv_min?: number | null;
	ltv_max?: number | null;
	// Facet hard filters (sidebar clicks → compound.filter equals)
	facet_segments?: string[];
	facet_tiers?: string[];
	facet_states?: string[];
	facet_entities?: string[];
	facet_genders?: string[];
	facet_ethnicities?: string[];
	page_size?: number;
	page?: number;
	cursor?: string | null;
}

export interface Pagination {
	hasMore: boolean;
	nextCursor: string | null;
	nextPage: number | null;
	limit: number;
}

export interface SearchResult {
	customers: CustomerSummary[];
	total: number;
	facets: {
		segments?: Record<string, number>;
		tiers?: Record<string, number>;
		states?: Record<string, number>;
		entities?: Record<string, number>;
		genders?: Record<string, number>;
		ethnicities?: Record<string, number>;
	};
	search_method: string;
	pagination: Pagination;
}

// Dashboard
export interface Signal {
	customer_id: string;
	signal_type: string;
	score: number;
	details: string;
	processed: boolean;
	created_at: string;
}

export interface DashboardKPIs {
	total_customers: number;
	total_opportunities: number;
	active_campaigns: number;
	avg_conversion_rate: number;
	customers_by_segment: Record<string, number>;
	customers_by_tier: Record<string, number>;
	avg_cross_sell_by_tier: Record<string, number>;
	avg_churn_by_tier: Record<string, number>;
	avg_ltv_by_segment: Record<string, number>;
	recent_signals: Signal[];
}

// Transactions
export interface TransactionItem {
	product_id: string;
	category: string;
	subcategory: string;
	quantity: number;
	unit_price: number;
	line_total: number;
}

export interface Transaction {
	transaction_id: string;
	customer_id: string;
	store_id: string;
	date: string;
	items: TransactionItem[];
	total_myr: number;
	payment_method: string;
	entity: string;
}

// Campaigns
export interface Campaign {
	campaign_id: string;
	name: string;
	type: string;
	entity: string;
	description: string;
	status: string;
	start_date: string;
	end_date: string;
	targeting: {
		segment_criteria: string[];
		behavior_criteria: string[];
		estimated_audience_size: number;
	};
	offer: {
		product: string;
		headline: string;
		value_proposition: string;
		terms: string;
		cta: string;
	};
	performance: {
		enrollment_count: number;
		conversion_rate: number;
		total_revenue_myr: number;
		avg_ltv_uplift: number;
		by_channel: { channel: string; sent: number; opened: number; clicked: number; converted: number }[];
	};
	budget_myr: number;
}

export interface CampaignEnrollment {
	customer_id: string;
	customer_name?: string;
	name?: string;
	campaign_id: string;
	campaign_name: string;
	enrolled_date: string;
	content_id?: string;
	content_headline?: string;
	reason: string;
	content_reason: string;
	expected_ltv_uplift: number;
	targeting_match: number;
	semantic_similarity: number;
	tier?: string;
	segment?: string;
	state?: string;
	ltv_myr?: number;
	active_campaigns?: ActiveCampaign[];
}

// Recommendations (12-node agent)
export interface ReasoningStep {
	step: string;
	status: string;
	duration_ms: number;
	detail?: string;
}

export interface StructuredRecommendation {
	primary_campaign_id: string;
	primary_campaign_name: string;
	content_asset_id: string | null;
	content_headline: string | null;
	recommended_channel: string;
	reasoning: string;
	expected_ltv_uplift: number;
	conversion_probability: number;
	risk_factors: string[];
	fallback_campaign_id: string | null;
	personalization_notes: string;
}

export interface RecommendationResult {
	customer_id: string;
	mode: string;
	pattern_analysis: string;
	similar_customers: { customer_id: string; name: string; score: number }[];
	matched_campaigns: { campaign_id: string; name: string; score: number; rerank_score: number }[];
	matched_content: { content_id: string; headline: string; channel: string; rerank_score: number }[];
	recommended_channel: string;
	recommendation: string;
	structured_recommendation?: StructuredRecommendation;
	reasoning_steps?: ReasoningStep[];
	enrollment_result: Record<string, unknown>;
	queries_executed: Record<string, unknown>[];
}

// Insights
export interface InsightsResult {
	question: string;
	role: string;
	query_type: string;
	mql: Record<string, unknown>[];
	aggregation_results: Record<string, unknown>[];
	search_results: Record<string, unknown>[];
	has_anomaly: boolean;
	anomaly_message: string;
	insight: string;
	queries_executed: Record<string, unknown>[];
	error: string;
	session_id: string;
	user_id: string;
	latency_ms: number;
	preferences_applied: boolean;
	preference_saved: boolean;
}

// Copilot
export interface CopilotResult {
	question: string;
	answer: string;
	mql: Record<string, unknown> | null;
	session_id: string;
	user_id: string;
	latency_ms: number;
	memory_trace: MemoryTraceEntry[];
}

export interface MemoryTraceEntry {
	tool: string;
	input: Record<string, string>;
	output: string;
}

// Shared agent types
export interface ConversationMessage {
	id: string;
	question: string;
	content: string;
	mql: string | Record<string, unknown>;
	latency_ms: number;
	timestamp: string;
}

export interface ConversationSummary {
	threadId: string;
	userId: string;
	agentType: string;
	turnCount: number;
	lastQuestion: string;
	title: string;
	summary: string;
	category: string;
	topics: string[];
	createdAt: string;
	updatedAt: string;
}

export interface MemoryItem {
	key: string;
	value: Record<string, unknown>;
	namespace: string[];
}

export interface AgentStats {
	totalQueries: number;
	activeSessions: number;
	avgLatencyMs: number;
}

export interface AppUser {
	userId: string;
	name: string;
	role: string;
	avatar: string;
	department: string;
	focus?: string;
	preferences?: Record<string, unknown>;
	copilot_suggestions?: string[];
	insights_suggestions?: string[];
}
