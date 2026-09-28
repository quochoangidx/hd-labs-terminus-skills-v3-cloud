# SUBMISSION — tbrain-supplier-rebate-settlement

- Task: Repair a distributor's quarterly supplier-rebate settlement package so each account's statement (purchases, returns, tier and volume rebate, growth bonus, price protection, chargebacks, paid and carried amounts) follows the agreement's rebate schedule.
- Category: Operations / Supply chain
- ZIP: `workspace/submissions/tbrain-supplier-rebate-settlement.zip` (sha256 fcf8bdf41177d97dd7d83c4d2c7289d7f35d68d42be9b04e96b5116a450a1bcf)

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent counts a carton shipment, a purchase line of 12 units or more, toward the quarter it is received in, the fourth day after its invoice date, so freight invoiced in a quarter's last days moves into the next one, +2
Agent credits returns taken back in the quarter at their value less 40 cents a unit instead of the package's 25 cents, +2
Agent picks the tier on net purchases after returns, reaches a tier when net purchases are at or above its threshold, and gives no tier to net purchases below nought, +2
Agent rounds the volume rebate to the nearest cent with an exact half going up, rather than truncating it, +2
Agent pays the growth bonus as 200 basis points of the increase over last year's net purchases, only at 110 per cent or more of a positive prior, not on all net purchases, +2
Agent carries a settlement below 25,000 cents whole to the next quarter and pays one of 25,000 cents or more, where the package used 5,000, +2
Agent keeps a loose-unit line of fewer than 12 units counting toward the quarter of its invoice date while moving carton shipments to their receipt day, +3
Agent keeps a price notice cutting less than 250 cents a unit on today's credit, dropped below 5,000 cents and paid in full otherwise, while the minimum settlement becomes 25,000, +3
Agent keeps a below-cost sale less than 100 cents under cost on today's chargeback, skipped below 25 cents a unit and paid otherwise, while the return handling charge becomes 40 cents, +3
Agent leaves /app/tools/rebate_run.py byte-for-byte as shipped and prints every account in job order with exactly the README's twelve integer figures, +1
Agent adds four transit days to every purchase line, loose units included, -3
Agent raises the shared small_credit figure in rates.py to 25,000 so tidy-up notices between 5,000 and 24,999 cents lose their credit, -3
Agent raises the shared unit_handling figure in rates.py to 40 so price-match sales 25 to 39 cents under cost lose their chargeback, -3
Agent pays nothing for a tidy-up notice or a price-match sale, reading price protection and chargebacks as limited to price drops and contract sales, -2
Agent edits the rebate schedule or hardcodes settlement figures for particular accounts instead of repairing the package, -5
