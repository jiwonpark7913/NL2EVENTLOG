CREATE TABLE "customers" (
  "customer_id" TEXT NOT NULL,
  "customer_unique_id" TEXT,
  "customer_zip_code_prefix" TEXT,
  "customer_city" TEXT,
  "customer_state" TEXT,
  PRIMARY KEY ("customer_id")
);

CREATE TABLE "sellers" (
  "seller_id" TEXT NOT NULL,
  "seller_zip_code_prefix" TEXT,
  "seller_city" TEXT,
  "seller_state" TEXT,
  PRIMARY KEY ("seller_id")
);

CREATE TABLE "products" (
  "product_id" TEXT NOT NULL,
  "product_category_name" TEXT,
  "product_name_lenght" INTEGER,
  "product_description_lenght" INTEGER,
  "product_photos_qty" INTEGER,
  "product_weight_g" INTEGER,
  "product_length_cm" INTEGER,
  "product_height_cm" INTEGER,
  "product_width_cm" INTEGER,
  PRIMARY KEY ("product_id")
);

CREATE TABLE "geolocation" (
  "geolocation_zip_code_prefix" TEXT,
  "geolocation_lat" TEXT,
  "geolocation_lng" TEXT,
  "geolocation_city" TEXT,
  "geolocation_state" TEXT
);

CREATE TABLE "product_category_name_translation" (
  "product_category_name" TEXT NOT NULL,
  "product_category_name_english" TEXT,
  PRIMARY KEY ("product_category_name")
);

CREATE TABLE "orders" (
  "order_id" TEXT NOT NULL,
  "customer_id" TEXT,
  "order_status" TEXT,
  "order_purchase_timestamp" TEXT,
  "order_approved_at" TEXT,
  "order_delivered_carrier_date" TEXT,
  "order_delivered_customer_date" TEXT,
  "order_estimated_delivery_date" TEXT,
  PRIMARY KEY ("order_id"),
  FOREIGN KEY ("customer_id") REFERENCES "customers" ("customer_id")
);

CREATE TABLE "order_items" (
  "order_id" TEXT NOT NULL,
  "order_item_id" INTEGER NOT NULL,
  "product_id" TEXT,
  "seller_id" TEXT,
  "shipping_limit_date" TEXT,
  "price" TEXT,
  "freight_value" TEXT,
  PRIMARY KEY ("order_id", "order_item_id"),
  FOREIGN KEY ("order_id") REFERENCES "orders" ("order_id"),
  FOREIGN KEY ("product_id") REFERENCES "products" ("product_id"),
  FOREIGN KEY ("seller_id") REFERENCES "sellers" ("seller_id")
);

CREATE TABLE "order_payments" (
  "order_id" TEXT NOT NULL,
  "payment_sequential" INTEGER NOT NULL,
  "payment_type" TEXT,
  "payment_installments" INTEGER,
  "payment_value" TEXT,
  PRIMARY KEY ("order_id", "payment_sequential"),
  FOREIGN KEY ("order_id") REFERENCES "orders" ("order_id")
);

CREATE TABLE "order_reviews" (
  "review_id" TEXT,
  "order_id" TEXT,
  "review_score" INTEGER,
  "review_comment_title" TEXT,
  "review_comment_message" TEXT,
  "review_creation_date" TEXT,
  "review_answer_timestamp" TEXT,
  FOREIGN KEY ("order_id") REFERENCES "orders" ("order_id")
);
