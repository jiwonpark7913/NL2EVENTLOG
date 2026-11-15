CREATE TABLE "DatabaseLog" (
  "DatabaseLogID" INTEGER NOT NULL,
  "PostTime" TEXT NOT NULL,
  "DatabaseUser" TEXT NOT NULL,
  "Event" TEXT NOT NULL,
  "Schema" TEXT,
  "Object" TEXT,
  "TSQL" TEXT NOT NULL,
  "XmlEvent" TEXT NOT NULL,
  PRIMARY KEY ("DatabaseLogID")
);

CREATE TABLE "ErrorLog" (
  "ErrorLogID" INTEGER NOT NULL,
  "ErrorTime" TEXT NOT NULL,
  "UserName" TEXT NOT NULL,
  "ErrorNumber" INTEGER NOT NULL,
  "ErrorSeverity" INTEGER,
  "ErrorState" INTEGER,
  "ErrorProcedure" TEXT,
  "ErrorLine" INTEGER,
  "ErrorMessage" TEXT NOT NULL,
  PRIMARY KEY ("ErrorLogID")
);

CREATE TABLE "Address" (
  "AddressID" INTEGER NOT NULL,
  "AddressLine1" TEXT NOT NULL,
  "AddressLine2" TEXT,
  "City" TEXT NOT NULL,
  "StateProvinceID" INTEGER NOT NULL,
  "PostalCode" TEXT NOT NULL,
  "SpatialLocation" BLOB,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("AddressID"),
  FOREIGN KEY ("StateProvinceID") REFERENCES "StateProvince" ("StateProvinceID")
);

CREATE TABLE "AddressType" (
  "AddressTypeID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("AddressTypeID")
);

CREATE TABLE "AWBuildVersion" (
  "SystemInformationID" INTEGER NOT NULL,
  "Database Version" TEXT NOT NULL,
  "VersionDate" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("SystemInformationID")
);

CREATE TABLE "BillOfMaterials" (
  "BillOfMaterialsID" INTEGER NOT NULL,
  "ProductAssemblyID" INTEGER,
  "ComponentID" INTEGER NOT NULL,
  "StartDate" TEXT NOT NULL,
  "EndDate" TEXT,
  "UnitMeasureCode" TEXT NOT NULL,
  "BOMLevel" INTEGER NOT NULL,
  "PerAssemblyQty" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BillOfMaterialsID"),
  FOREIGN KEY ("ProductAssemblyID") REFERENCES "Product" ("ProductID"),
  FOREIGN KEY ("ComponentID") REFERENCES "Product" ("ProductID"),
  FOREIGN KEY ("UnitMeasureCode") REFERENCES "UnitMeasure" ("UnitMeasureCode")
);

CREATE TABLE "BusinessEntity" (
  "BusinessEntityID" INTEGER NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID")
);

CREATE TABLE "BusinessEntityAddress" (
  "BusinessEntityID" INTEGER NOT NULL,
  "AddressID" INTEGER NOT NULL,
  "AddressTypeID" INTEGER NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID", "AddressID", "AddressTypeID"),
  FOREIGN KEY ("AddressID") REFERENCES "Address" ("AddressID"),
  FOREIGN KEY ("AddressTypeID") REFERENCES "AddressType" ("AddressTypeID"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "BusinessEntity" ("BusinessEntityID")
);

CREATE TABLE "BusinessEntityContact" (
  "BusinessEntityID" INTEGER NOT NULL,
  "PersonID" INTEGER NOT NULL,
  "ContactTypeID" INTEGER NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID", "PersonID", "ContactTypeID"),
  FOREIGN KEY ("PersonID") REFERENCES "Person" ("BusinessEntityID"),
  FOREIGN KEY ("ContactTypeID") REFERENCES "ContactType" ("ContactTypeID"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "BusinessEntity" ("BusinessEntityID")
);

CREATE TABLE "ContactType" (
  "ContactTypeID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ContactTypeID")
);

CREATE TABLE "CountryRegionCurrency" (
  "CountryRegionCode" TEXT NOT NULL,
  "CurrencyCode" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("CountryRegionCode", "CurrencyCode"),
  FOREIGN KEY ("CountryRegionCode") REFERENCES "CountryRegion" ("CountryRegionCode"),
  FOREIGN KEY ("CurrencyCode") REFERENCES "Currency" ("CurrencyCode")
);

CREATE TABLE "CountryRegion" (
  "CountryRegionCode" TEXT NOT NULL,
  "Name" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("CountryRegionCode")
);

CREATE TABLE "CreditCard" (
  "CreditCardID" INTEGER NOT NULL,
  "CardType" TEXT NOT NULL,
  "CardNumber" TEXT NOT NULL,
  "ExpMonth" INTEGER NOT NULL,
  "ExpYear" INTEGER NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("CreditCardID")
);

CREATE TABLE "Culture" (
  "CultureID" TEXT NOT NULL,
  "Name" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("CultureID")
);

CREATE TABLE "Currency" (
  "CurrencyCode" TEXT NOT NULL,
  "Name" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("CurrencyCode")
);

CREATE TABLE "CurrencyRate" (
  "CurrencyRateID" INTEGER NOT NULL,
  "CurrencyRateDate" TEXT NOT NULL,
  "FromCurrencyCode" TEXT NOT NULL,
  "ToCurrencyCode" TEXT NOT NULL,
  "AverageRate" TEXT NOT NULL,
  "EndOfDayRate" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("CurrencyRateID"),
  FOREIGN KEY ("FromCurrencyCode") REFERENCES "Currency" ("CurrencyCode"),
  FOREIGN KEY ("ToCurrencyCode") REFERENCES "Currency" ("CurrencyCode")
);

CREATE TABLE "Customer" (
  "CustomerID" INTEGER NOT NULL,
  "PersonID" INTEGER,
  "StoreID" INTEGER,
  "TerritoryID" INTEGER,
  "AccountNumber" TEXT,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("CustomerID"),
  FOREIGN KEY ("PersonID") REFERENCES "Person" ("BusinessEntityID"),
  FOREIGN KEY ("StoreID") REFERENCES "Store" ("BusinessEntityID"),
  FOREIGN KEY ("TerritoryID") REFERENCES "SalesTerritory" ("TerritoryID")
);

CREATE TABLE "Department" (
  "DepartmentID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "GroupName" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("DepartmentID")
);

CREATE TABLE "Document" (
  "DocumentNode" TEXT NOT NULL,
  "DocumentLevel" TEXT,
  "Title" TEXT NOT NULL,
  "Owner" INTEGER NOT NULL,
  "FolderFlag" INTEGER NOT NULL,
  "FileName" TEXT NOT NULL,
  "FileExtension" TEXT NOT NULL,
  "Revision" TEXT NOT NULL,
  "ChangeNumber" INTEGER NOT NULL,
  "Status" INTEGER NOT NULL,
  "DocumentSummary" TEXT,
  "Document" BLOB,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("DocumentNode"),
  FOREIGN KEY ("Owner") REFERENCES "Employee" ("BusinessEntityID")
);

CREATE TABLE "EmailAddress" (
  "BusinessEntityID" INTEGER NOT NULL,
  "EmailAddressID" INTEGER NOT NULL,
  "EmailAddress" TEXT,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID", "EmailAddressID"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "Person" ("BusinessEntityID")
);

CREATE TABLE "Employee" (
  "BusinessEntityID" INTEGER NOT NULL,
  "NationalIDNumber" TEXT NOT NULL,
  "LoginID" TEXT NOT NULL,
  "OrganizationNode" TEXT,
  "OrganizationLevel" TEXT,
  "JobTitle" TEXT NOT NULL,
  "BirthDate" TEXT NOT NULL,
  "MaritalStatus" TEXT NOT NULL,
  "Gender" TEXT NOT NULL,
  "HireDate" TEXT NOT NULL,
  "SalariedFlag" INTEGER NOT NULL,
  "VacationHours" INTEGER NOT NULL,
  "SickLeaveHours" INTEGER NOT NULL,
  "CurrentFlag" INTEGER NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "Person" ("BusinessEntityID")
);

CREATE TABLE "EmployeeDepartmentHistory" (
  "BusinessEntityID" INTEGER NOT NULL,
  "DepartmentID" INTEGER NOT NULL,
  "ShiftID" INTEGER NOT NULL,
  "StartDate" TEXT NOT NULL,
  "EndDate" TEXT,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID", "StartDate", "DepartmentID", "ShiftID"),
  FOREIGN KEY ("DepartmentID") REFERENCES "Department" ("DepartmentID"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "Employee" ("BusinessEntityID"),
  FOREIGN KEY ("ShiftID") REFERENCES "Shift" ("ShiftID")
);

CREATE TABLE "EmployeePayHistory" (
  "BusinessEntityID" INTEGER NOT NULL,
  "RateChangeDate" TEXT NOT NULL,
  "Rate" TEXT NOT NULL,
  "PayFrequency" INTEGER NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID", "RateChangeDate"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "Employee" ("BusinessEntityID")
);

CREATE TABLE "Illustration" (
  "IllustrationID" INTEGER NOT NULL,
  "Diagram" TEXT,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("IllustrationID")
);

CREATE TABLE "JobCandidate" (
  "JobCandidateID" INTEGER NOT NULL,
  "BusinessEntityID" INTEGER,
  "Resume" TEXT,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("JobCandidateID"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "Employee" ("BusinessEntityID")
);

CREATE TABLE "Location" (
  "LocationID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "CostRate" TEXT NOT NULL,
  "Availability" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("LocationID")
);

CREATE TABLE "Password" (
  "BusinessEntityID" INTEGER NOT NULL,
  "PasswordHash" TEXT NOT NULL,
  "PasswordSalt" TEXT NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "Person" ("BusinessEntityID")
);

CREATE TABLE "Person" (
  "BusinessEntityID" INTEGER NOT NULL,
  "PersonType" TEXT NOT NULL,
  "NameStyle" TEXT NOT NULL,
  "Title" TEXT,
  "FirstName" TEXT NOT NULL,
  "MiddleName" TEXT,
  "LastName" TEXT NOT NULL,
  "Suffix" TEXT,
  "EmailPromotion" INTEGER NOT NULL,
  "AdditionalContactInfo" TEXT,
  "Demographics" TEXT,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "BusinessEntity" ("BusinessEntityID")
);

CREATE TABLE "PersonCreditCard" (
  "BusinessEntityID" INTEGER NOT NULL,
  "CreditCardID" INTEGER NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID", "CreditCardID"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "Person" ("BusinessEntityID"),
  FOREIGN KEY ("CreditCardID") REFERENCES "CreditCard" ("CreditCardID")
);

CREATE TABLE "PersonPhone" (
  "BusinessEntityID" INTEGER NOT NULL,
  "PhoneNumber" TEXT NOT NULL,
  "PhoneNumberTypeID" INTEGER NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID", "PhoneNumber", "PhoneNumberTypeID"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "Person" ("BusinessEntityID"),
  FOREIGN KEY ("PhoneNumberTypeID") REFERENCES "PhoneNumberType" ("PhoneNumberTypeID")
);

CREATE TABLE "PhoneNumberType" (
  "PhoneNumberTypeID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("PhoneNumberTypeID")
);

CREATE TABLE "Product" (
  "ProductID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "ProductNumber" TEXT NOT NULL,
  "MakeFlag" INTEGER NOT NULL,
  "FinishedGoodsFlag" INTEGER NOT NULL,
  "Color" TEXT,
  "SafetyStockLevel" INTEGER NOT NULL,
  "ReorderPoint" INTEGER NOT NULL,
  "StandardCost" TEXT NOT NULL,
  "ListPrice" TEXT NOT NULL,
  "Size" TEXT,
  "SizeUnitMeasureCode" TEXT,
  "WeightUnitMeasureCode" TEXT,
  "Weight" TEXT,
  "DaysToManufacture" INTEGER NOT NULL,
  "ProductLine" TEXT,
  "Class" TEXT,
  "Style" TEXT,
  "ProductSubcategoryID" INTEGER,
  "ProductModelID" INTEGER,
  "SellStartDate" TEXT NOT NULL,
  "SellEndDate" TEXT,
  "DiscontinuedDate" TEXT,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductID"),
  FOREIGN KEY ("SizeUnitMeasureCode") REFERENCES "UnitMeasure" ("UnitMeasureCode"),
  FOREIGN KEY ("WeightUnitMeasureCode") REFERENCES "UnitMeasure" ("UnitMeasureCode"),
  FOREIGN KEY ("ProductModelID") REFERENCES "ProductModel" ("ProductModelID"),
  FOREIGN KEY ("ProductSubcategoryID") REFERENCES "ProductSubcategory" ("ProductSubcategoryID")
);

CREATE TABLE "ProductCategory" (
  "ProductCategoryID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductCategoryID")
);

CREATE TABLE "ProductCostHistory" (
  "ProductID" INTEGER NOT NULL,
  "StartDate" TEXT NOT NULL,
  "EndDate" TEXT,
  "StandardCost" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductID", "StartDate"),
  FOREIGN KEY ("ProductID") REFERENCES "Product" ("ProductID")
);

CREATE TABLE "ProductDescription" (
  "ProductDescriptionID" INTEGER NOT NULL,
  "Description" TEXT NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductDescriptionID")
);

CREATE TABLE "ProductDocument" (
  "ProductID" INTEGER NOT NULL,
  "DocumentNode" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductID", "DocumentNode"),
  FOREIGN KEY ("ProductID") REFERENCES "Product" ("ProductID"),
  FOREIGN KEY ("DocumentNode") REFERENCES "Document" ("DocumentNode")
);

CREATE TABLE "ProductInventory" (
  "ProductID" INTEGER NOT NULL,
  "LocationID" INTEGER NOT NULL,
  "Shelf" TEXT NOT NULL,
  "Bin" INTEGER NOT NULL,
  "Quantity" INTEGER NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductID", "LocationID"),
  FOREIGN KEY ("LocationID") REFERENCES "Location" ("LocationID"),
  FOREIGN KEY ("ProductID") REFERENCES "Product" ("ProductID")
);

CREATE TABLE "ProductListPriceHistory" (
  "ProductID" INTEGER NOT NULL,
  "StartDate" TEXT NOT NULL,
  "EndDate" TEXT,
  "ListPrice" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductID", "StartDate"),
  FOREIGN KEY ("ProductID") REFERENCES "Product" ("ProductID")
);

CREATE TABLE "ProductModel" (
  "ProductModelID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "CatalogDescription" TEXT,
  "Instructions" TEXT,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductModelID")
);

CREATE TABLE "ProductModelIllustration" (
  "ProductModelID" INTEGER NOT NULL,
  "IllustrationID" INTEGER NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductModelID", "IllustrationID"),
  FOREIGN KEY ("ProductModelID") REFERENCES "ProductModel" ("ProductModelID"),
  FOREIGN KEY ("IllustrationID") REFERENCES "Illustration" ("IllustrationID")
);

CREATE TABLE "ProductModelProductDescriptionCulture" (
  "ProductModelID" INTEGER NOT NULL,
  "ProductDescriptionID" INTEGER NOT NULL,
  "CultureID" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductModelID", "ProductDescriptionID", "CultureID"),
  FOREIGN KEY ("ProductDescriptionID") REFERENCES "ProductDescription" ("ProductDescriptionID"),
  FOREIGN KEY ("CultureID") REFERENCES "Culture" ("CultureID"),
  FOREIGN KEY ("ProductModelID") REFERENCES "ProductModel" ("ProductModelID")
);

CREATE TABLE "ProductPhoto" (
  "ProductPhotoID" INTEGER NOT NULL,
  "ThumbNailPhoto" BLOB,
  "ThumbnailPhotoFileName" TEXT,
  "LargePhoto" BLOB,
  "LargePhotoFileName" TEXT,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductPhotoID")
);

CREATE TABLE "ProductProductPhoto" (
  "ProductID" INTEGER NOT NULL,
  "ProductPhotoID" INTEGER NOT NULL,
  "Primary" INTEGER NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductID", "ProductPhotoID"),
  FOREIGN KEY ("ProductID") REFERENCES "Product" ("ProductID"),
  FOREIGN KEY ("ProductPhotoID") REFERENCES "ProductPhoto" ("ProductPhotoID")
);

CREATE TABLE "ProductReview" (
  "ProductReviewID" INTEGER NOT NULL,
  "ProductID" INTEGER NOT NULL,
  "ReviewerName" TEXT NOT NULL,
  "ReviewDate" TEXT NOT NULL,
  "EmailAddress" TEXT NOT NULL,
  "Rating" INTEGER NOT NULL,
  "Comments" TEXT,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductReviewID"),
  FOREIGN KEY ("ProductID") REFERENCES "Product" ("ProductID")
);

CREATE TABLE "ProductSubcategory" (
  "ProductSubcategoryID" INTEGER NOT NULL,
  "ProductCategoryID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductSubcategoryID"),
  FOREIGN KEY ("ProductCategoryID") REFERENCES "ProductCategory" ("ProductCategoryID")
);

CREATE TABLE "ProductVendor" (
  "ProductID" INTEGER NOT NULL,
  "BusinessEntityID" INTEGER NOT NULL,
  "AverageLeadTime" INTEGER NOT NULL,
  "StandardPrice" TEXT NOT NULL,
  "LastReceiptCost" TEXT,
  "LastReceiptDate" TEXT,
  "MinOrderQty" INTEGER NOT NULL,
  "MaxOrderQty" INTEGER NOT NULL,
  "OnOrderQty" INTEGER,
  "UnitMeasureCode" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ProductID", "BusinessEntityID"),
  FOREIGN KEY ("ProductID") REFERENCES "Product" ("ProductID"),
  FOREIGN KEY ("UnitMeasureCode") REFERENCES "UnitMeasure" ("UnitMeasureCode"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "Vendor" ("BusinessEntityID")
);

CREATE TABLE "PurchaseOrderDetail" (
  "PurchaseOrderID" INTEGER NOT NULL,
  "PurchaseOrderDetailID" INTEGER NOT NULL,
  "DueDate" TEXT NOT NULL,
  "OrderQty" INTEGER NOT NULL,
  "ProductID" INTEGER NOT NULL,
  "UnitPrice" TEXT NOT NULL,
  "LineTotal" TEXT,
  "ReceivedQty" TEXT NOT NULL,
  "RejectedQty" TEXT NOT NULL,
  "StockedQty" TEXT,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("PurchaseOrderID", "PurchaseOrderDetailID"),
  FOREIGN KEY ("ProductID") REFERENCES "Product" ("ProductID"),
  FOREIGN KEY ("PurchaseOrderID") REFERENCES "PurchaseOrderHeader" ("PurchaseOrderID")
);

CREATE TABLE "PurchaseOrderHeader" (
  "PurchaseOrderID" INTEGER NOT NULL,
  "RevisionNumber" INTEGER NOT NULL,
  "Status" INTEGER NOT NULL,
  "EmployeeID" INTEGER NOT NULL,
  "VendorID" INTEGER NOT NULL,
  "ShipMethodID" INTEGER NOT NULL,
  "OrderDate" TEXT NOT NULL,
  "ShipDate" TEXT,
  "SubTotal" TEXT NOT NULL,
  "TaxAmt" TEXT NOT NULL,
  "Freight" TEXT NOT NULL,
  "TotalDue" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("PurchaseOrderID"),
  FOREIGN KEY ("EmployeeID") REFERENCES "Employee" ("BusinessEntityID"),
  FOREIGN KEY ("VendorID") REFERENCES "Vendor" ("BusinessEntityID"),
  FOREIGN KEY ("ShipMethodID") REFERENCES "ShipMethod" ("ShipMethodID")
);

CREATE TABLE "SalesOrderDetail" (
  "SalesOrderID" INTEGER NOT NULL,
  "SalesOrderDetailID" INTEGER NOT NULL,
  "CarrierTrackingNumber" TEXT,
  "OrderQty" INTEGER NOT NULL,
  "ProductID" INTEGER NOT NULL,
  "SpecialOfferID" INTEGER NOT NULL,
  "UnitPrice" TEXT NOT NULL,
  "UnitPriceDiscount" TEXT NOT NULL,
  "LineTotal" TEXT,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("SalesOrderID", "SalesOrderDetailID"),
  FOREIGN KEY ("SalesOrderID") REFERENCES "SalesOrderHeader" ("SalesOrderID"),
  FOREIGN KEY ("SpecialOfferID", "ProductID") REFERENCES "SpecialOfferProduct" ("SpecialOfferID", "ProductID")
);

CREATE TABLE "SalesOrderHeader" (
  "SalesOrderID" INTEGER NOT NULL,
  "RevisionNumber" INTEGER NOT NULL,
  "OrderDate" TEXT NOT NULL,
  "DueDate" TEXT NOT NULL,
  "ShipDate" TEXT,
  "Status" INTEGER NOT NULL,
  "OnlineOrderFlag" INTEGER NOT NULL,
  "SalesOrderNumber" TEXT,
  "PurchaseOrderNumber" TEXT,
  "AccountNumber" TEXT,
  "CustomerID" INTEGER NOT NULL,
  "SalesPersonID" INTEGER,
  "TerritoryID" INTEGER,
  "BillToAddressID" INTEGER NOT NULL,
  "ShipToAddressID" INTEGER NOT NULL,
  "ShipMethodID" INTEGER NOT NULL,
  "CreditCardID" INTEGER,
  "CreditCardApprovalCode" TEXT,
  "CurrencyRateID" INTEGER,
  "SubTotal" TEXT NOT NULL,
  "TaxAmt" TEXT NOT NULL,
  "Freight" TEXT NOT NULL,
  "TotalDue" TEXT,
  "Comment" TEXT,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("SalesOrderID"),
  FOREIGN KEY ("BillToAddressID") REFERENCES "Address" ("AddressID"),
  FOREIGN KEY ("ShipToAddressID") REFERENCES "Address" ("AddressID"),
  FOREIGN KEY ("CreditCardID") REFERENCES "CreditCard" ("CreditCardID"),
  FOREIGN KEY ("CurrencyRateID") REFERENCES "CurrencyRate" ("CurrencyRateID"),
  FOREIGN KEY ("CustomerID") REFERENCES "Customer" ("CustomerID"),
  FOREIGN KEY ("SalesPersonID") REFERENCES "SalesPerson" ("BusinessEntityID"),
  FOREIGN KEY ("ShipMethodID") REFERENCES "ShipMethod" ("ShipMethodID"),
  FOREIGN KEY ("TerritoryID") REFERENCES "SalesTerritory" ("TerritoryID")
);

CREATE TABLE "SalesOrderHeaderSalesReason" (
  "SalesOrderID" INTEGER NOT NULL,
  "SalesReasonID" INTEGER NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("SalesOrderID", "SalesReasonID"),
  FOREIGN KEY ("SalesReasonID") REFERENCES "SalesReason" ("SalesReasonID"),
  FOREIGN KEY ("SalesOrderID") REFERENCES "SalesOrderHeader" ("SalesOrderID")
);

CREATE TABLE "SalesPerson" (
  "BusinessEntityID" INTEGER NOT NULL,
  "TerritoryID" INTEGER,
  "SalesQuota" TEXT,
  "Bonus" TEXT NOT NULL,
  "CommissionPct" TEXT NOT NULL,
  "SalesYTD" TEXT NOT NULL,
  "SalesLastYear" TEXT NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "Employee" ("BusinessEntityID"),
  FOREIGN KEY ("TerritoryID") REFERENCES "SalesTerritory" ("TerritoryID")
);

CREATE TABLE "SalesPersonQuotaHistory" (
  "BusinessEntityID" INTEGER NOT NULL,
  "QuotaDate" TEXT NOT NULL,
  "SalesQuota" TEXT NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID", "QuotaDate"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "SalesPerson" ("BusinessEntityID")
);

CREATE TABLE "SalesReason" (
  "SalesReasonID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "ReasonType" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("SalesReasonID")
);

CREATE TABLE "SalesTaxRate" (
  "SalesTaxRateID" INTEGER NOT NULL,
  "StateProvinceID" INTEGER NOT NULL,
  "TaxType" INTEGER NOT NULL,
  "TaxRate" TEXT NOT NULL,
  "Name" TEXT NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("SalesTaxRateID"),
  FOREIGN KEY ("StateProvinceID") REFERENCES "StateProvince" ("StateProvinceID")
);

CREATE TABLE "SalesTerritory" (
  "TerritoryID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "CountryRegionCode" TEXT NOT NULL,
  "Group" TEXT NOT NULL,
  "SalesYTD" TEXT NOT NULL,
  "SalesLastYear" TEXT NOT NULL,
  "CostYTD" TEXT NOT NULL,
  "CostLastYear" TEXT NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("TerritoryID"),
  FOREIGN KEY ("CountryRegionCode") REFERENCES "CountryRegion" ("CountryRegionCode")
);

CREATE TABLE "SalesTerritoryHistory" (
  "BusinessEntityID" INTEGER NOT NULL,
  "TerritoryID" INTEGER NOT NULL,
  "StartDate" TEXT NOT NULL,
  "EndDate" TEXT,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID", "StartDate", "TerritoryID"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "SalesPerson" ("BusinessEntityID"),
  FOREIGN KEY ("TerritoryID") REFERENCES "SalesTerritory" ("TerritoryID")
);

CREATE TABLE "ScrapReason" (
  "ScrapReasonID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ScrapReasonID")
);

CREATE TABLE "Shift" (
  "ShiftID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "StartTime" TEXT NOT NULL,
  "EndTime" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ShiftID")
);

CREATE TABLE "ShipMethod" (
  "ShipMethodID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "ShipBase" TEXT NOT NULL,
  "ShipRate" TEXT NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ShipMethodID")
);

CREATE TABLE "ShoppingCartItem" (
  "ShoppingCartItemID" INTEGER NOT NULL,
  "ShoppingCartID" TEXT NOT NULL,
  "Quantity" INTEGER NOT NULL,
  "ProductID" INTEGER NOT NULL,
  "DateCreated" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("ShoppingCartItemID"),
  FOREIGN KEY ("ProductID") REFERENCES "Product" ("ProductID")
);

CREATE TABLE "SpecialOffer" (
  "SpecialOfferID" INTEGER NOT NULL,
  "Description" TEXT NOT NULL,
  "DiscountPct" TEXT NOT NULL,
  "Type" TEXT NOT NULL,
  "Category" TEXT NOT NULL,
  "StartDate" TEXT NOT NULL,
  "EndDate" TEXT NOT NULL,
  "MinQty" INTEGER NOT NULL,
  "MaxQty" INTEGER,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("SpecialOfferID")
);

CREATE TABLE "SpecialOfferProduct" (
  "SpecialOfferID" INTEGER NOT NULL,
  "ProductID" INTEGER NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("SpecialOfferID", "ProductID"),
  FOREIGN KEY ("ProductID") REFERENCES "Product" ("ProductID"),
  FOREIGN KEY ("SpecialOfferID") REFERENCES "SpecialOffer" ("SpecialOfferID")
);

CREATE TABLE "StateProvince" (
  "StateProvinceID" INTEGER NOT NULL,
  "StateProvinceCode" TEXT NOT NULL,
  "CountryRegionCode" TEXT NOT NULL,
  "IsOnlyStateProvinceFlag" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "TerritoryID" INTEGER NOT NULL,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("StateProvinceID"),
  FOREIGN KEY ("CountryRegionCode") REFERENCES "CountryRegion" ("CountryRegionCode"),
  FOREIGN KEY ("TerritoryID") REFERENCES "SalesTerritory" ("TerritoryID")
);

CREATE TABLE "Store" (
  "BusinessEntityID" INTEGER NOT NULL,
  "Name" TEXT NOT NULL,
  "SalesPersonID" INTEGER,
  "Demographics" TEXT,
  "rowguid" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "BusinessEntity" ("BusinessEntityID"),
  FOREIGN KEY ("SalesPersonID") REFERENCES "SalesPerson" ("BusinessEntityID")
);

CREATE TABLE "TransactionHistory" (
  "TransactionID" INTEGER NOT NULL,
  "ProductID" INTEGER NOT NULL,
  "ReferenceOrderID" INTEGER NOT NULL,
  "ReferenceOrderLineID" INTEGER NOT NULL,
  "TransactionDate" TEXT NOT NULL,
  "TransactionType" TEXT NOT NULL,
  "Quantity" INTEGER NOT NULL,
  "ActualCost" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("TransactionID"),
  FOREIGN KEY ("ProductID") REFERENCES "Product" ("ProductID")
);

CREATE TABLE "TransactionHistoryArchive" (
  "TransactionID" INTEGER NOT NULL,
  "ProductID" INTEGER NOT NULL,
  "ReferenceOrderID" INTEGER NOT NULL,
  "ReferenceOrderLineID" INTEGER NOT NULL,
  "TransactionDate" TEXT NOT NULL,
  "TransactionType" TEXT NOT NULL,
  "Quantity" INTEGER NOT NULL,
  "ActualCost" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("TransactionID")
);

CREATE TABLE "UnitMeasure" (
  "UnitMeasureCode" TEXT NOT NULL,
  "Name" TEXT NOT NULL,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("UnitMeasureCode")
);

CREATE TABLE "Vendor" (
  "BusinessEntityID" INTEGER NOT NULL,
  "AccountNumber" TEXT NOT NULL,
  "Name" TEXT NOT NULL,
  "CreditRating" INTEGER NOT NULL,
  "PreferredVendorStatus" INTEGER NOT NULL,
  "ActiveFlag" INTEGER NOT NULL,
  "PurchasingWebServiceURL" TEXT,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("BusinessEntityID"),
  FOREIGN KEY ("BusinessEntityID") REFERENCES "BusinessEntity" ("BusinessEntityID")
);

CREATE TABLE "WorkOrder" (
  "WorkOrderID" INTEGER NOT NULL,
  "ProductID" INTEGER NOT NULL,
  "OrderQty" INTEGER NOT NULL,
  "StockedQty" TEXT,
  "ScrappedQty" INTEGER NOT NULL,
  "StartDate" TEXT NOT NULL,
  "EndDate" TEXT,
  "DueDate" TEXT NOT NULL,
  "ScrapReasonID" INTEGER,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("WorkOrderID"),
  FOREIGN KEY ("ProductID") REFERENCES "Product" ("ProductID"),
  FOREIGN KEY ("ScrapReasonID") REFERENCES "ScrapReason" ("ScrapReasonID")
);

CREATE TABLE "WorkOrderRouting" (
  "WorkOrderID" INTEGER NOT NULL,
  "ProductID" INTEGER NOT NULL,
  "OperationSequence" INTEGER NOT NULL,
  "LocationID" INTEGER NOT NULL,
  "ScheduledStartDate" TEXT NOT NULL,
  "ScheduledEndDate" TEXT NOT NULL,
  "ActualStartDate" TEXT,
  "ActualEndDate" TEXT,
  "ActualResourceHrs" TEXT,
  "PlannedCost" TEXT NOT NULL,
  "ActualCost" TEXT,
  "ModifiedDate" TEXT NOT NULL,
  PRIMARY KEY ("WorkOrderID", "ProductID", "OperationSequence"),
  FOREIGN KEY ("LocationID") REFERENCES "Location" ("LocationID"),
  FOREIGN KEY ("WorkOrderID") REFERENCES "WorkOrder" ("WorkOrderID")
);
