# Rappi MX recon

## Restaurant feed endpoint
URL: Not identified yet from the provided capture
Method: Not confirmed
How coordinates are sent: Not confirmed for the restaurant listing/feed endpoint. A related store/menu request sends coordinates in the JSON body as `lat` and `lng`.
Auth headers required: Not confirmed for the feed endpoint, though observed requests in this session included `authorization` and `deviceid`.
Response shape (where are restaurants in the JSON tree): Not identified yet from the provided data.

## Store menu endpoint
URL: https://services.mxgrability.rappi.com/api/restaurant-bus/store/brand/id/706
Method: POST
How store ID is passed: In the URL path as `/brand/id/706`
How coordinates are sent: In the JSON request body as `lat` and `lng`
Observed request payload:
```json
{
  "is_prime": false,
  "lat": 19.43161,
  "lng": -99.18605,
  "store_type": "restaurant",
  "prime_config": {
    "unlimited_shipping": false
  }
}
Auth headers observed: authorization (Bearer token) and deviceid
Response shape (where are products + prices): Top-level JSON object containing store metadata. Menu sections are in corridors[], and products are in corridors[].products[]. Prices appear in price, real_price, discount_percentage, and discounts[].


## Notes
- Visible promo format:
  - Store-level promos appear in `discount_tags[]`
  - Fields observed include:
    - `id`
    - `type`
    - `tag`
    - `title`
    - `description`
    - `message`
    - `value`
    - `conditions`
    - `card_details`
    - `type_filter`
  - Example promo types observed:
    - `free_shipping`
    - `offer_by_product`
- ETA format:
  - Human-readable ETA appears in `eta`, e.g. `"12 min"`
  - Numeric/internal ETA appears in `eta_value`, e.g. `32`

- Anything weird:
  - The endpoint uses `POST` even though it appears to fetch/read store data.
  - Menu sections are named `corridors`, which is a non-obvious field name for categories.
  - The store can be available/open while individual products still have `is_available: false`.
  - Promotional pricing may be represented separately in `discounts[]`, so `price` is not always the fully discounted effective price.
  - Response compression observed: `content-encoding: zstd`
  - CORS headers are permissive, including `access-control-allow-origin: *`
  - Request passed through CloudFront; response headers included tracing/performance fields such as:
    - `x-rappi-request-execution-time`
    - `x-rappi-trace-id`
    - `server-timing`

## Saved cURL examples
curl 'https://services.mxgrability.rappi.com/api/restaurant-bus/store/brand/id/706' \
  -H 'accept: application/json' \
  -H 'accept-language: es-MX' \
  -H 'access-control-allow-headers: *' \
  -H 'access-control-allow-origin: *' \
  -H 'app-version: 1.161.2' \
  -H 'app-version-name: 1.161.2' \
  -H 'authorization: Bearer ft.gAAAAABp5rw_GwcamM5U0UEb3N5nKM6WQqiFIx4ulqOO_XH1J5_nRtZ9Z3dyp62s3Q_WYzJU1MWgVg1jMY32bxhr25gvjKVtqyCuV1tdawt5yxdwi7IW2Qr1tr7yN58lpYAdqHslyeMrrcxtNwlxN8XRLZzZ-t-ewF4j8SfNN0KSxo7nBmSrs_H9TBN1w_trIj44m5bMyGyYRcHmvM9QQUKfcbtt04qlBZ3eK9bIcGRYkVVyG-cMFamXKihnzIRDRsJ7uZhnO5wuSX6WyKwaOv272NRjqRNDagR1rlFzYoWT745Wp7xhKwySXCh6PmjMXxSxxjJGVyFisJaC68JJMhqJdvTRL0PFC20NsVw9lwqjFNbBQLem4InL8EkW632FPKenoZ7OVvWcBNueIkRdMbCRgNSPYlENtA==' \
  -H 'content-type: application/json; charset=UTF-8' \
  -H 'deviceid: c0709df4-3b5c-48eb-b49d-a3f532f0e52aR' \
  -H 'needappsflyerid: false' \
  -H 'origin: https://www.rappi.com.mx' \
  -H 'priority: u=1, i' \
  -H 'referer: https://www.rappi.com.mx/' \
  -H 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: cross-site' \
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  --data-raw '{"is_prime":false,"lat":19.43161,"lng":-99.18605,"store_type":"restaurant","prime_config":{"unlimited_shipping":false}}'
