# Semantic routing checks

Checked with fresh agents on 2026-07-21. `Observed` records routing from
frontmatter only; no skill body or expected label was shown to the router.

## Baseline

| Prompt | Expected | Observed | Rationale |
| --- | --- | --- | --- |
| 帮我把这台富士 XS10 挂到闲鱼卖掉。 | INVOKE | INVOKE | Explicit personal Xianyu sale. |
| 我想清掉家里的闲置，你看照片帮我定价写文案。 | INVOKE | INVOKE | Personal idle-item selling workflow. |
| 这部旧手机在闲鱼大概能卖多少？ | INVOKE | INVOKE | Xianyu seller-side pricing. |
| 帮我把这条闲鱼宝贝改价到 1800。 | INVOKE | INVOKE | Existing-listing price edit. |
| 我闲鱼上这台相机三天没动静，看看标题和主图要不要改。 | INVOKE | INVOKE | Seller-side listing optimization. |
| Sell my used lens on Goofish and verify the live listing. | INVOKE | INVOKE | Goofish publication and verification. |
| 去闲鱼帮我买一台便宜的 XS10。 | DO_NOT_INVOKE | DO_NOT_INVOKE | Buyer request. |
| 帮我批量采集闲鱼 5000 条相机价格做数据集。 | DO_NOT_INVOKE | DO_NOT_INVOKE | Bulk scraping. |
| 我是闲鱼商家，给店里 200 个 SKU 批量上新。 | DO_NOT_INVOKE | DO_NOT_INVOKE | Merchant bulk operation. |
| 帮我把这台相机发到转转。 | DO_NOT_INVOKE | DO_NOT_INVOKE | Different marketplace. |
| 这台相机二手值多少钱？ | AMBIGUOUS | AMBIGUOUS | Xianyu intent is missing. |
| 帮我写一个二手相机文案。 | AMBIGUOUS | AMBIGUOUS | Platform and selling workflow are unclear. |

## Held-out retest

The first held-out pass over-invoked prompts 8 and 9. The description was
revised to require clear personal-seller intent; a new agent then produced the
results below.

| Prompt | Expected | Observed | Rationale |
| --- | --- | --- | --- |
| 我准备把自用两年的富士镜头挂闲鱼，照片都在这里，请帮我查同款价格、定价并写发布文案。 | INVOKE | INVOKE | Explicit personal Xianyu sale. |
| Please lower my Goofish listing for the used iPad from ¥2,600 to ¥2,450 after I confirm. | INVOKE | INVOKE | Seller-owned Goofish price edit. |
| 这条闲鱼发布三天了，帮我持续看浏览量和想要数，数据没起色时提醒我怎么优化。 | INVOKE | INVOKE | Monitoring and optimization. |
| 帮我在闲鱼找一台成色好的二手 Switch，预算 1500 元以内。 | DO_NOT_INVOKE | DO_NOT_INVOKE | Buyer request. |
| Can you draft an eBay listing for my old mechanical keyboard? | DO_NOT_INVOKE | DO_NOT_INVOKE | Different marketplace. |
| 我有 300 个同款手机壳，想批量铺货到闲鱼店铺并自动改价。 | DO_NOT_INVOKE | DO_NOT_INVOKE | Merchant bulk operation. |
| 这台用了三年的相机大概还能卖多少钱？ | AMBIGUOUS | AMBIGUOUS | Xianyu intent is missing. |
| This Goofish listing seems overpriced—can you check comparable listings and tell me a fair number? | AMBIGUOUS | AMBIGUOUS | Buyer versus seller role is unclear. |
| 帮我优化一下闲鱼上的五个商品，让它们更容易成交。 | AMBIGUOUS | AMBIGUOUS | Personal versus commercial scope is unclear. |
