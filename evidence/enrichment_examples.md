# Phase 2 Evidence — GenAI Entity Recognition, Vector Search & LLM Judge

_Captured: 2026-11-24 03:05:44 UTC_

Live end-to-end enrichment output on real transactions. Models: chat `databricks-claude-sonnet-5-5`, embeddings `databricks-gte-large-en`. Ground-truth `expected_*` columns are shown ONLY for verification and are never seen by the enrichment workflow.



**Summary:** 11/12 examples agreed with ground-truth decision on this curated sample. Full quantitative evaluation over all 400 held-out transactions is in [`evaluation_results.md`](evaluation_results.md).


---

## Example 1 — expected **MATCHED**, system decided **MATCHED** ✅

**Transaction** `T000023`  

**Raw descriptor:** `NOO HOUSE  LOC 5597  CHARLESTON SC`


**1) Extracted entities (GenAI):**

| payment_facilitator | merchant_name | city | state | store_identifier | order_identifier |
| --- | --- | --- | --- | --- | --- |
|  | Noo House | Charleston | SC | 5597 |  |


**2) Vector Search — top candidates (similarity):**

| similarity | merchant_id | merchant_name | city | state | category |
| --- | --- | --- | --- | --- | --- |
| 0.6738 | M00547 | Noodle House | Charleston | SC | Restaurant |
| 0.6712 | M00551 | Noodle House | San Francisco | CA | Restaurant |
| 0.669 | M00562 | Noodle House | Raleigh | NC | Restaurant |
| 0.6611 | M00563 | Noodle House | Providence | RI | Restaurant |
| 0.6514 | M00559 | Noodle House | Santa Fe | NM | Restaurant |
| 0.649 | M00560 | Noodle House | Fort Wayne | IN | Restaurant |
| 0.6251 | M00543 | Noodle House | Boulder | CO | Restaurant |
| 0.622 | M00565 | Noodle House | Indianapolis | IN | Restaurant |
| 0.6188 | M00552 | Noodle House | Little Rock | AR | Restaurant |
| 0.6184 | M00566 | Noodle House | Larchmont | NY | Restaurant |


**3) LLM judge decision:**

| decision | merchant_id | merchant_name | confidence | alternatives |
| --- | --- | --- | --- | --- |
| MATCHED | M00547 | Noodle House | 0.85 | M00562, M00551, M00563 |


> **Reason:** The descriptor 'NOO HOUSE' is a plausible truncation of 'Noodle House', and its location Charleston SC matches only candidate M00547. The other Noodle House candidates are in different cities and states, so the location separates them. The store identifier 5597 cannot be checked against the candidate data, so it is treated as unknown.


_Latency: 7560 ms · LLM calls: 2 · Ground truth: MATCHED / merchant M00547_


---

## Example 2 — expected **MATCHED**, system decided **MATCHED** ✅

**Transaction** `T000075`  

**Raw descriptor:** `GREEN LEAF SALADS / COLUMBUS`


**1) Extracted entities (GenAI):**

| payment_facilitator | merchant_name | city | state | store_identifier | order_identifier |
| --- | --- | --- | --- | --- | --- |
|  | Green Leaf Salads | Columbus |  |  |  |


**2) Vector Search — top candidates (similarity):**

| similarity | merchant_id | merchant_name | city | state | category |
| --- | --- | --- | --- | --- | --- |
| 0.8343 | M00454 | Green Leaf Salads | Columbus | OH | Restaurant |
| 0.7932 | M00502 | Green Leaf Salads | Eugene | OR | Restaurant |
| 0.7645 | M00484 | Green Leaf Salads | Fort Wayne | IN | Restaurant |
| 0.7639 | M00477 | Green Leaf Salads | Jacksonville | FL | Restaurant |
| 0.7606 | M00459 | Green Leaf Salads | Akron | OH | Restaurant |
| 0.755 | M00488 | Green Leaf Salads | Philadelphia | PA | Restaurant |
| 0.7542 | M00482 | Green Leaf Salads | Cleveland | OH | Restaurant |
| 0.754 | M00451 | Green Leaf Salads | Charleston | SC | Restaurant |
| 0.7529 | M00453 | Green Leaf Salads | Buffalo | NY | Restaurant |
| 0.7503 | M00494 | Green Leaf Salads | Rochester | NY | Restaurant |


**3) LLM judge decision:**

| decision | merchant_id | merchant_name | confidence | alternatives |
| --- | --- | --- | --- | --- |
| MATCHED | M00454 | Green Leaf Salads | 0.9 | M00459, M00482, M00484 |


> **Reason:** The descriptor names 'Green Leaf Salads' in Columbus. Exactly one candidate (M00454) is in Columbus (OH), and its name matches exactly. The other same-name candidates are in different cities (Eugene, Fort Wayne, Jacksonville, Akron, etc.), so the location rule disambiguates them. The missing state is treated as unknown, not as a conflict.


_Latency: 6084 ms · LLM calls: 2 · Ground truth: MATCHED / merchant M00454_


---

## Example 3 — expected **MATCHED**, system decided **AMBIGUOUS** ⚠️

**Transaction** `T000098`  

**Raw descriptor:** `HPAPYPAWSPETSUPPLIESSPOKANEWADJQ1PQV`


**1) Extracted entities (GenAI):**

| payment_facilitator | merchant_name | city | state | store_identifier | order_identifier |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |


**2) Vector Search — top candidates (similarity):**

| similarity | merchant_id | merchant_name | city | state | category |
| --- | --- | --- | --- | --- | --- |
| 0.5407 | M02028 | Happy Paws Pet Supplies | Trenton | NJ | Pet Store |
| 0.5386 | M01264 | GadgetWorld | Wichita | KS | Electronics |
| 0.5329 | M01242 | GadgetWorld | Plano | TX | Electronics |
| 0.5258 | M02008 | Happy Paws Pet Supplies | New Orleans | LA | Pet Store |
| 0.5224 | M01813 | PixelForge Studios | Pittsburgh | PA | Digital Services |
| 0.5212 | M01258 | GadgetWorld | Richmond | VA | Electronics |
| 0.5204 | M01304 | Wellness Pharmacy | Indianapolis | IN | Pharmacy |
| 0.5195 | M01650 | PeakFit Gym | Jacksonville | FL | Fitness |
| 0.5188 | M01823 | PixelForge Studios | Charleston | SC | Digital Services |
| 0.518 | M01732 | IronWorks Fitness | Scottsdale | AZ | Fitness |


**3) LLM judge decision:**

| decision | merchant_id | merchant_name | confidence | alternatives |
| --- | --- | --- | --- | --- |
| AMBIGUOUS |  |  | 0.0 | — |


> **Reason:** Judge error, routed to review: chat_json failed after 3 attempts: 'list' object has no attribute 'strip'


_Latency: 18431 ms · LLM calls: 2 · Ground truth: MATCHED / merchant M01978_


---

## Example 4 — expected **MATCHED**, system decided **MATCHED** ✅

**Transaction** `T000153`  

**Raw descriptor:** `SPEEDWAY MART / RENO NV`


**1) Extracted entities (GenAI):**

| payment_facilitator | merchant_name | city | state | store_identifier | order_identifier |
| --- | --- | --- | --- | --- | --- |
|  | Speedway Mart | Reno | NV |  |  |


**2) Vector Search — top candidates (similarity):**

| similarity | merchant_id | merchant_name | city | state | category |
| --- | --- | --- | --- | --- | --- |
| 0.8988 | M00894 | Speedway Mart | Reno | NV | Convenience Store |
| 0.7252 | M00875 | Speedway Mart | Boulder | CO | Convenience Store |
| 0.7244 | M00893 | Speedway Mart | Newark | NJ | Convenience Store |
| 0.7176 | M00879 | Speedway Mart | Oakland | CA | Convenience Store |
| 0.7136 | M00884 | Speedway Mart | Arlington | VA | Convenience Store |
| 0.7116 | M00878 | Speedway Mart | Spokane | WA | Convenience Store |
| 0.7035 | M00910 | Speedway Mart | San Francisco | CA | Convenience Store |
| 0.7028 | M00883 | Speedway Mart | Raleigh | NC | Convenience Store |
| 0.702 | M00921 | Speedway Mart | Sacramento | CA | Convenience Store |
| 0.7006 | M00916 | Speedway Mart | Santa Fe | NM | Convenience Store |


**3) LLM judge decision:**

| decision | merchant_id | merchant_name | confidence | alternatives |
| --- | --- | --- | --- | --- |
| MATCHED | M00894 | Speedway Mart | 0.96 | — |


> **Reason:** Descriptor name 'Speedway Mart' exactly matches candidate 1, and its city/state (Reno, NV) match the descriptor's location. All other 'Speedway Mart' candidates are in different cities/states, so the location disambiguates them.


_Latency: 3003 ms · LLM calls: 2 · Ground truth: MATCHED / merchant M00894_


---

## Example 5 — expected **MATCHED**, system decided **MATCHED** ✅

**Transaction** `T000176`  

**Raw descriptor:** `BUILDERS DEPOT  OAKLAND`


**1) Extracted entities (GenAI):**

| payment_facilitator | merchant_name | city | state | store_identifier | order_identifier |
| --- | --- | --- | --- | --- | --- |
|  | Builders Depot | Oakland |  |  |  |


**2) Vector Search — top candidates (similarity):**

| similarity | merchant_id | merchant_name | city | state | category |
| --- | --- | --- | --- | --- | --- |
| 0.8737 | M01491 | Builders Depot | Oakland | CA | Home Improvement |
| 0.7923 | M01505 | Builders Depot | San Francisco | CA | Home Improvement |
| 0.7404 | M01487 | Builders Depot | Pittsburgh | PA | Home Improvement |
| 0.7357 | M01495 | Builders Depot | Detroit | MI | Home Improvement |
| 0.7308 | M01528 | Builders Depot | Portland | OR | Home Improvement |
| 0.7237 | M01533 | Builders Depot | Tampa | FL | Home Improvement |
| 0.7232 | M01548 | Builders Depot | Rochester | NY | Home Improvement |
| 0.7228 | M01534 | Builders Depot | Spokane | WA | Home Improvement |
| 0.7213 | M01536 | Builders Depot | Long Beach | CA | Home Improvement |
| 0.7206 | M01501 | Builders Depot | San Jose | CA | Home Improvement |


**3) LLM judge decision:**

| decision | merchant_id | merchant_name | confidence | alternatives |
| --- | --- | --- | --- | --- |
| MATCHED | M01491 | Builders Depot | 0.93 | M01505, M01536, M01501 |


> **Reason:** Descriptor names Builders Depot in Oakland. Only candidate M01491 has that name in Oakland (CA). The other Builders Depot candidates are in different cities, so the location separates them.


_Latency: 2724 ms · LLM calls: 2 · Ground truth: MATCHED / merchant M01491_


---

## Example 6 — expected **AMBIGUOUS**, system decided **AMBIGUOUS** ✅

**Transaction** `T000111`  

**Raw descriptor:** `AUTOCARE SERVICE CENTE  #2718`


**1) Extracted entities (GenAI):**

| payment_facilitator | merchant_name | city | state | store_identifier | order_identifier |
| --- | --- | --- | --- | --- | --- |
|  | Autocare Service Center |  |  | 2718 |  |


**2) Vector Search — top candidates (similarity):**

| similarity | merchant_id | merchant_name | city | state | category |
| --- | --- | --- | --- | --- | --- |
| 0.7741 | M02087 | AutoCare Service Center | Las Vegas | NV | Automotive |
| 0.7673 | M02052 | AutoCare Service Center | Reno | NV | Automotive |
| 0.7619 | M02095 | AutoCare Service Center | Madison | WI | Automotive |
| 0.7615 | M02059 | AutoCare Service Center | Boulder | CO | Automotive |
| 0.7609 | M02078 | AutoCare Service Center | New Orleans | LA | Automotive |
| 0.7599 | M02061 | AutoCare Service Center | Tampa | FL | Automotive |
| 0.7592 | M02103 | AutoCare Service Center | Baton Rouge | LA | Automotive |
| 0.7592 | M02104 | AutoCare Service Center | Sacramento | CA | Automotive |
| 0.7573 | M02089 | AutoCare Service Center | Charleston | SC | Automotive |
| 0.7565 | M02093 | AutoCare Service Center | Jersey City | NJ | Automotive |


**3) LLM judge decision:**

| decision | merchant_id | merchant_name | confidence | alternatives |
| --- | --- | --- | --- | --- |
| AMBIGUOUS |  |  | 0.93 | M02087, M02052, M02095 |


> **Reason:** The descriptor names 'Autocare Service Center' with only store number #2718 and no city or state. All 10 candidates share the same name in different cities, and none of the candidate data links store #2718 to a particular branch. The top similarity score (0.7741) is only marginally higher than the others and is not sufficient evidence to choose one.


_Latency: 3271 ms · LLM calls: 2 · Ground truth: AMBIGUOUS_


---

## Example 7 — expected **AMBIGUOUS**, system decided **AMBIGUOUS** ✅

**Transaction** `T000237`  

**Raw descriptor:** `HOPPY TRAIL BREWING`


**1) Extracted entities (GenAI):**

| payment_facilitator | merchant_name | city | state | store_identifier | order_identifier |
| --- | --- | --- | --- | --- | --- |
|  | Hoppy Trail Brewing |  |  |  |  |


**2) Vector Search — top candidates (similarity):**

| similarity | merchant_id | merchant_name | city | state | category |
| --- | --- | --- | --- | --- | --- |
| 0.7662 | M02254 | Hoppy Trails Brewing | Des Moines | IA | Bar |
| 0.7655 | M02228 | Hoppy Trails Brewing | Reno | NV | Bar |
| 0.7641 | M02240 | Hoppy Trails Brewing | Portland | OR | Bar |
| 0.7616 | M02238 | Hoppy Trails Brewing | Cleveland | OH | Bar |
| 0.761 | M02212 | Hoppy Trails Brewing | Arlington | VA | Bar |
| 0.761 | M02210 | Hoppy Trails Brewing | Milwaukee | WI | Bar |
| 0.7604 | M02234 | Hoppy Trails Brewing | Charlotte | NC | Bar |
| 0.7569 | M02199 | Hoppy Trails Brewing | Oakland | CA | Bar |
| 0.7563 | M02227 | Hoppy Trails Brewing | Rochester | NY | Bar |
| 0.7552 | M02235 | Hoppy Trails Brewing | Fort Wayne | IN | Bar |


**3) LLM judge decision:**

| decision | merchant_id | merchant_name | confidence | alternatives |
| --- | --- | --- | --- | --- |
| AMBIGUOUS |  |  | 0.95 | M02254, M02228, M02240 |


> **Reason:** The descriptor 'HOPPY TRAIL BREWING' has no city or state. Ten candidates share the name 'Hoppy Trails Brewing' in different cities, and the similarity scores are nearly identical (0.755-0.766). With no location, the branches cannot be separated, and the small name difference (Trail vs Trails) applies equally to all of them.


_Latency: 3277 ms · LLM calls: 2 · Ground truth: AMBIGUOUS_


---

## Example 8 — expected **AMBIGUOUS**, system decided **AMBIGUOUS** ✅

**Transaction** `T000496`  

**Raw descriptor:** `HAPPY PAWS PET SUPPLIES`


**1) Extracted entities (GenAI):**

| payment_facilitator | merchant_name | city | state | store_identifier | order_identifier |
| --- | --- | --- | --- | --- | --- |
|  | Happy Paws Pet Supplies |  |  |  |  |


**2) Vector Search — top candidates (similarity):**

| similarity | merchant_id | merchant_name | city | state | category |
| --- | --- | --- | --- | --- | --- |
| 0.8272 | M02029 | Happy Paws Pet Supplies | Denver | CO | Pet Store |
| 0.8234 | M01996 | Happy Paws Pet Supplies | Boulder | CO | Pet Store |
| 0.8208 | M01975 | Happy Paws Pet Supplies | Aurora | CO | Pet Store |
| 0.8145 | M02002 | Happy Paws Pet Supplies | St Louis | MO | Pet Store |
| 0.8136 | M02043 | Happy Paws Pet Supplies | Columbia | SC | Pet Store |
| 0.8119 | M01968 | Happy Paws Pet Supplies | Seattle | WA | Pet Store |
| 0.8102 | M02021 | Happy Paws Pet Supplies | Grand Rapids | MI | Pet Store |
| 0.8094 | M02026 | Happy Paws Pet Supplies | Madison | WI | Pet Store |
| 0.8074 | M01965 | Happy Paws Pet Supplies | San Diego | CA | Pet Store |
| 0.8039 | M02044 | Happy Paws Pet Supplies | Chicago | IL | Pet Store |


**3) LLM judge decision:**

| decision | merchant_id | merchant_name | confidence | alternatives |
| --- | --- | --- | --- | --- |
| AMBIGUOUS |  |  | 0.96 | M02029, M01996, M01975 |


> **Reason:** The descriptor gives the name 'Happy Paws Pet Supplies' but no city, state, or store identifier. All 10 candidates share this exact name in different locations (Denver, Boulder, Aurora, St Louis, Columbia, Seattle, Grand Rapids, Madison, San Diego, Chicago), so the location rule cannot separate them. The similarity scores are close (0.80-0.83) and are not decisive evidence.


_Latency: 3142 ms · LLM calls: 2 · Ground truth: AMBIGUOUS_


---

## Example 9 — expected **AMBIGUOUS**, system decided **AMBIGUOUS** ✅

**Transaction** `T000908`  

**Raw descriptor:** `HOPPY TRAILS BREWING / 482`


**1) Extracted entities (GenAI):**

| payment_facilitator | merchant_name | city | state | store_identifier | order_identifier |
| --- | --- | --- | --- | --- | --- |
|  | Hoppy Trails Brewing |  |  | 482 |  |


**2) Vector Search — top candidates (similarity):**

| similarity | merchant_id | merchant_name | city | state | category |
| --- | --- | --- | --- | --- | --- |
| 0.8019 | M02240 | Hoppy Trails Brewing | Portland | OR | Bar |
| 0.7979 | M02199 | Hoppy Trails Brewing | Oakland | CA | Bar |
| 0.7962 | M02254 | Hoppy Trails Brewing | Des Moines | IA | Bar |
| 0.7925 | M02210 | Hoppy Trails Brewing | Milwaukee | WI | Bar |
| 0.7914 | M02228 | Hoppy Trails Brewing | Reno | NV | Bar |
| 0.7903 | M02235 | Hoppy Trails Brewing | Fort Wayne | IN | Bar |
| 0.7898 | M02227 | Hoppy Trails Brewing | Rochester | NY | Bar |
| 0.7869 | M02238 | Hoppy Trails Brewing | Cleveland | OH | Bar |
| 0.7853 | M02201 | Hoppy Trails Brewing | Minneapolis | MN | Bar |
| 0.7844 | M02222 | Hoppy Trails Brewing | Raleigh | NC | Bar |


**3) LLM judge decision:**

| decision | merchant_id | merchant_name | confidence | alternatives |
| --- | --- | --- | --- | --- |
| AMBIGUOUS |  |  | 0.93 | M02240, M02199, M02254 |


> **Reason:** The descriptor names 'Hoppy Trails Brewing' with only store identifier 482 and no city or state. Ten candidates share the exact same name in different cities, and none of the candidate records carries a store number that could link to 482. Location cannot separate them and the similarity scores are nearly identical (0.784-0.802), so no single branch can be reliably chosen.


_Latency: 3402 ms · LLM calls: 2 · Ground truth: AMBIGUOUS_


---

## Example 10 — expected **NO_MATCH**, system decided **NO_MATCH** ✅

**Transaction** `T000149`  

**Raw descriptor:** `NOVA UNKNOWN MERCHANT`


**1) Extracted entities (GenAI):**

| payment_facilitator | merchant_name | city | state | store_identifier | order_identifier |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |


**2) Vector Search — top candidates (similarity):**

| similarity | merchant_id | merchant_name | city | state | category |
| --- | --- | --- | --- | --- | --- |
| 0.5339 | M00697 | Cornerstone Market | Annapolis | MD | Grocery |
| 0.5296 | M00981 | Corner Pantry | Richmond | VA | Convenience Store |
| 0.5285 | M00965 | Corner Pantry | Santa Fe | NM | Convenience Store |
| 0.5284 | M00916 | Speedway Mart | Santa Fe | NM | Convenience Store |
| 0.528 | M00198 | Daily Grind Coffee | Annapolis | MD | Coffee Shop |
| 0.5272 | M00593 | Fresh Market Grocers | Reno | NV | Grocery |
| 0.5259 | M01517 | Builders Depot | Santa Fe | NM | Home Improvement |
| 0.5238 | M00711 | Cornerstone Market | Arlington | VA | Grocery |
| 0.5225 | M01485 | Builders Depot | Reno | NV | Home Improvement |
| 0.5222 | M00980 | Corner Pantry | Las Vegas | NV | Convenience Store |


**3) LLM judge decision:**

| decision | merchant_id | merchant_name | confidence | alternatives |
| --- | --- | --- | --- | --- |
| NO_MATCH |  |  | 0.97 | — |


> **Reason:** The descriptor 'NOVA UNKNOWN MERCHANT' has no extractable merchant name or location. None of the candidates contain 'NOVA' in their names. All similarity scores are low (about 0.52-0.53) and nearly identical, so the vector search gives no meaningful signal. Linking any candidate would be forcing a match.


_Latency: 12120 ms · LLM calls: 2 · Ground truth: NO_MATCH_


---

## Example 11 — expected **NO_MATCH**, system decided **NO_MATCH** ✅

**Transaction** `T000229`  

**Raw descriptor:** `NOVA UNKNOWN MERCHANT`


**1) Extracted entities (GenAI):**

| payment_facilitator | merchant_name | city | state | store_identifier | order_identifier |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |


**2) Vector Search — top candidates (similarity):**

| similarity | merchant_id | merchant_name | city | state | category |
| --- | --- | --- | --- | --- | --- |
| 0.5339 | M00697 | Cornerstone Market | Annapolis | MD | Grocery |
| 0.5296 | M00981 | Corner Pantry | Richmond | VA | Convenience Store |
| 0.5285 | M00965 | Corner Pantry | Santa Fe | NM | Convenience Store |
| 0.5284 | M00916 | Speedway Mart | Santa Fe | NM | Convenience Store |
| 0.528 | M00198 | Daily Grind Coffee | Annapolis | MD | Coffee Shop |
| 0.5272 | M00593 | Fresh Market Grocers | Reno | NV | Grocery |
| 0.5259 | M01517 | Builders Depot | Santa Fe | NM | Home Improvement |
| 0.5239 | M00711 | Cornerstone Market | Arlington | VA | Grocery |
| 0.5225 | M01485 | Builders Depot | Reno | NV | Home Improvement |
| 0.5223 | M00980 | Corner Pantry | Las Vegas | NV | Convenience Store |


**3) LLM judge decision:**

| decision | merchant_id | merchant_name | confidence | alternatives |
| --- | --- | --- | --- | --- |
| NO_MATCH |  |  | 0.96 | — |


> **Reason:** The descriptor 'NOVA UNKNOWN MERCHANT' has no extracted merchant name or location. None of the candidates has a name resembling 'NOVA'. The candidates have low, tightly clustered similarity scores (0.52-0.53), which look like noise, so no candidate can be reliably linked.


_Latency: 11947 ms · LLM calls: 2 · Ground truth: NO_MATCH_


---

## Example 12 — expected **NO_MATCH**, system decided **NO_MATCH** ✅

**Transaction** `T000282`  

**Raw descriptor:** `QUANTUM WIDGETS SAN JOSE CA FLUN3YPQ`


**1) Extracted entities (GenAI):**

| payment_facilitator | merchant_name | city | state | store_identifier | order_identifier |
| --- | --- | --- | --- | --- | --- |
|  | Quantum Widgets | San Jose | CA |  | FLUN3YPQ |


**2) Vector Search — top candidates (similarity):**

| similarity | merchant_id | merchant_name | city | state | category |
| --- | --- | --- | --- | --- | --- |
| 0.5945 | M01227 | TechNova Electronics | San Francisco | CA | Electronics |
| 0.5926 | M01256 | GadgetWorld | San Jose | CA | Electronics |
| 0.5805 | M01215 | TechNova Electronics | San Jose | CA | Electronics |
| 0.5759 | M01046 | Urban Threads | San Jose | CA | Apparel |
| 0.575 | M01202 | TechNova Electronics | Oakland | CA | Electronics |
| 0.5739 | M01887 | BrightLearn Academy | San Jose | CA | Education |
| 0.5654 | M01271 | GadgetWorld | Jersey City | NJ | Electronics |
| 0.5615 | M01235 | GadgetWorld | Phoenix | AZ | Electronics |
| 0.5595 | M01252 | GadgetWorld | Chandler | AZ | Electronics |
| 0.5588 | M01245 | GadgetWorld | Boulder | CO | Electronics |


**3) LLM judge decision:**

| decision | merchant_id | merchant_name | confidence | alternatives |
| --- | --- | --- | --- | --- |
| NO_MATCH |  |  | 0.95 | — |


> **Reason:** No candidate name matches 'Quantum Widgets'. The candidates (TechNova Electronics, GadgetWorld, Urban Threads, BrightLearn Academy) are different merchants. Several are in San Jose, CA, but a matching location alone is not enough, and the similarity scores (~0.59) are low.


_Latency: 3117 ms · LLM calls: 2 · Ground truth: NO_MATCH_
