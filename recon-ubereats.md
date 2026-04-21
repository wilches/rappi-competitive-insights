# UberEats MX recon

## Restaurant feed endpoint
URL: Not identified yet from the provided captures
Method: Not confirmed
How coordinates are sent: Not confirmed for the restaurant feed endpoint. In the observed store endpoint, location is sent in request headers using `x-uber-device-location-latitude`, `x-uber-device-location-longitude`, `x-uber-target-location-latitude`, and `x-uber-target-location-longitude`.
Auth headers required: Not confirmed for the feed endpoint. Observed Uber Eats store requests included cookie/session context and headers such as `x-csrf-token`, `x-uber-session-id`, and `x-uber-ciid`.
Response shape (where are restaurants in the JSON tree): Not identified yet from the provided data.

## Store menu endpoint
*Observed on the Uber Eats MX McDonald's store page.*

* **URL:** `https://www.ubereats.com/_p/api/getStoreV1?localeCode=mx`
* **Method:** `POST`
* **How store ID is passed:** In the JSON request body as `storeUuid`
* **Observed request payload:** `{"storeUuid":"a08108e0-594d-4c9e-a2a0-e3a90be971b1","diningMode":"DELIVERY","time":{"asap":true},"cbType":"EATER_ENDORSED"}`
* **How coordinates are sent:** In request headers including `x-uber-device-location-latitude`, `x-uber-device-location-longitude`, `x-uber-target-location-latitude`, and `x-uber-target-location-longitude`
* **Auth/session headers observed:** Cookies/session context plus headers such as `x-csrf-token`, `x-uber-session-id`, and `x-uber-ciid`
*   Observed request payload:
```json
{
  "storeUuid": "a08108e0-594d-4c9e-a2a0-e3a90be971b1",
  "diningMode": "DELIVERY",
  "time": {
    "asap": true
  },
  "cbType": "EATER_ENDORSED"
}

How coordinates are sent: In request headers including:

x-uber-device-location-latitude
x-uber-device-location-longitude
x-uber-target-location-latitude
x-uber-target-location-longitude
Auth/session headers observed:

Cookie/session context present
x-csrf-token
x-uber-session-id
x-uber-ciid
Response shape (where are products + prices):

Top-level status field: status
Main store object: data
Store metadata appears directly under data, e.g.:
title
uuid
slug
location
currencyCode
isOrderable
etaRange
rating
hours
categories
Menu section list appears in data.sections[]
A schema/SEO menu representation appears inside data.metaJson
In data.metaJson, menu sections are under hasMenu.hasMenuSection[]
In data.metaJson, menu items are under hasMenu.hasMenuSection[].hasMenuItem[]
In data.metaJson, prices appear under hasMenu.hasMenuSection[].hasMenuItem[].offers.price
Observed store metadata
Examples from the response:

data.title: "McDonald's (Plaza Galerías)"
data.uuid: "a08108e0-594d-4c9e-a2a0-e3a90be971b1"
data.slug: "mcdonalds-plaza-galerias"
data.citySlug: "mexico-city"
data.currencyCode: "MXN"
data.isOrderable: true
data.isOpen: true
Observed ETA / rating / distance fields
data.etaRange.text: "14-30 min"
data.modalityInfo.modalityOptions[].subtitle: "14 min"
data.rating.ratingValue: 4.5
data.rating.reviewCount: "15000+"
data.distanceBadge.text: "1.6 km"
Observed menu section fields
From data.sections[]:

title
subtitle
uuid
subsectionUuids
isTop
isOnSale
Example:

data.sections[0].title: "Menú Regular"
data.sections[0].subtitle: "12:00 PM – 9:45 PM"
Observed menu item / price format
In the schema menu under data.metaJson:

section name: hasMenu.hasMenuSection[].name
item name: hasMenu.hasMenuSection[].hasMenuItem[].name
description: hasMenu.hasMenuSection[].hasMenuItem[].description
price: hasMenu.hasMenuSection[].hasMenuItem[].offers.price
currency: hasMenu.hasMenuSection[].hasMenuItem[].offers.priceCurrency
Example:

Section: "Mc para Todos"
Item: "McTrío mediano McPollo"
Price: "99.00"
Currency: "MXN"
Notes
Visible promo format:

Delivery promo/free-shipping-style info appears under data.modalityInfo.modalityOptions[]
Example observed text: "Costo de envío a MXN0" with subtitle "nuevos usuarios"
Store-level promotion flags also appear as:
hasStorePromotion
promotion
suggestedPromotion
ETA format:

ETA range shown in data.etaRange.text, e.g. "14-30 min"
A shorter ETA also appears in data.modalityInfo.modalityOptions[].subtitle, e.g. "14 min"
Anything weird:

Endpoint uses POST for fetching store/menu data
Store is identified by storeUuid in the body, not the URL path
Coordinates are sent via custom headers rather than only in the request body
The response includes both UI-oriented store data and an embedded schema/SEO representation in data.metaJson
The schema JSON contains a very complete menu representation with sections, items, and prices
data.sections[] references subsectionUuids, but the provided snippet did not show populated subsection/item maps
Response includes rich metadata beyond menu data, including hours, distance, ratings, location, and FAQ/SEO content

## Saved cURL examples
curl 'https://www.ubereats.com/_p/api/getStoreV1?localeCode=mx' \
  -H 'accept: */*' \
  -H 'accept-language: en-US,en;q=0.9' \
  -H 'content-type: application/json' \
  -b '__cf_bm=XN_n5MpoJbeUVrfbJfnDOQiM3IBunJBijxdT4.I_FBQ-1776735279-1.0.1.1-MZqvm.wh5ypWBWPfW4qlTV5XY0pPfWeoREJVP9lX8c9Mx1lmYz4xUQK5jceKy5dtxsBwoudQO3QzwUm0piZ_XMC2bhtu5yBOuhHfBqBanYI; uev2.id.session_v2=e5042ca1-3ea5-43da-9624-151aeac83a1e; uev2.ts.session_v2=1776735280576; uev2.id.xp=40ab2ddd-722a-4270-859d-190842d27bf6; dId=e4fa0283-250a-473f-ab88-bbe42beade26; uev2.id.session=578ea1b6-daca-4955-b0c4-c7a617940bb8; uev2.ts.session=1776735280580; _ua={"session_id":"3b64851f-e7ab-496d-8e30-9c0fc71d8bc4","session_time_ms":1776735280600}; marketing_vistor_id=d52bcb1a-872f-47a0-95eb-c065a2e6d9ec; jwt-session=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7InNsYXRlLWV4cGlyZXMtYXQiOjE3NzY3MzcwODA2MDB9LCJpYXQiOjE3NzY3MzUyODAsImV4cCI6MTc3NjgyMTY4MH0.ZSkw0Y0JO4ziNexr5YrHQQhHc3zGToVGHTKyrgvks-o; cf_clearance=TEemwSautmms2iUyHN9SwRas0uKp3kYiNEuZOYVOZG4-1776735283-1.2.1.1-eKu7ZKDjFyeDs3CrdJ1vvy7s.0ydoBNHQBIeKELhRS0Ua7mb9TVam6koe.o1pokTQBwxUBgf.dAJay.Mn8rNuC02oV3K9GF1okXWOPqUVYKmN12TypDeuFf5BgLTwQ7yS_j9APcklVBEKR8ha9pWonAFHev_CR.pk3nwhwNlgzh3OAzpoQcRryR6U.zJk.jekZ2jB9Hu_9I4O4dTWi5GBpEgxL1FDQDkOTNKQBDI7K4vg8n6BMAVT.m.zc48xFBShlue1IAlX1C1obFqKuwEvxpaHmz0EQ49FEvt7gM.kT_0uxBHVacIDN5qmlGI8ochkL8r5hYm.ghBn6USGJbBlg; uev2.loc=%7B%22address%22%3A%7B%22address1%22%3A%22Av.%20Pdte.%20Masaryk%20111%22%2C%22address2%22%3A%22Chapultepec%20Morales%2C%20Polanco%20III%20Secc%2C%20Miguel%20Hidalgo%2C%2011560%20Ciudad%20de%20M%C3%A9xico%2C%20CDMX%22%2C%22aptOrSuite%22%3A%22%22%2C%22eaterFormattedAddress%22%3A%22Av.%20Pdte.%20Masaryk%20111%2C%20Chapultepec%20Morales%2C%20Polanco%20III%20Secc%2C%20Miguel%20Hidalgo%2C%2011560%20Ciudad%20de%20M%C3%A9xico%2C%20CDMX%2C%20M%C3%A9xico%22%2C%22subtitle%22%3A%22Chapultepec%20Morales%2C%20Polanco%20III%20Secc%2C%20Miguel%20Hidalgo%2C%2011560%20Ciudad%20de%20M%C3%A9xico%2C%20CDMX%22%2C%22title%22%3A%22Av.%20Pdte.%20Masaryk%20111%22%2C%22uuid%22%3A%22%22%7D%2C%22latitude%22%3A19.4319472%2C%22longitude%22%3A-99.1860116%2C%22reference%22%3A%22ChIJUcGuPqv40YURd8lPVyuIurI%22%2C%22referenceType%22%3A%22google_places%22%2C%22type%22%3A%22google_places%22%2C%22addressComponents%22%3A%7B%22city%22%3A%22M%C3%A9xico%20D.F.%22%2C%22countryCode%22%3A%22MX%22%2C%22firstLevelSubdivisionCode%22%3A%22CDMX%22%2C%22postalCode%22%3A%2211560%22%7D%2C%22categories%22%3A%5B%22address_point%22%5D%2C%22originType%22%3A%22user_autocomplete%22%2C%22source%22%3A%22manual_auto_complete%22%2C%22userState%22%3A%22Unknown%22%2C%22residenceType%22%3A%22%22%7D; mp_adec770be288b16d9008c964acfba5c2_mixpanel=%7B%22distinct_id%22%3A%20%22d52bcb1a-872f-47a0-95eb-c065a2e6d9ec%22%2C%22%24device_id%22%3A%20%2219dadaceaa9255-0e04f0a6404bcd-26061e51-144000-19dadaceaaaf50%22%2C%22%24initial_referrer%22%3A%20%22%24direct%22%2C%22%24initial_referring_domain%22%3A%20%22%24direct%22%2C%22%24user_id%22%3A%20%22d52bcb1a-872f-47a0-95eb-c065a2e6d9ec%22%7D; g_state={"i_l":0,"i_ll":1776735461195,"i_b":"voAwzIJQjKX/qJkepag13whNcElgTQ39LQhwx2XtI3s","i_e":{"enable_itp_optimization":21},"i_et":1776735324020}; uev2.embed_theme_preference=light; u-cookie-prefs=eyJ2ZXJzaW9uIjoxMDAsImRhdGUiOjE3NzY3MzU0NjgxMjcsImNvb2tpZUNhdGVnb3JpZXMiOlsiYWxsIl0sImltcGxpY2l0IjpmYWxzZX0%3D; uev2.gg=true; utag_main__sn=1; utag_main_ses_id=1776735469596%3Bexp-session; utag_main__pn=1%3Bexp-session; utm_medium=undefined; utm_source=undefined; _scid=A6uRV6cqWcx9dlH8RQNpv-OwXdxRB2p9; _scid_r=A6uRV6cqWcx9dlH8RQNpv-OwXdxRB2p9; utag_main__ss=0%3Bexp-session; _userUuid=; _gcl_au=1.1.993145419.1776735474; _yjsu_yjad=1776735477.42af7343-7c61-4d6a-87a4-7a6f3a4625ae; utag_main__se=6%3Bexp-session; utag_main__st=1776737278054%3Bexp-session; _twpid=tw.1776735482123.671015270164020206; _uetsid=bff7c3a03d2211f1856553b890a800d7; _uetvid=bff811503d2211f18611a97ebff30224; _fbp=fb.1.1776735488834.987248835197021471; _ga=GA1.1.1947210399.1776735491; _ga_P1RM71MPFP=GS2.1.s1776735490$o1$g1$t1776735490$j60$l0$h0; _tt_enable_cookie=1; _ttp=01KPPV07T2XG5DEKJTNMF2WP5Y_.tt.1; _clck=1970etp%5E2%5Eg5e%5E0%5E2302; _clsk=p9xgva%5E1776735513222%5E1%5E0%5Eb.clarity.ms%2Fcollect; ttcsid=1776735493961::_QFHYpLUuc1_5c1Dc5Sy.1.1776735859008.0::1.-37688.0::365019.1.388.202::362782.64.34; ttcsid_C69TD6PO8QD6LKH42DTG=1776735493960::rNFVjCaP-SBm5OgA8jYt.1.1776735859008.1' \
  -H 'origin: https://www.ubereats.com' \
  -H 'priority: u=1, i' \
  -H 'referer: https://www.ubereats.com/mx/store/mcdonalds-plaza-galerias/oIEI4FlNTJ6ioOOpC-lxsQ?surfaceName=' \
  -H 'sec-ch-prefers-color-scheme: light' \
  -H 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-origin' \
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -H 'x-csrf-token: x' \
  -H 'x-uber-ciid: 187d5405-4aea-42bc-9c8c-d34c2d1c4a51' \
  -H 'x-uber-client-gitref: 13f5eccf9f10070915fc17f70be4f2b0c7a5e271' \
  -H 'x-uber-device-location-latitude: 19.4319472' \
  -H 'x-uber-device-location-longitude: -99.1860116' \
  -H 'x-uber-request-id: 9c0c2d18-ac9c-4b0a-9439-9b9bd9332cb8' \
  -H 'x-uber-session-id: 578ea1b6-daca-4955-b0c4-c7a617940bb8' \
  -H 'x-uber-target-location-latitude: 19.4319472' \
  -H 'x-uber-target-location-longitude: -99.1860116' \
  --data-raw '{"storeUuid":"a08108e0-594d-4c9e-a2a0-e3a90be971b1","diningMode":"DELIVERY","time":{"asap":true},"cbType":"EATER_ENDORSED"}'
