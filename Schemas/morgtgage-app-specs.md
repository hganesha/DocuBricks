Below is a comprehensive canonical mortgage application schema for the U.S. market designed to support most banks, credit unions, mortgage brokers, POS/LOS vendors, AUS submissions, secondary-market delivery preparation, compliance reporting, and document workflows.

It is intentionally modeled around the dominant U.S. mortgage standards and forms: URLA/Form 1003, Freddie Mac Form 65, ULAD, MISMO v3.x, iLAD, GSE AUS interfaces, HMDA/LAR, and common operational integrations such as credit, appraisal, title, flood, MERS, and eClosing. Fannie Mae notes that URLA is mapped to MISMO v3.4 through ULAD, and MISMO’s iLAD is a broader application dataset covering URLA, GSE AUS interfaces, and legacy Fannie Mae 3.2-style exchanges.  ￼

⸻

1. Design principles

A schema that can support the majority of banks and vendors should be:

Canonical, not screen-based.
It should model the business object, not a particular Form 1003 screen, LOS page, or vendor API.

MISMO-aligned.
Use MISMO-style entities and naming where practical: Loan, Borrower, Party, Role, Asset, Liability, Collateral, Subject Property, Terms, Government Monitoring, Declaration, Closing, Servicing, Investor, Document, and Event. MISMO describes its reference model as an industry-standard organization of data and documentation needed to support mortgage business processes.  ￼

Extensible.
Banks need proprietary overlays, investor conditions, local fees, portfolio rules, CRA/fair-lending attributes, and product-specific extensions.

Multi-borrower and multi-property capable.
A single application may involve multiple borrowers, spouses, non-borrowing spouses, co-signers, trustees, employers, properties, liabilities, REO assets, gift donors, and contacts.

Audit-friendly.
Every field that affects underwriting, compliance, pricing, disclosure, or investor delivery should support provenance, timestamp, source, user/system actor, and version.

Regulatory-ready.
HMDA, ECOA/Reg B, TRID, RESPA, TILA, flood, OFAC, FCRA, SAFE Act, CRA, state-specific rules, and fair-lending monitoring all require structured data. HMDA reporting remains a major regulatory data sink, with CFPB/FFIEC publishing Loan Application Register datasets and resources.  ￼

⸻

2. Top-level canonical object

{
  "mortgageApplication": {
    "applicationId": "string",
    "applicationVersion": "integer",
    "schemaVersion": "string",
    "sourceSystem": {},
    "applicationStatus": {},
    "channel": {},
    "loan": {},
    "parties": [],
    "borrowerGroups": [],
    "subjectProperty": {},
    "otherProperties": [],
    "income": [],
    "employment": [],
    "assets": [],
    "liabilities": [],
    "realEstateOwned": [],
    "expenses": [],
    "credit": {},
    "underwriting": {},
    "pricing": {},
    "feesAndClosingCosts": {},
    "disclosures": [],
    "documents": [],
    "compliance": {},
    "hmda": {},
    "contacts": [],
    "workflow": {},
    "integrations": {},
    "audit": {},
    "extensions": {}
  }
}

⸻

3. Core schema

3.1 Application metadata

"applicationMetadata": {
  "applicationId": "UUID/string",
  "loanApplicationIdentifier": "string",
  "lenderLoanNumber": "string",
  "universalLoanIdentifier": "string",
  "mersMin": "string",
  "applicationReceivedDate": "date",
  "initialSubmissionDate": "date",
  "lastUpdatedDateTime": "datetime",
  "applicationTakenMethod": "Online | Phone | InPerson | Mail | Broker | Correspondent | Other",
  "applicationTakenBy": {
    "userId": "string",
    "name": "string",
    "nmlsId": "string",
    "organizationId": "string"
  },
  "sourceSystem": {
    "systemName": "string",
    "vendorName": "string",
    "systemType": "POS | LOS | PPE | AUS | CRM | CoreBanking | BrokerPortal | Other",
    "externalApplicationId": "string"
  },
  "languagePreference": "string",
  "preferredCommunicationMethod": "Email | Phone | SMS | Mail | Portal",
  "applicationStatus": {
    "currentStatus": "Started | Submitted | InReview | Approved | Suspended | Denied | Withdrawn | Closed | Funded | Cancelled",
    "statusReason": "string",
    "statusDate": "date"
  }
}

Why this matters: banks and vendors need to distinguish started applications, completed applications, withdrawn applications, adverse action cases, and funded loans.

⸻

3.2 Loan structure

"loan": {
  "loanPurpose": "Purchase | Refinance | CashOutRefinance | Construction | ConstructionPermanent | HomeEquity | HELOC | Assumption | Modification | Other",
  "loanType": "Conventional | FHA | VA | USDA | Jumbo | Portfolio | NonQM | Reverse | Other",
  "lienPriority": "FirstLien | SecondLien | Other",
  "mortgageType": "FixedRate | AdjustableRate | Balloon | InterestOnly | GraduatedPayment | Other",
  "amortizationType": "Fixed | ARM | Balloon | InterestOnly | NegativeAmortization | Other",
  "loanProgramName": "string",
  "productCode": "string",
  "investorProductCode": "string",
  "requestedLoanAmount": "decimal",
  "baseLoanAmount": "decimal",
  "totalLoanAmount": "decimal",
  "noteAmount": "decimal",
  "loanTermMonths": "integer",
  "amortizationTermMonths": "integer",
  "interestRatePercent": "decimal",
  "aprPercent": "decimal",
  "rateLock": {
    "isLocked": "boolean",
    "lockDateTime": "datetime",
    "lockExpirationDate": "date",
    "lockPeriodDays": "integer",
    "lockConfirmationNumber": "string"
  },
  "occupancyType": "PrimaryResidence | SecondHome | InvestmentProperty",
  "propertyUsageType": "OwnerOccupied | NonOwnerOccupied",
  "estimatedClosingDate": "date",
  "estimatedFirstPaymentDate": "date",
  "escrowWaiverRequested": "boolean",
  "impoundsRequired": "boolean",
  "prepaymentPenalty": {
    "exists": "boolean",
    "termMonths": "integer",
    "description": "string"
  },
  "balloon": {
    "hasBalloonPayment": "boolean",
    "balloonTermMonths": "integer"
  },
  "arm": {
    "indexType": "SOFR | Treasury | Other",
    "marginPercent": "decimal",
    "initialAdjustmentPeriodMonths": "integer",
    "subsequentAdjustmentPeriodMonths": "integer",
    "initialRateCapPercent": "decimal",
    "periodicRateCapPercent": "decimal",
    "lifetimeRateCapPercent": "decimal",
    "floorRatePercent": "decimal"
  }
}

⸻

3.3 Transaction details

"transactionDetail": {
  "purchasePrice": "decimal",
  "estimatedPropertyValue": "decimal",
  "appraisedValue": "decimal",
  "downPaymentAmount": "decimal",
  "downPaymentPercent": "decimal",
  "downPaymentSourceTypes": [
    "CheckingSavings",
    "Gift",
    "Grant",
    "SecuredBorrowedFunds",
    "UnsecuredBorrowedFunds",
    "SaleOfProperty",
    "EmployerAssistance",
    "Other"
  ],
  "refinance": {
    "refinanceType": "RateTerm | CashOut | LimitedCashOut | Streamline | Other",
    "existingLoanAmount": "decimal",
    "cashOutAmount": "decimal",
    "purposeOfRefinance": "string",
    "propertyAcquiredDate": "date",
    "propertyOriginalCost": "decimal",
    "existingLienPayoffAmount": "decimal"
  },
  "construction": {
    "constructionType": "ConstructionOnly | ConstructionToPermanent",
    "landValue": "decimal",
    "constructionCost": "decimal",
    "completedValue": "decimal",
    "builderName": "string"
  },
  "sellerCreditsAmount": "decimal",
  "interestedPartyContributionsAmount": "decimal",
  "subordinateFinancingAmount": "decimal"
}

⸻

3.4 Parties and roles

Use a generic party model because one person or organization can play multiple roles.

"parties": [
  {
    "partyId": "string",
    "partyType": "Individual | Organization | Trust | Estate | GovernmentEntity",
    "roles": [
      "Borrower",
      "CoBorrower",
      "NonBorrowingSpouse",
      "Guarantor",
      "Seller",
      "LoanOfficer",
      "LoanProcessor",
      "Underwriter",
      "Broker",
      "Lender",
      "Investor",
      "Servicer",
      "SettlementAgent",
      "TitleCompany",
      "Appraiser",
      "RealEstateAgent",
      "Builder",
      "GiftDonor",
      "Employer",
      "InsuranceAgent",
      "Other"
    ],
    "individual": {},
    "organization": {},
    "contactPoints": [],
    "addresses": [],
    "identifiers": [],
    "consents": [],
    "kyc": {},
    "audit": {}
  }
]

⸻

3.5 Borrower / co-borrower

"borrowers": [
  {
    "borrowerId": "string",
    "partyId": "string",
    "borrowerType": "PrimaryBorrower | CoBorrower | Cosigner | NonOccupantBorrower",
    "borrowerPairId": "string",
    "fullName": {
      "firstName": "string",
      "middleName": "string",
      "lastName": "string",
      "suffix": "string"
    },
    "alternateNames": [],
    "dateOfBirth": "date",
    "taxpayerIdentifier": {
      "type": "SSN | ITIN | EIN | ForeignTaxId | None",
      "valueMasked": "string",
      "tokenizedValue": "string"
    },
    "maritalStatus": "Married | Separated | Unmarried | CivilUnion | DomesticPartnership | Unknown",
    "dependents": {
      "count": "integer",
      "ages": ["integer"]
    },
    "citizenshipResidency": {
      "citizenshipStatus": "USCitizen | PermanentResidentAlien | NonPermanentResidentAlien | ForeignNational | Other",
      "visaType": "string",
      "visaExpirationDate": "date"
    },
    "militaryService": {
      "serviceStatus": "ActiveDuty | Veteran | SurvivingSpouse | ReservesNationalGuard | None",
      "vaEligibilityIndicator": "boolean",
      "certificateOfEligibilityStatus": "NotRequested | Requested | Received | NotEligible"
    },
    "housingExpense": {
      "currentHousingType": "Own | Rent | LiveRentFree | Other",
      "monthlyRentAmount": "decimal",
      "presentAddressYears": "decimal"
    },
    "creditAuthorization": {
      "authorized": "boolean",
      "authorizationDateTime": "datetime",
      "authorizationMethod": "Electronic | WetSignature | Verbal | Other"
    },
    "eConsent": {
      "consented": "boolean",
      "consentDateTime": "datetime",
      "ipAddress": "string",
      "deliveryPreference": "Electronic | Paper"
    }
  }
]

⸻

3.6 Addresses

"addresses": [
  {
    "addressId": "string",
    "partyId": "string",
    "addressType": "CurrentResidence | FormerResidence | Mailing | Employer | SubjectProperty | REO | Other",
    "streetLine1": "string",
    "streetLine2": "string",
    "city": "string",
    "stateCode": "string",
    "postalCode": "string",
    "countyName": "string",
    "countryCode": "string",
    "residencyBasis": "Own | Rent | LiveRentFree | Other",
    "startDate": "date",
    "endDate": "date",
    "monthsAtAddress": "integer",
    "isPrimary": "boolean"
  }
]

⸻

3.7 Subject property

"subjectProperty": {
  "propertyId": "string",
  "address": {},
  "propertyType": "SingleFamily | Condo | Cooperative | TwoToFourUnit | ManufacturedHome | PlannedUnitDevelopment | MixedUse | Multifamily | Other",
  "unitCount": "integer",
  "occupancyType": "PrimaryResidence | SecondHome | InvestmentProperty",
  "projectClassification": {
    "isCondo": "boolean",
    "condoProjectName": "string",
    "projectReviewType": "Limited | Full | Waiver | NotApplicable",
    "hoaName": "string",
    "hoaDuesMonthlyAmount": "decimal"
  },
  "legalDescription": "string",
  "parcelIdentifier": "string",
  "county": "string",
  "state": "string",
  "censusTract": "string",
  "msaMdCode": "string",
  "flood": {
    "floodZone": "string",
    "specialFloodHazardAreaIndicator": "boolean",
    "floodInsuranceRequired": "boolean",
    "femaMapNumber": "string",
    "determinationDate": "date"
  },
  "valuation": {
    "estimatedValue": "decimal",
    "appraisedValue": "decimal",
    "valuationMethod": "Appraisal | AVM | DesktopAppraisal | Hybrid | PIW | ACE | Other",
    "appraisalIdentifier": "string",
    "appraisalEffectiveDate": "date"
  },
  "title": {
    "mannerHeld": "SoleOwnership | JointTenants | TenantsInCommon | CommunityProperty | Trust | Other",
    "estateHeldIn": "FeeSimple | Leasehold | Other",
    "leaseholdExpirationDate": "date"
  },
  "insurance": {
    "hazardInsuranceMonthlyAmount": "decimal",
    "floodInsuranceMonthlyAmount": "decimal",
    "windInsuranceMonthlyAmount": "decimal"
  }
}

⸻

3.8 Employment

"employment": [
  {
    "employmentId": "string",
    "borrowerId": "string",
    "employmentType": "CurrentPrimary | CurrentSecondary | Previous | SelfEmployed | Military | Retired | Homemaker | Student | Unemployed | Other",
    "employerName": "string",
    "employerAddress": {},
    "employerPhone": "string",
    "positionTitle": "string",
    "startDate": "date",
    "endDate": "date",
    "monthsOnJob": "integer",
    "yearsInProfession": "decimal",
    "selfEmployedIndicator": "boolean",
    "ownershipInterestPercent": "decimal",
    "businessType": "SoleProprietorship | Partnership | Corporation | SCorp | LLC | Other",
    "verification": {
      "verificationMethod": "VOE | DigitalPayroll | TaxTranscript | BankStatements | Manual | Other",
      "verificationProvider": "string",
      "verificationDate": "date",
      "status": "Pending | Verified | Failed | Waived"
    }
  }
]

⸻

3.9 Income

"income": [
  {
    "incomeId": "string",
    "borrowerId": "string",
    "employmentId": "string",
    "incomeType": "Base | Overtime | Bonus | Commission | Military | SelfEmployment | SocialSecurity | Pension | Retirement | Alimony | ChildSupport | Rental | DividendInterest | CapitalGains | Trust | PublicAssistance | Other",
    "frequency": "Hourly | Weekly | BiWeekly | SemiMonthly | Monthly | Annual | Irregular",
    "amount": "decimal",
    "monthlyAmount": "decimal",
    "isTaxable": "boolean",
    "isUsedToQualify": "boolean",
    "historyMonths": "integer",
    "expectedContinuanceMonths": "integer",
    "documentationType": "Paystub | W2 | TaxReturn | VOE | AwardLetter | BankStatement | Lease | Other",
    "verificationStatus": "Unverified | Verified | Rejected | Waived",
    "confidenceScore": "decimal"
  }
]

⸻

3.10 Assets

"assets": [
  {
    "assetId": "string",
    "borrowerId": "string",
    "assetType": "Checking | Savings | MoneyMarket | CertificateOfDeposit | Retirement | Brokerage | Stocks | Bonds | MutualFunds | LifeInsuranceCashValue | Gift | Grant | EarnestMoney | ProceedsFromSale | BusinessAsset | Other",
    "financialInstitutionName": "string",
    "accountIdentifierMasked": "string",
    "accountOwnershipType": "Individual | Joint | Business | Trust | Other",
    "currentBalance": "decimal",
    "availableBalance": "decimal",
    "amountUsedForTransaction": "decimal",
    "liquidAssetIndicator": "boolean",
    "sourceOfFunds": "string",
    "seasonedIndicator": "boolean",
    "verification": {
      "verificationMethod": "VOA | BankStatement | Manual | OpenBanking | Other",
      "provider": "string",
      "verificationDate": "date",
      "status": "Pending | Verified | Failed | Waived"
    }
  }
]

⸻

3.11 Liabilities

"liabilities": [
  {
    "liabilityId": "string",
    "borrowerId": "string",
    "liabilityType": "MortgageLoan | HELOC | AutoLoan | StudentLoan | CreditCard | Installment | LeasePayment | Alimony | ChildSupport | Taxes | Judgment | Collection | Other",
    "creditorName": "string",
    "accountIdentifierMasked": "string",
    "unpaidBalance": "decimal",
    "monthlyPayment": "decimal",
    "monthsRemaining": "integer",
    "isToBePaidOffAtOrBeforeClosing": "boolean",
    "isOmittedFromDebtRatio": "boolean",
    "omissionReason": "PaidByBusiness | LessThan10Months | ContingentLiability | Deferred | Other",
    "creditReportSource": {
      "bureau": "Equifax | Experian | TransUnion | Other",
      "tradelineId": "string"
    },
    "verificationStatus": "Unverified | Verified | Disputed | Excluded"
  }
]

⸻

3.12 Real estate owned

"realEstateOwned": [
  {
    "reoId": "string",
    "borrowerId": "string",
    "propertyAddress": {},
    "propertyDisposition": "Retain | PendingSale | Sold | ConvertToRental | Other",
    "propertyUsageType": "PrimaryResidence | SecondHome | Investment | Other",
    "currentMarketValue": "decimal",
    "mortgageBalance": "decimal",
    "grossRentalIncomeMonthly": "decimal",
    "netRentalIncomeMonthly": "decimal",
    "taxesInsuranceHoaMonthly": "decimal",
    "associatedMortgageLiabilityIds": ["string"]
  }
]

⸻

3.13 Declarations

URLA declarations are critical and should be structured rather than stored as free text.

"declarations": {
  "borrowerId": "string",
  "outstandingJudgmentsIndicator": "boolean",
  "presentlyDelinquentIndicator": "boolean",
  "partyToLawsuitIndicator": "boolean",
  "priorPropertyForeclosureIndicator": "boolean",
  "deedInLieuIndicator": "boolean",
  "shortSaleIndicator": "boolean",
  "bankruptcyIndicator": "boolean",
  "bankruptcyTypes": [
    "Chapter7",
    "Chapter11",
    "Chapter12",
    "Chapter13"
  ],
  "intentToOccupyIndicator": "boolean",
  "ownershipInterestInPropertyLastThreeYearsIndicator": "boolean",
  "priorPropertyUsageType": "PrimaryResidence | SecondHome | InvestmentProperty | Other",
  "priorPropertyTitleType": "Sole | JointWithSpouse | JointWithOther | Other",
  "borrowedDownPaymentIndicator": "boolean",
  "coMakerEndorserIndicator": "boolean",
  "usCitizenIndicator": "boolean",
  "permanentResidentAlienIndicator": "boolean",
  "primaryResidenceIndicator": "boolean"
}

⸻

3.14 Demographic / government monitoring information

This should be separated from underwriting decisioning and permissioned carefully.

"governmentMonitoring": {
  "borrowerId": "string",
  "collectionMethod": "ApplicantProvided | VisualObservationOrSurname | MailInternetPhone | NotProvided",
  "ethnicity": {
    "hispanicOrLatinoIndicator": "boolean",
    "notHispanicOrLatinoIndicator": "boolean",
    "mexicanIndicator": "boolean",
    "puertoRicanIndicator": "boolean",
    "cubanIndicator": "boolean",
    "otherHispanicOrLatinoDescription": "string",
    "informationNotProvidedIndicator": "boolean",
    "notApplicableIndicator": "boolean"
  },
  "race": {
    "americanIndianOrAlaskaNativeIndicator": "boolean",
    "asianIndicator": "boolean",
    "blackOrAfricanAmericanIndicator": "boolean",
    "nativeHawaiianOrOtherPacificIslanderIndicator": "boolean",
    "whiteIndicator": "boolean",
    "otherDescription": "string",
    "informationNotProvidedIndicator": "boolean",
    "notApplicableIndicator": "boolean"
  },
  "sex": {
    "femaleIndicator": "boolean",
    "maleIndicator": "boolean",
    "informationNotProvidedIndicator": "boolean",
    "notApplicableIndicator": "boolean"
  }
}

The demographic section appears on the standard mortgage application, but applicants may choose not to provide some or all of it.  ￼

⸻

3.15 Credit

"credit": {
  "creditRequestId": "string",
  "authorizationDateTime": "datetime",
  "creditReportType": "TriMerge | SingleBureau | SoftPull | HardPull | Other",
  "creditReportIdentifier": "string",
  "creditVendorName": "string",
  "bureauScores": [
    {
      "borrowerId": "string",
      "bureau": "Equifax | Experian | TransUnion",
      "score": "integer",
      "scoreModel": "FICOClassic | FICO10T | VantageScore | Other",
      "scoreDate": "date"
    }
  ],
  "representativeCreditScore": {
    "borrowerId": "string",
    "score": "integer",
    "selectionMethod": "MiddleOfThree | LowerOfTwo | Single | Other"
  },
  "creditEvents": [
    {
      "eventType": "Bankruptcy | Foreclosure | ShortSale | DeedInLieu | LateMortgagePayment | Collection | ChargeOff | Judgment | TaxLien | Other",
      "eventDate": "date",
      "status": "Open | Satisfied | Discharged | Dismissed | Paid | Other"
    }
  ],
  "fraudAlerts": [],
  "creditFreezeIndicator": "boolean"
}

⸻

3.16 Underwriting

"underwriting": {
  "ausSubmissions": [
    {
      "ausProvider": "DU | LPA | GUS | TOTALScorecard | Proprietary | Other",
      "submissionId": "string",
      "submissionDateTime": "datetime",
      "recommendation": "ApproveEligible | Accept | Refer | Caution | Ineligible | Error | Other",
      "casefileId": "string",
      "findingsDocumentId": "string"
    }
  ],
  "manualUnderwriting": {
    "requiredIndicator": "boolean",
    "reason": "string",
    "underwriterId": "string",
    "decision": "Approved | Suspended | Denied | Counteroffer | Withdrawn | Other",
    "decisionDate": "date"
  },
  "ratios": {
    "housingExpenseRatioPercent": "decimal",
    "totalDebtExpenseRatioPercent": "decimal",
    "ltvPercent": "decimal",
    "cltvPercent": "decimal",
    "hcltvPercent": "decimal",
    "residualIncomeAmount": "decimal"
  },
  "riskAssessment": {
    "riskGrade": "string",
    "riskScore": "decimal",
    "compensatingFactors": ["string"],
    "riskFlags": ["string"]
  },
  "conditions": [
    {
      "conditionId": "string",
      "conditionType": "PriorToApproval | PriorToDocs | PriorToFunding | PostClosing | Other",
      "description": "string",
      "ownerRole": "Borrower | Processor | Underwriter | Closing | Vendor | Other",
      "status": "Open | Satisfied | Waived | Rejected",
      "createdDate": "date",
      "satisfiedDate": "date"
    }
  ]
}

⸻

3.17 Pricing and eligibility

"pricing": {
  "pricingEngine": "string",
  "pricingRequestId": "string",
  "pricingDateTime": "datetime",
  "selectedRate": "decimal",
  "selectedPrice": "decimal",
  "discountPointsPercent": "decimal",
  "lenderCreditAmount": "decimal",
  "loanLevelPriceAdjustments": [
    {
      "adjustmentType": "CreditScore | LTV | Occupancy | PropertyType | CashOut | Units | Other",
      "amount": "decimal",
      "percent": "decimal",
      "description": "string"
    }
  ],
  "eligibilityResults": [
    {
      "investorName": "string",
      "productName": "string",
      "eligible": "boolean",
      "ineligibilityReasons": ["string"]
    }
  ]
}

⸻

3.18 Fees, closing costs, and cash to close

"feesAndClosingCosts": {
  "loanEstimateIssuedDate": "date",
  "closingDisclosureIssuedDate": "date",
  "estimatedCashToClose": "decimal",
  "finalCashToClose": "decimal",
  "fees": [
    {
      "feeId": "string",
      "feeType": "Origination | DiscountPoints | Appraisal | CreditReport | FloodCertification | TaxService | Title | Recording | TransferTax | Prepaids | Escrow | MI | VA | FHA | USDA | Other",
      "feeDescription": "string",
      "amount": "decimal",
      "paidBy": "Borrower | Seller | Lender | Broker | ThirdParty | Other",
      "paidTo": "Lender | Broker | Affiliate | ThirdParty | Government | Other",
      "section": "LE_A | LE_B | LE_C | LE_E | LE_F | LE_G | LE_H | Other",
      "toleranceCategory": "ZeroTolerance | TenPercentCumulative | NoTolerance | NotApplicable",
      "aprIndicator": "boolean"
    }
  ],
  "escrow": {
    "escrowedItems": [
      "PropertyTaxes",
      "HazardInsurance",
      "FloodInsurance",
      "MortgageInsurance",
      "HOA",
      "Other"
    ],
    "initialEscrowDeposit": "decimal",
    "aggregateAdjustment": "decimal"
  }
}

⸻

3.19 Mortgage insurance / guarantees

"mortgageInsurance": {
  "requiredIndicator": "boolean",
  "miType": "BorrowerPaidMonthly | BorrowerPaidSingle | LenderPaid | SplitPremium | FHA_MIP | USDA_Guarantee | VA_FundingFee | None",
  "providerName": "string",
  "coveragePercent": "decimal",
  "monthlyPremiumAmount": "decimal",
  "upfrontPremiumAmount": "decimal",
  "financedPremiumAmount": "decimal",
  "certificateIdentifier": "string",
  "cancellationCriteria": "string"
}

⸻

3.20 Compliance

"compliance": {
  "hmdaReportableIndicator": "boolean",
  "tridApplicableIndicator": "boolean",
  "respaApplicableIndicator": "boolean",
  "tilaApplicableIndicator": "boolean",
  "hoepaStatus": "NotHOEPA | HOEPA | Exempt | Unknown",
  "qualifiedMortgageStatus": "GeneralQM | SmallCreditorQM | BalloonPaymentQM | NonQM | Exempt | Unknown",
  "abilityToRepayStatus": "Pass | Fail | Exempt | Unknown",
  "highPricedMortgageLoanIndicator": "boolean",
  "higherPricedCoveredTransactionIndicator": "boolean",
  "aprSpreadPercent": "decimal",
  "stateCompliance": [
    {
      "stateCode": "string",
      "licenseRequiredIndicator": "boolean",
      "stateSpecificRulesApplied": ["string"]
    }
  ],
  "ofacScreening": {
    "screenedIndicator": "boolean",
    "screeningDate": "date",
    "result": "Clear | PotentialMatch | Match | NotScreened"
  },
  "fairLending": {
    "protectedClassDataSegregatedIndicator": "boolean",
    "pricingExceptionIndicator": "boolean",
    "exceptionReason": "string"
  }
}

⸻

3.21 HMDA / Loan Application Register

HMDA should be a derived/reporting view where possible, not the only system of record.

"hmda": {
  "universalLoanIdentifier": "string",
  "legalEntityIdentifier": "string",
  "applicationDate": "date",
  "loanType": "Conventional | FHA | VA | USDA",
  "loanPurpose": "HomePurchase | HomeImprovement | Refinancing | CashOutRefinancing | Other",
  "preapproval": "Requested | NotRequested | NotApplicable",
  "constructionMethod": "SiteBuilt | ManufacturedHome",
  "occupancyType": "PrincipalResidence | SecondResidence | InvestmentProperty",
  "loanAmount": "decimal",
  "actionTaken": "Originated | ApprovedNotAccepted | Denied | Withdrawn | Incomplete | Purchased | PreapprovalDenied | PreapprovalApprovedNotAccepted",
  "actionTakenDate": "date",
  "propertyAddress": {},
  "censusTract": "string",
  "applicantEthnicity": {},
  "coApplicantEthnicity": {},
  "applicantRace": {},
  "coApplicantRace": {},
  "applicantSex": {},
  "coApplicantSex": {},
  "applicantAge": "integer",
  "coApplicantAge": "integer",
  "income": "decimal",
  "purchaserType": "string",
  "rateSpread": "decimal",
  "hoepaStatus": "string",
  "lienStatus": "string",
  "denialReasons": [],
  "totalLoanCosts": "decimal",
  "totalPointsAndFees": "decimal",
  "originationCharges": "decimal",
  "discountPoints": "decimal",
  "lenderCredits": "decimal",
  "interestRate": "decimal",
  "prepaymentPenaltyTerm": "integer",
  "debtToIncomeRatio": "string",
  "combinedLoanToValueRatio": "decimal",
  "loanTerm": "integer",
  "introductoryRatePeriod": "integer",
  "negativeAmortizationIndicator": "boolean",
  "interestOnlyPaymentIndicator": "boolean",
  "balloonPaymentIndicator": "boolean",
  "otherNonAmortizingFeaturesIndicator": "boolean",
  "manufacturedHomeSecuredPropertyType": "string",
  "manufacturedHomeLandPropertyInterest": "string",
  "totalUnits": "integer",
  "multifamilyAffordableUnits": "integer",
  "submissionOfApplication": "string",
  "initiallyPayableToInstitution": "boolean",
  "automatedUnderwritingSystem": [],
  "ausResult": []
}

Federal agencies have historically identified a subset of HMDA fields as key fields for compliance validation, but institutions required to report full HMDA data still need broader LAR support.  ￼

⸻

3.22 Documents

"documents": [
  {
    "documentId": "string",
    "documentType": "URLA | CreditReport | Paystub | W2 | TaxReturn | BankStatement | PurchaseContract | Appraisal | TitleCommitment | LE | CD | Note | MortgageDeedOfTrust | ClosingPackage | AUSFindings | VOE | VOA | VOD | Insurance | FloodCertificate | Other",
    "documentName": "string",
    "borrowerId": "string",
    "relatedEntityType": "Loan | Borrower | Asset | Income | Property | Closing | Compliance | Other",
    "relatedEntityId": "string",
    "source": "BorrowerUpload | Vendor | LOS | eSign | Email | Scan | API | Other",
    "receivedDateTime": "datetime",
    "status": "Requested | Received | Accepted | Rejected | Expired | Waived",
    "classificationConfidence": "decimal",
    "extractedData": {},
    "fileMetadata": {
      "mimeType": "string",
      "fileSizeBytes": "integer",
      "hash": "string",
      "storageUri": "string"
    },
    "signatures": [
      {
        "signerPartyId": "string",
        "signatureType": "Electronic | Wet | RemoteOnlineNotary | InPersonElectronicNotary",
        "signedDateTime": "datetime",
        "signatureProvider": "string"
      }
    ]
  }
]

⸻

3.23 Disclosures and consents

"disclosures": [
  {
    "disclosureId": "string",
    "disclosureType": "LoanEstimate | ClosingDisclosure | IntentToProceed | ECOA | FCRA | ServicingDisclosure | AffiliatedBusinessArrangement | StateDisclosure | PrivacyNotice | Other",
    "issuedDateTime": "datetime",
    "deliveryMethod": "Electronic | Mail | InPerson | Other",
    "deliveryStatus": "Sent | Delivered | Viewed | Consented | Signed | Failed",
    "recipientPartyIds": ["string"],
    "signatureRequiredIndicator": "boolean",
    "signedDateTime": "datetime",
    "documentId": "string"
  }
]

⸻

3.24 Closing and funding

"closing": {
  "closingType": "Wet | Hybrid | FullEClosing | RemoteOnlineNotary | InPersonElectronicNotary",
  "settlementAgentPartyId": "string",
  "titleCompanyPartyId": "string",
  "closingDate": "date",
  "fundingDate": "date",
  "disbursementDate": "date",
  "rescission": {
    "rescissionApplicableIndicator": "boolean",
    "rescissionStartDate": "date",
    "rescissionEndDate": "date",
    "rescissionWaivedIndicator": "boolean"
  },
  "wireInstructions": {
    "recipientName": "string",
    "bankName": "string",
    "routingNumberMasked": "string",
    "accountNumberMasked": "string",
    "verifiedIndicator": "boolean",
    "verificationMethod": "CallBack | Vendor | Manual | Other"
  },
  "recording": {
    "recordingJurisdiction": "string",
    "recordingDate": "date",
    "instrumentNumber": "string",
    "book": "string",
    "page": "string"
  }
}

⸻

3.25 Post-closing, delivery, servicing, MERS

MERS is widely used for tracking servicing rights and beneficial ownership interests in loans secured by real estate; its system provides a national electronic database for these transfers.  ￼

"postClosing": {
  "loanBoardingStatus": "Pending | Boarded | Failed | NotApplicable",
  "servicerPartyId": "string",
  "investorPartyId": "string",
  "mers": {
    "mersRegisteredIndicator": "boolean",
    "mersMortgageIdentificationNumber": "string",
    "registrationDate": "date",
    "momLoanIndicator": "boolean",
    "servicerOrgId": "string",
    "investorOrgId": "string"
  },
  "delivery": {
    "deliveryInvestor": "FannieMae | FreddieMac | GinnieMae | FHA | VA | USDA | PrivateInvestor | Portfolio | Other",
    "deliveryStatus": "NotStarted | InProgress | Delivered | Purchased | Suspended | Rejected",
    "deliveryDate": "date",
    "commitmentNumber": "string",
    "poolNumber": "string"
  },
  "custody": {
    "documentCustodianPartyId": "string",
    "collateralFileStatus": "Pending | Shipped | Received | Certified | Exception",
    "noteStatus": "OriginalWetNote | eNote | LostNoteAffidavit | Other"
  }
}

⸻

4. Recommended relational model

For a bank-grade implementation, I would avoid one giant table. Use a canonical entity model like this:

MortgageApplication
 ├── Loan
 ├── LoanTerms
 ├── TransactionDetail
 ├── Party
 │    ├── Individual
 │    ├── Organization
 │    ├── PartyRole
 │    ├── ContactPoint
 │    └── Address
 ├── Borrower
 │    ├── Employment
 │    ├── Income
 │    ├── Asset
 │    ├── Liability
 │    ├── Declaration
 │    └── GovernmentMonitoring
 ├── Property
 │    ├── SubjectProperty
 │    ├── Valuation
 │    ├── Flood
 │    ├── Title
 │    └── Insurance
 ├── REOProperty
 ├── CreditReport
 ├── AUSSubmission
 ├── UnderwritingDecision
 ├── Condition
 ├── PricingResult
 ├── Fee
 ├── Disclosure
 ├── Document
 ├── ComplianceResult
 ├── HMDARecord
 ├── Closing
 ├── PostClosingDelivery
 ├── IntegrationEvent
 └── AuditEvent

⸻

5. Key enumerations banks/vendors should standardize

At minimum, standardize these enumerations:

ApplicationStatus
LoanPurpose
LoanType
LienPriority
OccupancyType
PropertyType
AmortizationType
IncomeType
AssetType
LiabilityType
EmploymentType
CitizenshipResidencyType
MaritalStatus
MilitaryServiceStatus
DeclarationQuestionType
DemographicCollectionMethod
AUSProvider
AUSRecommendation
ConditionType
ConditionStatus
FeeType
DisclosureType
DocumentType
ActionTaken
DenialReason
HMDAReportability
ClosingType
DeliveryInvestor
ServicingStatus

Where possible, map values to MISMO, ULAD, URLA, HMDA, GSE AUS, and investor-specific code lists rather than inventing new internal-only values.

⸻

6. Integration coverage matrix

Integration / use case	Schema areas needed
POS application intake	Borrower, property, loan purpose, income, assets, liabilities, declarations, eConsent
LOS processing	Full canonical application, documents, conditions, workflow
Credit pull	Borrower identity, address history, authorization, credit report
AUS: DU/LPA/GUS/TOTAL	Borrower, income, asset, liability, property, loan terms, declarations
Pricing/PPE	Credit score, LTV/CLTV, occupancy, product, property type, lock data
Appraisal	Subject property, transaction, contacts, loan purpose
Title/settlement	Property, parties, closing, vesting, liens, fees
TRID disclosures	Loan terms, fees, contacts, property, timing events
HMDA	Application, action, loan, property, demographics, pricing, AUS
eClosing/eNote	Documents, signatures, closing, notary, MERS/eRegistry
Servicing boarding	Loan terms, escrow, borrower, property, payment, investor, MERS
Secondary delivery	Investor, loan terms, collateral, MI, AUS, delivery status

⸻

7. Field-level metadata every serious implementation should add

For regulated mortgage data, each important field should support metadata:

{
  "value": "any",
  "source": "Borrower | CreditReport | AUS | LOSUser | Vendor | DocumentOCR | Calculated | Imported",
  "sourceSystem": "string",
  "confidence": "decimal",
  "effectiveDate": "date",
  "createdDateTime": "datetime",
  "createdBy": "string",
  "lastUpdatedDateTime": "datetime",
  "lastUpdatedBy": "string",
  "verifiedIndicator": "boolean",
  "verificationMethod": "string",
  "sensitiveDataClassification": "Public | Internal | Confidential | Restricted | NPI | GovernmentMonitoring",
  "auditRequiredIndicator": "boolean"
}

This is especially important for income, assets, liabilities, credit scores, demographic data, compliance fields, AUS results, fees, disclosures, and underwriting decisions.

⸻

8. Minimal viable schema vs. enterprise schema

MVP schema

A vendor building a POS or prequalification flow can start with:

Application
Borrower
Address
Employment
Income
Asset
Liability
SubjectProperty
Loan
Declarations
CreditAuthorization
Documents
Status

Enterprise bank schema

A bank-grade platform should include everything in MVP plus:

GovernmentMonitoring
HMDA
AUSSubmission
Pricing
Fees
Disclosures
Compliance
Conditions
Appraisal
Title
Flood
Insurance
Closing
Funding
PostClosing
MERS
InvestorDelivery
ServicingBoarding
Audit
FieldProvenance
VendorIntegrationEvents

⸻

9. Suggested API resource model

POST   /mortgage-applications
GET    /mortgage-applications/{applicationId}
PATCH  /mortgage-applications/{applicationId}
POST   /mortgage-applications/{id}/borrowers
PATCH  /mortgage-applications/{id}/borrowers/{borrowerId}
POST   /mortgage-applications/{id}/assets
POST   /mortgage-applications/{id}/liabilities
POST   /mortgage-applications/{id}/income
POST   /mortgage-applications/{id}/employment
POST   /mortgage-applications/{id}/credit-authorizations
POST   /mortgage-applications/{id}/credit-reports
POST   /mortgage-applications/{id}/aus-submissions
POST   /mortgage-applications/{id}/pricing-requests
POST   /mortgage-applications/{id}/documents
POST   /mortgage-applications/{id}/disclosures
POST   /mortgage-applications/{id}/conditions
PATCH  /mortgage-applications/{id}/conditions/{conditionId}
GET    /mortgage-applications/{id}/hmda-record
POST   /mortgage-applications/{id}/closing
POST   /mortgage-applications/{id}/delivery

⸻

10. Canonical schema package recommendation

For maximum vendor/bank interoperability, I would package the schema into four layers:

Layer 1: Intake Schema
URLA-style application data, borrower, property, income, asset, liability, declarations.
Layer 2: Decisioning Schema
Credit, AUS, underwriting, ratios, pricing, eligibility, conditions.
Layer 3: Compliance & Disclosure Schema
HMDA, TRID, ATR/QM, HOEPA, ECOA, disclosures, demographic monitoring.
Layer 4: Closing, Delivery & Servicing Schema
Fees, CD, closing, funding, eSign/eNote, MERS, investor delivery, servicing boarding.

This layered approach lets a fintech POS vendor implement Layer 1 first, while a full LOS/core banking platform can support all four.

⸻

11. Practical implementation recommendations

Use MISMO/iLAD as the canonical external mapping baseline, not a proprietary LOS export. MISMO iLAD is specifically intended to replace many peer-to-peer application data exchanges that historically used the Fannie Mae 3.2 file as a de facto standard.  ￼

Maintain separate logical domains for application intake, underwriting, compliance, closing, and servicing. Do not overload a single borrower or loan table with hundreds of nullable fields.

Treat HMDA as a reporting projection from canonical data, with manual override and audit support.

Keep government monitoring data permissioned and segregated from underwriting decision workflows.

Add field provenance from the beginning. It is very difficult to retrofit source-of-truth tracking after integrations with credit, payroll, bank verification, AUS, OCR, and LOS users are already live.

Support extension objects at every major entity:

"extensions": {
  "vendorSpecific": {},
  "investorSpecific": {},
  "bankSpecific": {},
  "stateSpecific": {},
  "experimental": {}
}

Use event sourcing or immutable audit trails for key actions: application submitted, credit authorized, credit pulled, LE issued, intent to proceed received, AUS submitted, underwriting decisioned, CD issued, closing docs signed, funded, shipped, purchased, boarded.

⸻

12. Final recommended canonical domains

A comprehensive U.S. mortgage application schema should include these domains:

1. Application metadata
2. Loan purpose and terms
3. Transaction detail
4. Borrowers and borrower groups
5. Parties and roles
6. Contact information
7. Address history
8. Subject property
9. Other owned real estate
10. Employment
11. Income
12. Assets
13. Liabilities
14. Housing expenses
15. Declarations
16. Demographic / government monitoring
17. Credit authorization and credit report
18. AUS / underwriting
19. Product eligibility
20. Pricing and rate lock
21. Conditions
22. Fees and cash to close
23. Disclosures and consents
24. Documents and OCR/extraction
25. Compliance
26. HMDA
27. Appraisal / valuation
28. Flood
29. Title
30. Insurance
31. Closing
32. Funding
33. MERS / eNote / registry
34. Investor delivery
35. Servicing boarding
36. Workflow
37. Integration events
38. Audit and provenance
39. Security / privacy classification
40. Extensions

This structure should support the majority of U.S. banks, credit unions, independent mortgage banks, brokers, POS vendors, LOS vendors, AUS/PPE integrations, compliance reporting, closing platforms, and post-closing delivery workflows.