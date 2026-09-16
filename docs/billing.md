# Billing & Entitlement Architecture

## Plans & Tiers

| Plan | Price | Monthly Chars | Fair-Use Limit | Cloning | Premium Voices | API |
|---|---|---|---|---|---|---|
| Free | $0/mo | 10,000 | 15,000 | No | No | No |
| Starter | $9/mo | 50,000 | 60,000 | No | No | Yes |
| Creator | $29/mo | 250,000 | 300,000 | Yes | Yes | Yes |
| Pro | $79/mo | 1,000,000 | 1,200,000 | Yes | Yes | Yes |
| Unlimited | $149/mo | 5,000,000 | 5,000,000 | Yes | Yes | Yes |

## Entitlement Rules
- Tier check: Free and Starter users cannot generate using `premium` or `ultra` voices without upgrading.
- Custom Voice check: Cloned voices are private by default and can only be used by their owner.
- Fair-Use Unlimited: "Unlimited" is enforced via fair-use policies and status tracking (`healthy`, `warning`, `throttled`) to prevent infinite compute abuse.
