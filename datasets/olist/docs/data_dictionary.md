# Olist Data Dictionary

Author descriptions derived from published CSV headers and dataset documentation. No Gold events or Entity Types are included.

## customers

Customer identifier and location; customer_unique_id identifies a customer across orders.

| Column | Type | Key | Description |
|---|---|---|---|
| customer_id | TEXT | PK | Order-specific customer identifier. |
| customer_unique_id | TEXT |  | Identifier that can repeat across customer records for the same individual. |
| customer_zip_code_prefix | TEXT |  | customer zip code prefix. |
| customer_city | TEXT |  | customer city. |
| customer_state | TEXT |  | customer state. |

## sellers

Seller identifier and location.

| Column | Type | Key | Description |
|---|---|---|---|
| seller_id | TEXT | PK | seller id. |
| seller_zip_code_prefix | TEXT |  | seller zip code prefix. |
| seller_city | TEXT |  | seller city. |
| seller_state | TEXT |  | seller state. |

## products

Products, their categories, and product dimensions.

| Column | Type | Key | Description |
|---|---|---|---|
| product_id | TEXT | PK | product id. |
| product_category_name | TEXT |  | Product category in Portuguese. |
| product_name_lenght | INTEGER |  | product name lenght. |
| product_description_lenght | INTEGER |  | product description lenght. |
| product_photos_qty | INTEGER |  | product photos qty. |
| product_weight_g | INTEGER |  | product weight g. |
| product_length_cm | INTEGER |  | product length cm. |
| product_height_cm | INTEGER |  | product height cm. |
| product_width_cm | INTEGER |  | product width cm. |

## geolocation

Geographic records at ZIP-code-prefix level; multiple records can share a prefix.

| Column | Type | Key | Description |
|---|---|---|---|
| geolocation_zip_code_prefix | TEXT |  | Postal prefix; not unique in the source records. |
| geolocation_lat | TEXT |  | geolocation lat. |
| geolocation_lng | TEXT |  | geolocation lng. |
| geolocation_city | TEXT |  | geolocation city. |
| geolocation_state | TEXT |  | geolocation state. |

## product_category_name_translation

Portuguese-to-English product category labels.

| Column | Type | Key | Description |
|---|---|---|---|
| product_category_name | TEXT | PK | Product category in Portuguese. |
| product_category_name_english | TEXT |  | English category translation. |

## orders

Order status and recorded ordering, approval, carrier handoff and delivery times.

| Column | Type | Key | Description |
|---|---|---|---|
| order_id | TEXT | PK | Order identifier. |
| customer_id | TEXT | FK | Order-specific customer identifier. |
| order_status | TEXT |  | Current order status, not a timestamped status transition history. |
| order_purchase_timestamp | TEXT |  | Timestamp of purchase/order placement. |
| order_approved_at | TEXT |  | Recorded order approval timestamp. |
| order_delivered_carrier_date | TEXT |  | Timestamp the order was handed to the carrier. |
| order_delivered_customer_date | TEXT |  | Timestamp the order was delivered to the customer. |
| order_estimated_delivery_date | TEXT |  | Planned delivery date, not the actual delivery event. |

## order_items

Ordered items, product and seller references, shipping deadline, price and freight.

| Column | Type | Key | Description |
|---|---|---|---|
| order_id | TEXT | PK | Order identifier. |
| order_item_id | INTEGER | PK | Item sequence within the order. |
| product_id | TEXT | FK | product id. |
| seller_id | TEXT | FK | seller id. |
| shipping_limit_date | TEXT |  | Seller shipping deadline; a planned time, not carrier handoff. |
| price | TEXT |  | price. |
| freight_value | TEXT |  | freight value. |

## order_payments

Payment details per order and payment sequence; this table has no payment occurrence timestamp.

| Column | Type | Key | Description |
|---|---|---|---|
| order_id | TEXT | PK | Order identifier. |
| payment_sequential | INTEGER | PK | Payment sequence within the order. |
| payment_type | TEXT |  | Payment method or category. |
| payment_installments | INTEGER |  | Installment count. |
| payment_value | TEXT |  | Payment monetary amount. |

## order_reviews

Review content, survey-creation time and response time; review_id alone need not be unique.

| Column | Type | Key | Description |
|---|---|---|---|
| review_id | TEXT |  | Review identifier; uniqueness is not assumed. |
| order_id | TEXT | FK | Order identifier. |
| review_score | INTEGER |  | review score. |
| review_comment_title | TEXT |  | review comment title. |
| review_comment_message | TEXT |  | review comment message. |
| review_creation_date | TEXT |  | Date the review survey was created/sent. |
| review_answer_timestamp | TEXT |  | Timestamp of the review answer. |
