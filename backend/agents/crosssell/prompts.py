"""Prompts for the 12-node cross-sell agent pipeline.

Three LLM-backed nodes use these prompts:
  - Node 4:  analyze_patterns
  - Node 8:  analyze_similar_conversions
  - Node 11: generate_recommendations
"""

ANALYZE_PATTERNS_PROMPT = """\
You are a customer intelligence analyst for RetailGroup Group Malaysia, \
which operates three entities: RetailGroup Co (retail/supermarket), \
RetailGroup Credit (credit cards, personal finance), and RetailGroup Bank (digital banking).

Analyze this customer's unified profile and recent transaction history to \
identify cross-sell opportunities across the three RetailGroup entities.

**Unified Profile:**
{unified_profile}

**Entity Profiles:**
{entity_profiles}

**Cross-Entity Metrics:**
{cross_entity_metrics}

**Recent Transactions (up to 50):**
{transactions}

**Your analysis MUST cover:**
1. **Spending patterns** — dominant categories, average basket, frequency, \
   seasonal trends.
2. **Entity gaps** — which RetailGroup entities the customer does NOT yet use and \
   why they are a fit (e.g., high grocery spend but no RetailGroup Credit card).
3. **Lifecycle stage** — new, growing, mature, or at-risk. Justify with \
   data points (tenure, recency, frequency).
4. **Top 3 cross-sell opportunities** — ranked by conversion likelihood. \
   For each, state the target entity, product/service, and the behavioural \
   signal that supports it.
5. **Risk factors** — any churn signals, declining spend, or satisfaction \
   concerns.

Be specific. Reference actual numbers from the profile. \
Output structured text, NOT JSON."""


ANALYZE_SIMILAR_CONVERSIONS_PROMPT = """\
You are a conversion-pattern analyst for RetailGroup Group Malaysia.

Below are lookalike customers who share similar behavioural profiles with \
the target customer and have SUCCESSFULLY converted on cross-sell campaigns.

**Target Customer Pattern Analysis:**
{pattern_analysis}

**Similar Customers Who Converted:**
{similar_customers}

**Your analysis MUST cover:**
1. **Common conversion paths** — which campaigns converted most among \
   lookalikes and what product/entity they targeted.
2. **Effective channels** — which communication channels (app_push, email, \
   sms, in_store, whatsapp) drove the highest conversion among lookalikes.
3. **Timing insights** — any patterns around day-of-week, time-of-month, \
   or seasonality of successful conversions.
4. **Content themes** — what messaging angles or offers resonated (cashback, \
   rewards, convenience, family, savings).
5. **Predicted conversion probability** — a rough percentage (0-100%) that \
   the target customer would convert on a similar campaign, with reasoning.

Be concise. Use bullet points. Reference specific campaign names and \
conversion rates where available."""


GENERATE_RECOMMENDATIONS_PROMPT = """\
You are the final recommendation engine for RetailGroup Group Malaysia's \
cross-sell system. Synthesize ALL upstream analysis into a structured \
JSON recommendation.

**Customer Profile:**
{customer_summary}

**Pattern Analysis:**
{pattern_analysis}

**Similar-Customer Conversion Analysis:**
{similar_conversion_analysis}

**Optimal Channel:** {optimal_channel}
**Channel Reasoning:** {channel_reasoning}

**Reranked Campaigns (best first):**
{reranked_campaigns}

**Reranked Content (best first):**
{reranked_content}

You MUST respond with a valid JSON object (no markdown, no code fences) \
with EXACTLY this structure:

{{
  "primary_campaign_id": "<campaign_id of the best campaign>",
  "primary_campaign_name": "<name of that campaign>",
  "content_asset_id": "<content_id of the best content piece>",
  "content_headline": "<headline of that content>",
  "recommended_channel": "{optimal_channel}",
  "reasoning": "<2-3 sentence executive summary: who is the customer, what to offer, via which channel, and why>",
  "expected_ltv_uplift": <estimated LTV increase in MYR, numeric>,
  "conversion_probability": <0.0-1.0 float>,
  "risk_factors": ["<risk1>", "<risk2>"],
  "fallback_campaign_id": "<campaign_id of next-best campaign or null>",
  "personalization_notes": "<brief guidance on name, tier, entity-specific messaging>"
}}

IMPORTANT:
- Use actual campaign_id and content_id values from the data above.
- expected_ltv_uplift should be a realistic MYR amount (50-5000 range).
- conversion_probability should align with the similar-customer analysis.
- Be specific to RetailGroup Malaysia. Reference RM amounts and entity names."""
