"""Seed campaigns and content assets with full targeting, offer, performance.by_channel."""

import asyncio
import random
from datetime import datetime, timedelta

from pymongo import AsyncMongoClient

from backend.config import settings
from backend.seed.helpers import CAMPAIGN_TYPES, ENTITIES, SEGMENTS, TIERS
from backend.services.embedding_service import embed_batch

EMBED_BATCH = 128
NOW = datetime(2026, 4, 13)

CAMPAIGN_TEMPLATES = [
    {"name": "RetailGroup Credit Card Cashback Fiesta", "type": "cross_sell", "entity": "RetailGroup Credit",
     "description": "Get up to 10% cashback on all RetailGroup retail purchases with RetailGroup Credit Card. Target retail-only customers for credit card acquisition.",
     "offer_product": "RetailGroup Credit Card", "offer_cta": "Apply Now", "offer_value_prop": "10% cashback on all RetailGroup purchases"},
    {"name": "RetailGroup Bank Savings Booster", "type": "cross_sell", "entity": "RetailGroup Bank",
     "description": "Open an RetailGroup Bank savings account and earn 4.5% p.a. for the first 6 months.",
     "offer_product": "RetailGroup Bank Savings", "offer_cta": "Open Account", "offer_value_prop": "4.5% p.a. for 6 months"},
    {"name": "Tri-Entity Loyalty Accelerator", "type": "upsell", "entity": "All",
     "description": "Earn 3x points across all RetailGroup entities. Target dual-entity customers to become tri-entity.",
     "offer_product": "Loyalty Program", "offer_cta": "Activate Now", "offer_value_prop": "3x points across all entities"},
    {"name": "Gold Tier Fast-Track", "type": "loyalty_upgrade", "entity": "All",
     "description": "Spend RM5,000 in 3 months to earn Gold tier status with exclusive benefits.",
     "offer_product": "Gold Tier", "offer_cta": "Start Challenge", "offer_value_prop": "Gold status with priority checkout"},
    {"name": "Win Back Premium Customers", "type": "reactivation", "entity": "RetailGroup Co",
     "description": "Personal RM50 voucher for Gold/Platinum customers who haven't visited in 30+ days.",
     "offer_product": "RM50 Voucher", "offer_cta": "Claim Offer", "offer_value_prop": "RM50 exclusive voucher"},
    {"name": "RetailGroup Credit Personal Loan", "type": "cross_sell", "entity": "RetailGroup Credit",
     "description": "Pre-approved personal loan up to RM50,000 at competitive rates.",
     "offer_product": "Personal Loan", "offer_cta": "Apply Now", "offer_value_prop": "Pre-approved up to RM50,000"},
    {"name": "RetailGroup Bank Fixed Deposit Promo", "type": "cross_sell", "entity": "RetailGroup Bank",
     "description": "Premium FD rate of 4.8% p.a. for 12-month placement.",
     "offer_product": "Fixed Deposit", "offer_cta": "Place Now", "offer_value_prop": "4.8% p.a. for 12 months"},
    {"name": "Family Bundle Electronics", "type": "upsell", "entity": "RetailGroup Co",
     "description": "Bundle pricing on electronics for families: buy laptop + tablet combo and save 20%.",
     "offer_product": "Electronics Bundle", "offer_cta": "Shop Now", "offer_value_prop": "Save 20% on combo"},
    {"name": "Raya Festival Mega Sale", "type": "upsell", "entity": "RetailGroup Co",
     "description": "Up to 70% off during Hari Raya season.",
     "offer_product": "Hari Raya Collection", "offer_cta": "Shop Now", "offer_value_prop": "Up to 70% off"},
    {"name": "CNY Golden Deals", "type": "upsell", "entity": "RetailGroup Co",
     "description": "Chinese New Year exclusive deals on premium groceries, hampers, and electronics.",
     "offer_product": "CNY Collection", "offer_cta": "Shop Now", "offer_value_prop": "Exclusive CNY deals"},
    {"name": "Deepavali Sparkle Campaign", "type": "upsell", "entity": "RetailGroup Co",
     "description": "Deepavali specials on fashion, jewelry, and sweets.",
     "offer_product": "Deepavali Collection", "offer_cta": "Shop Now", "offer_value_prop": "Festive specials"},
    {"name": "RetailGroup Member Gets Member", "type": "retention", "entity": "All",
     "description": "Refer a friend to any RetailGroup entity and both earn 500 bonus points.",
     "offer_product": "Referral Bonus", "offer_cta": "Refer Now", "offer_value_prop": "500 bonus points each"},
    {"name": "Smart Grocery Saver", "type": "retention", "entity": "RetailGroup Co",
     "description": "Weekly personalized grocery deals based on purchase history.",
     "offer_product": "Personalized Deals", "offer_cta": "View Deals", "offer_value_prop": "Tailored weekly savings"},
    {"name": "RetailGroup Credit Balance Transfer", "type": "cross_sell", "entity": "RetailGroup Credit",
     "description": "Transfer balances from other credit cards at 0% interest for 12 months.",
     "offer_product": "Balance Transfer", "offer_cta": "Transfer Now", "offer_value_prop": "0% interest for 12 months"},
    {"name": "RetailGroup Bank Digital Onboarding", "type": "cross_sell", "entity": "RetailGroup Bank",
     "description": "Open account in 5 minutes, get RM30 welcome bonus.",
     "offer_product": "Digital Account", "offer_cta": "Sign Up", "offer_value_prop": "RM30 welcome bonus"},
    {"name": "Platinum Exclusive Wine & Dine", "type": "retention", "entity": "All",
     "description": "Quarterly exclusive dining experiences for Platinum members.",
     "offer_product": "Dining Experience", "offer_cta": "RSVP Now", "offer_value_prop": "Exclusive quarterly dining"},
    {"name": "Student First Card", "type": "cross_sell", "entity": "RetailGroup Credit",
     "description": "First credit card for university students with RM1,000 limit.",
     "offer_product": "Student Card", "offer_cta": "Apply Now", "offer_value_prop": "RM1,000 limit, 0% annual fee"},
    {"name": "SME Business Banking", "type": "cross_sell", "entity": "RetailGroup Bank",
     "description": "Business account package for small merchants.",
     "offer_product": "Business Account", "offer_cta": "Get Started", "offer_value_prop": "Complete business banking"},
    {"name": "Insurance Cross-sell Bundle", "type": "cross_sell", "entity": "RetailGroup Credit",
     "description": "Travel and personal accident insurance bundled with credit card.",
     "offer_product": "Insurance Bundle", "offer_cta": "Add Coverage", "offer_value_prop": "Bundled insurance coverage"},
    {"name": "Birthday Month Double Points", "type": "retention", "entity": "All",
     "description": "Earn 2x loyalty points on all purchases during birthday month.",
     "offer_product": "Double Points", "offer_cta": "Activate", "offer_value_prop": "2x points all month"},
    {"name": "Health & Wellness Rewards", "type": "upsell", "entity": "RetailGroup Co",
     "description": "Extra points on health supplements, organic produce, and fitness accessories.",
     "offer_product": "Wellness Collection", "offer_cta": "Shop Now", "offer_value_prop": "Bonus points on wellness"},
    {"name": "RetailGroup Pay Digital Wallet Promo", "type": "cross_sell", "entity": "RetailGroup Bank",
     "description": "Link RetailGroup Pay to RetailGroup Bank account and get RM20 cashback.",
     "offer_product": "RetailGroup Pay", "offer_cta": "Link Now", "offer_value_prop": "RM20 cashback on first 5 txns"},
    {"name": "Premium Card Upgrade", "type": "loyalty_upgrade", "entity": "RetailGroup Credit",
     "description": "Upgrade to RetailGroup Credit Visa Signature with complimentary airport lounge access.",
     "offer_product": "Visa Signature", "offer_cta": "Upgrade Now", "offer_value_prop": "Airport lounge + 3x overseas points"},
    {"name": "Grocery Subscription Box", "type": "retention", "entity": "RetailGroup Co",
     "description": "Monthly curated grocery box delivered to doorstep at 15% discount.",
     "offer_product": "Subscription Box", "offer_cta": "Subscribe", "offer_value_prop": "15% off monthly delivery"},
    {"name": "Back-to-School Bundle", "type": "upsell", "entity": "RetailGroup Co",
     "description": "School supplies, uniforms, and stationery bundles in January.",
     "offer_product": "School Bundle", "offer_cta": "Shop Now", "offer_value_prop": "Complete school bundles"},
    {"name": "Year-End Tax Relief", "type": "cross_sell", "entity": "RetailGroup Bank",
     "description": "PRS and unit trust investments qualifying for tax relief.",
     "offer_product": "Investment Products", "offer_cta": "Invest Now", "offer_value_prop": "Tax relief eligible"},
    {"name": "E-Commerce Integration", "type": "cross_sell", "entity": "RetailGroup Co",
     "description": "Shop online at RetailGroup.com.my with same loyalty points.",
     "offer_product": "Online Shopping", "offer_cta": "Shop Online", "offer_value_prop": "Same points online & offline"},
    {"name": "RetailGroup Credit BNPL", "type": "cross_sell", "entity": "RetailGroup Credit",
     "description": "Buy Now Pay Later on purchases above RM500 at 0% installment.",
     "offer_product": "BNPL", "offer_cta": "Activate", "offer_value_prop": "0% installment for 6 months"},
    {"name": "Churn Prevention Offer", "type": "reactivation", "entity": "All",
     "description": "Exclusive RM30 voucher + bonus points for high churn risk customers.",
     "offer_product": "Retention Voucher", "offer_cta": "Claim Now", "offer_value_prop": "RM30 voucher + bonus points"},
    {"name": "Weekend Warrior Deals", "type": "retention", "entity": "RetailGroup Co",
     "description": "Special weekend-only flash deals on popular items.",
     "offer_product": "Flash Deals", "offer_cta": "View Deals", "offer_value_prop": "Weekend-only flash prices"},
]

CHANNELS = ["email", "sms", "push_notification", "in_app", "whatsapp"]
PERSONAS = ["value_seeker", "premium_shopper", "young_professional", "family_oriented", "tech_savvy", "health_conscious"]
LANGUAGES = ["en", "ms", "zh", "ta"]
TONES = ["friendly", "professional", "urgent", "aspirational", "warm"]

BEST_SEND_TIME_OPTIONS = ["morning", "afternoon", "evening", "night"]
BEST_SEND_TIME_WEIGHTS = [0.15, 0.2, 0.4, 0.25]
BEST_SEND_DAY_OPTIONS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
# Friday/Saturday weighted higher than mid-week
BEST_SEND_DAY_WEIGHTS = [0.09, 0.09, 0.09, 0.09, 0.23, 0.23, 0.18]
DEMOGRAPHIC_POOL = ["18-24", "25-34", "35-44", "45-54", "55+", "urban", "suburban", "family"]


def _channel_performance(channel: str) -> dict:
    base_open = {"email": 0.25, "sms": 0.45, "push_notification": 0.30, "in_app": 0.55, "whatsapp": 0.60}
    open_rate = base_open.get(channel, 0.30) * random.uniform(0.7, 1.3)
    sent = random.randint(500, 10000)
    opened = int(sent * open_rate)
    clicked = int(opened * random.uniform(0.15, 0.45))
    converted = int(clicked * random.uniform(0.05, 0.25))
    return {
        "channel": channel,
        "sent": sent,
        "opened": opened,
        "clicked": clicked,
        "converted": converted,
        "open_rate": round(opened / sent, 3) if sent > 0 else 0,
        "ctr": round(clicked / opened, 3) if opened > 0 else 0,
        "conversion_rate": round(converted / clicked, 3) if clicked > 0 else 0,
    }


def generate_campaigns() -> list[dict]:
    campaigns = []
    for i, tmpl in enumerate(CAMPAIGN_TEMPLATES):
        target_segments = random.sample(SEGMENTS, k=random.randint(2, 5))
        target_tiers = random.sample(TIERS, k=random.randint(1, 4))
        start = NOW - timedelta(days=random.randint(0, 90))
        end = start + timedelta(days=random.randint(30, 180))

        by_channel = [_channel_performance(ch) for ch in random.sample(CHANNELS, k=random.randint(2, 5))]
        total_converted = sum(ch["converted"] for ch in by_channel)
        total_sent = sum(ch["sent"] for ch in by_channel)

        behavior_criteria = random.sample([
            "high_spend_last_90d", "no_credit_product", "no_bank_account",
            "dormant_30d", "tier_upgrade_eligible", "birthday_month",
            "category_affinity_electronics", "high_loyalty_points",
        ], k=random.randint(1, 3))
        budget = round(random.uniform(10000, 500000), 2)
        status = "active" if end > NOW else "completed"
        conv_rate = round(total_converted / total_sent, 3) if total_sent > 0 else 0
        total_rev = round(total_converted * random.uniform(50, 500), 2)

        seg_str = ", ".join(target_segments)
        tier_str = ", ".join(target_tiers)
        behavior_str = ", ".join(b.replace("_", " ") for b in behavior_criteria)
        channels_str = ", ".join(ch["channel"].replace("_", " ") for ch in by_channel)

        embedding_text = (
            f"{tmpl['name']}: {tmpl['type']} campaign for {tmpl['entity']}. {tmpl['description']} "
            f"Targets {seg_str} segments, {tier_str} tiers. "
            f"Behavior triggers: {behavior_str}. "
            f"Offer: {tmpl.get('offer_value_prop', '')} via {tmpl.get('offer_cta', 'Learn More')}. "
            f"Channels: {channels_str}. Status: {status}, budget RM{budget:,.0f}. "
            f"Conversion rate {conv_rate:.1%}, total revenue RM{total_rev:,.0f}."
        )

        campaigns.append({
            "campaign_id": f"CMP-{i+1:04d}",
            "name": tmpl["name"],
            "type": tmpl["type"],
            "entity": tmpl["entity"],
            "description": tmpl["description"],
            "targeting": {
                "segment_criteria": target_segments,
                "behavior_criteria": behavior_criteria,
                "estimated_audience_size": random.randint(1000, 15000),
                "threshold_id": f"THR-{i+1:04d}",
            },
            "offer": {
                "product": tmpl.get("offer_product", ""),
                "headline": tmpl["name"],
                "value_proposition": tmpl.get("offer_value_prop", ""),
                "terms": f"Valid {start.strftime('%d %b')} - {end.strftime('%d %b %Y')}. T&C apply.",
                "cta": tmpl.get("offer_cta", "Learn More"),
            },
            "content_assets": [],
            "target_segments": target_segments,
            "target_tiers": target_tiers,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "status": status,
            "budget_myr": budget,
            "performance": {
                "enrollment_count": total_sent,
                "conversion_rate": conv_rate,
                "total_revenue_myr": total_rev,
                "avg_ltv_uplift": round(random.uniform(50, 500), 2),
                "by_channel": by_channel,
            },
            "embedding": None,
            "embedding_text": embedding_text,
        })
    return campaigns


def generate_content_assets(campaigns: list[dict]) -> list[dict]:
    """Generate ~120 content assets linked to campaigns."""
    assets = []
    idx = 0
    for campaign in campaigns:
        n_assets = random.randint(3, 5)
        content_ids = []
        for _ in range(n_assets):
            idx += 1
            content_id = f"CNT-{idx:05d}"
            content_ids.append(content_id)
            channel = random.choice(CHANNELS)
            persona = random.choice(PERSONAS)
            language = random.choice(LANGUAGES)
            tone = random.choice(TONES)

            desc_snippet = campaign["description"][:100] + "..."
            body = "Hi {{customer_name}}, " + f"exclusive offer from {campaign['entity']}: {desc_snippet}"
            body_template = (
                "Hi {{customer_name}}, exclusive offer from {{entity}}: {{campaign_description}}"
            )
            best_send_time = random.choices(
                BEST_SEND_TIME_OPTIONS, weights=BEST_SEND_TIME_WEIGHTS, k=1
            )[0]
            best_send_day = random.choices(
                BEST_SEND_DAY_OPTIONS, weights=BEST_SEND_DAY_WEIGHTS, k=1
            )[0]
            opens = random.randint(100, 5000)
            clicks = random.randint(50, 2000)
            conversions = random.randint(5, 500)

            ctr = round(clicks / max(opens, 1), 3)
            conv_r = round(conversions / max(clicks, 1), 3)
            tgt_segs = ", ".join(random.sample(SEGMENTS, k=random.randint(1, 3)))
            tgt_tiers = ", ".join(random.sample(TIERS, k=random.randint(1, 3)))
            demos = ", ".join(random.sample(DEMOGRAPHIC_POOL, k=random.randint(1, 3)))

            embedding_text = (
                f"{campaign['name']} content for {channel.replace('_', ' ')} channel. "
                f"Campaign: {campaign['description'][:150]} "
                f"Persona: {persona.replace('_', ' ')}, tone: {tone}, language: {language}. "
                f"Offer: {campaign['offer']['value_proposition']}. CTA: {campaign['offer']['cta']}. "
                f"Best send {best_send_day} {best_send_time}. "
                f"Targeting {tgt_segs} segments, {tgt_tiers} tiers, {demos} demographics. "
                f"Performance: {ctr:.1%} CTR, {conv_r:.1%} conversion."
            )

            assets.append({
                "content_id": content_id,
                "campaign_id": campaign["campaign_id"],
                "campaign_name": campaign["name"],
                "channel": channel,
                "headline": f"{campaign['name']} - {channel.replace('_', ' ').title()}",
                "body": body,
                "body_template": body_template,
                "image_url": f"https://cdn.RetailCustomer360.demo/assets/{content_id.lower()}.jpg",
                "cta_deeplink": f"RetailCustomer360://campaigns/{campaign['campaign_id']}/enroll",
                "target_persona": persona,
                "language": language,
                "tone": tone,
                "cta": campaign["offer"]["cta"],
                "personalization_fields": [
                    {"field_name": "customer_name", "source": "unified_profile.name"},
                    {"field_name": "tier", "source": "tier"},
                    {"field_name": "points_balance", "source": "entity_profiles.RetailGroup_co.points_balance"},
                ],
                "performance_stats": {
                    "opens": opens,
                    "clicks": clicks,
                    "conversions": conversions,
                    "ctr": round(clicks / max(opens, 1), 3),
                    "conversion_rate": round(conversions / max(clicks, 1), 3),
                    "best_send_time": best_send_time,
                    "best_send_day": best_send_day,
                },
                "targeting_affinity": {
                    "segments": random.sample(SEGMENTS, k=random.randint(1, 3)),
                    "tiers": random.sample(TIERS, k=random.randint(1, 3)),
                    "entities": [campaign["entity"]],
                    "best_for_demographics": random.sample(
                        DEMOGRAPHIC_POOL, k=random.randint(1, 3)
                    ),
                },
                "best_send_time": best_send_time,
                "best_send_day": best_send_day,
                "avg_engagement_window_hours": round(random.uniform(1.0, 8.0), 1),
                "embedding": None,
                "embedding_text": embedding_text,
            })
            if idx >= 120:
                campaign["content_assets"] = content_ids
                return assets
        campaign["content_assets"] = content_ids
    return assets


async def seed_campaigns():
    print("Generating campaigns...")
    campaigns = generate_campaigns()

    print("Generating content assets...")
    content_assets = generate_content_assets(campaigns)

    # Embed campaigns (all 30)
    print("Embedding campaigns...")
    campaign_texts = [c["embedding_text"] for c in campaigns]
    campaign_embs = embed_batch(campaign_texts, batch_size=EMBED_BATCH)
    for i, emb in enumerate(campaign_embs):
        campaigns[i]["embedding"] = emb

    # Embed content assets (all ~120)
    print("Embedding content assets...")
    content_texts = [a["embedding_text"] for a in content_assets]
    content_embs = embed_batch(content_texts, batch_size=EMBED_BATCH)
    for i, emb in enumerate(content_embs):
        content_assets[i]["embedding"] = emb

    # Insert
    print("Inserting into MongoDB...")
    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]

    await db["campaigns"].drop()
    await db["content_assets"].drop()

    await db["campaigns"].insert_many(campaigns)
    await db["content_assets"].insert_many(content_assets)

    print(f"Seeded {len(campaigns)} campaigns and {len(content_assets)} content assets")
    await client.close()


if __name__ == "__main__":
    asyncio.run(seed_campaigns())
