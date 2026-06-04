Below is a comprehensive AML schema for U.S. banks, fintechs, lenders, payment companies, broker-dealers, MSBs, crypto/VASP-adjacent platforms, and AML vendors.

It complements the prior KYC/KYB schema. KYC answers “Who is the customer and what risk do they pose?” AML answers “What activity is occurring, is it suspicious or prohibited, how was it detected, how was it investigated, and what regulatory action was taken?”

This schema is grounded in U.S. BSA/AML, FinCEN SAR/CTR filing, FFIEC BSA/AML examination expectations, and OFAC sanctions compliance. FFIEC describes suspicious activity monitoring and reporting as critical internal controls, and states that appropriate policies, procedures, and processes should monitor and identify unusual activity.  ￼ FinCEN requires SARs to be filed electronically through the BSA E-Filing System, and the BSA E-Filing System supports individual and batch filing of BSA forms.  ￼ OFAC also requires blocked and rejected transactions to be reported, generally within 10 days, and provides the OFAC Reporting System for these filings.  ￼

⸻

1. Top-level canonical object

{
  "amlProgram": {
    "schemaVersion": "string",
    "institution": {},
    "customerProfiles": [],
    "accounts": [],
    "transactions": [],
    "counterparties": [],
    "screeningEvents": [],
    "transactionMonitoring": {},
    "alerts": [],
    "cases": [],
    "investigations": [],
    "regulatoryReports": [],
    "ofacActions": [],
    "riskAssessments": [],
    "typologies": [],
    "models": [],
    "rules": [],
    "watchlists": [],
    "qualityAssurance": {},
    "modelGovernance": {},
    "audit": {},
    "extensions": {}
  }
}

⸻

2. Core AML design principles

A bank/vendor-grade AML schema should be:

Event-centric.
AML is driven by activity: transactions, screening events, alerts, cases, investigations, SAR decisions, CTR filings, blocking, rejecting, and periodic reviews.

Customer-aware but not customer-only.
AML must cover customers, non-customers, counterparties, nested parties, beneficiaries, originators, intermediaries, wallets, devices, merchants, and correspondent banking relationships.

Scenario and typology driven.
Monitoring rules should map to typologies such as structuring, funnel accounts, rapid movement of funds, sanctions evasion, trade-based money laundering, elder exploitation, cybercrime, human trafficking, narcotics, terrorist financing, and fraud.

Investigation-first.
The schema should support analyst workflow, evidence, decisions, narratives, escalation, SAR/No-SAR decisions, law-enforcement requests, and examiner review.

Auditable and explainable.
Every alert, model score, disposition, rule threshold, suppression, override, and report decision needs provenance.

Vendor-neutral.
The schema should support Actimize, Oracle FCCM, SAS AML, Quantexa, Feedzai, ComplyAdvantage, NICE, Alloy, Unit21, Hummingbird, Sardine, Chainalysis/TRM/Elliptic-style crypto tools, and custom systems.

⸻

3. Institution and AML program metadata

"institution": {
  "institutionId": "string",
  "legalEntityName": "string",
  "legalEntityIdentifier": "string",
  "primaryRegulator": "OCC | FederalReserve | FDIC | NCUA | FinCEN | SEC | FINRA | CFTC | StateRegulator | Other",
  "charterType": "NationalBank | StateBank | CreditUnion | BrokerDealer | MSB | MoneyTransmitter | FintechPartner | TrustCompany | Other",
  "businessLines": [
    "RetailBanking",
    "CommercialBanking",
    "PrivateBanking",
    "CorrespondentBanking",
    "Mortgage",
    "Card",
    "Payments",
    "Brokerage",
    "Wealth",
    "MerchantServices",
    "Crypto",
    "Lending",
    "Other"
  ],
  "bsaOfficer": {
    "partyId": "string",
    "name": "string",
    "title": "string",
    "email": "string"
  },
  "amlProgramVersion": "string",
  "policyVersion": "string",
  "riskAppetiteVersion": "string",
  "effectiveDate": "date"
}

⸻

4. Customer AML profile

This should reference the KYC/KYB customer profile rather than duplicate all KYC data.

"customerAmlProfile": {
  "customerId": "string",
  "kycProfileId": "string",
  "customerType": "Individual | Business | Trust | Estate | GovernmentEntity | NonProfit | FinancialInstitution | Fund | Other",
  "relationshipStatus": "Prospect | Active | Restricted | Suspended | Closed | Offboarded | Rejected",
  "relationshipStartDate": "date",
  "relationshipManagerId": "string",
  "businessUnit": "string",
  "customerRiskRating": "Low | Medium | High | Prohibited | Unknown",
  "customerRiskScore": "decimal",
  "riskRatingDate": "date",
  "riskRatingMethodologyVersion": "string",
  "dueDiligenceLevel": "Simplified | Standard | Enhanced | Prohibited",
  "expectedActivityProfileId": "string",
  "monitoringSegment": "Retail | SMB | Commercial | PrivateBanking | MSB | Correspondent | Crypto | HighRisk | Other",
  "peerGroup": "string",
  "highRiskIndicators": [
    "PEP",
    "AdverseMedia",
    "HighRiskJurisdiction",
    "CashIntensiveBusiness",
    "MSB",
    "CryptoRelated",
    "ForeignFinancialInstitution",
    "ComplexOwnership",
    "NestedActivity",
    "NonResidentAlien",
    "PrivateBanking",
    "MarijuanaRelatedBusiness",
    "EmbassyConsulate",
    "CharityNonProfit",
    "ImportExport",
    "Other"
  ],
  "restrictions": [
    {
      "restrictionType": "NoWire | NoCash | NoInternational | NoACH | Blocked | Frozen | ExitInProgress | ManualReviewRequired | Other",
      "reason": "string",
      "startDateTime": "datetime",
      "endDateTime": "datetime",
      "approvedBy": "string"
    }
  ]
}

⸻

5. Account schema

"accounts": [
  {
    "accountId": "string",
    "customerId": "string",
    "accountNumberMasked": "string",
    "accountToken": "string",
    "accountType": "Checking | Savings | MoneyMarket | CD | CreditCard | Loan | Mortgage | Brokerage | Wallet | Merchant | Trust | Correspondent | Nostro | Vostro | Other",
    "productCode": "string",
    "currency": "string",
    "openDate": "date",
    "closeDate": "date",
    "status": "Open | Dormant | Restricted | Frozen | Closed | ChargedOff | PendingClosure",
    "ownershipType": "Individual | Joint | Business | Trust | Custodial | Fiduciary | Other",
    "authorizedPartyIds": ["string"],
    "beneficialOwnerPartyIds": ["string"],
    "branchId": "string",
    "countryOfBooking": "string",
    "expectedActivityProfileId": "string",
    "riskRating": "Low | Medium | High | Prohibited | Unknown",
    "riskFlags": ["string"]
  }
]

⸻

6. Transaction schema

This is the backbone of AML.

"transactions": [
  {
    "transactionId": "string",
    "sourceSystemTransactionId": "string",
    "transactionVersion": "integer",
    "accountId": "string",
    "customerId": "string",
    "transactionDateTime": "datetime",
    "postingDate": "date",
    "effectiveDate": "date",
    "transactionType": "CashDeposit | CashWithdrawal | WireIn | WireOut | ACHCredit | ACHDebit | CheckDeposit | CheckWithdrawal | CardPurchase | CardRefund | P2PTransfer | InternalTransfer | BookTransfer | LoanPayment | LoanDisbursement | CryptoDeposit | CryptoWithdrawal | Trade | Fee | Other",
    "direction": "Inbound | Outbound | Internal | Unknown",
    "status": "Pending | Posted | Reversed | Returned | Rejected | Blocked | Cancelled | Failed",
    "amount": "decimal",
    "currency": "string",
    "amountUsdEquivalent": "decimal",
    "fxRate": "decimal",
    "channel": "Branch | ATM | Online | Mobile | WireRoom | ACH | Teller | CardNetwork | API | Partner | Batch | CryptoWallet | Other",
    "branchId": "string",
    "originatingCountry": "string",
    "destinationCountry": "string",
    "originatingInstitution": {},
    "receivingInstitution": {},
    "originator": {},
    "beneficiary": {},
    "counterparties": [],
    "intermediaries": [],
    "paymentRailDetails": {},
    "cashDetails": {},
    "checkDetails": {},
    "cardDetails": {},
    "cryptoDetails": {},
    "tradeFinanceDetails": {},
    "merchantDetails": {},
    "deviceSession": {},
    "narrative": "string",
    "referenceText": "string",
    "purposeOfPayment": "string",
    "relatedTransactionIds": ["string"],
    "monitoringTags": ["string"],
    "screeningStatus": "NotScreened | Clear | PotentialMatch | Blocked | Rejected | PendingReview",
    "amlDisposition": "Normal | Unusual | Suspicious | Exempt | FalsePositive | UnderReview",
    "dataQuality": {
      "completenessScore": "decimal",
      "missingFields": ["string"],
      "normalizationStatus": "Raw | Normalized | Enriched | Failed"
    }
  }
]

⸻

7. Payment rail details

7.1 Wire / funds transfer

"wireDetails": {
  "wireType": "Fedwire | SWIFT | CHIPS | RTP | BookTransfer | International | Other",
  "imad": "string",
  "omad": "string",
  "uetr": "string",
  "swiftMessageType": "MT103 | MT202 | MT202COV | ISO20022_pacs008 | ISO20022_pacs009 | Other",
  "originatorBankBic": "string",
  "beneficiaryBankBic": "string",
  "intermediaryBankBics": ["string"],
  "originatorName": "string",
  "originatorAddress": {},
  "originatorAccountNumberMasked": "string",
  "beneficiaryName": "string",
  "beneficiaryAddress": {},
  "beneficiaryAccountNumberMasked": "string",
  "paymentPurposeCode": "string",
  "remittanceInformation": "string"
}

7.2 ACH

"achDetails": {
  "achStandardEntryClassCode": "CCD | PPD | WEB | TEL | CTX | IAT | POP | ARC | BOC | RCK | Other",
  "odfiRoutingNumber": "string",
  "rdfiRoutingNumber": "string",
  "companyName": "string",
  "companyId": "string",
  "entryDescription": "string",
  "traceNumber": "string",
  "returnCode": "string",
  "iatIndicator": "boolean",
  "addenda": []
}

7.3 Cash

"cashDetails": {
  "cashInAmount": "decimal",
  "cashOutAmount": "decimal",
  "currency": "string",
  "tellerId": "string",
  "branchId": "string",
  "cashTransactionAggregationKey": "string",
  "ctrAggregationCandidateIndicator": "boolean",
  "conductorPartyId": "string",
  "onBehalfOfPartyId": "string",
  "monetaryInstrumentType": "Cash | CashiersCheck | MoneyOrder | TravelersCheck | Other"
}

7.4 Check

"checkDetails": {
  "checkNumber": "string",
  "draweeBankRoutingNumber": "string",
  "payorName": "string",
  "payeeName": "string",
  "remoteDepositIndicator": "boolean",
  "imageAvailableIndicator": "boolean",
  "returnReasonCode": "string",
  "endorsementText": "string"
}

7.5 Card / merchant

"cardDetails": {
  "cardToken": "string",
  "cardNetwork": "Visa | Mastercard | Amex | Discover | Other",
  "mccCode": "string",
  "merchantName": "string",
  "merchantId": "string",
  "terminalId": "string",
  "authorizationCode": "string",
  "cardPresentIndicator": "boolean",
  "crossBorderIndicator": "boolean"
}

7.6 Crypto / blockchain

"cryptoDetails": {
  "assetSymbol": "BTC | ETH | USDC | USDT | Other",
  "assetNetwork": "Bitcoin | Ethereum | Solana | Tron | Polygon | Other",
  "transactionHash": "string",
  "walletAddressFrom": "string",
  "walletAddressTo": "string",
  "hostedWalletIndicator": "boolean",
  "selfHostedWalletIndicator": "boolean",
  "vaspName": "string",
  "blockTimestamp": "datetime",
  "chainAnalyticsProvider": "string",
  "chainRiskScore": "decimal",
  "chainRiskCategories": [
    "SanctionedEntity",
    "Mixer",
    "DarknetMarket",
    "Scam",
    "Ransomware",
    "Gambling",
    "HighRiskExchange",
    "PrivacyCoin",
    "Bridge",
    "PeelChain",
    "Other"
  ],
  "travelRuleMessageId": "string"
}

⸻

8. Counterparty schema

"counterparties": [
  {
    "counterpartyId": "string",
    "counterpartyType": "Individual | Business | FinancialInstitution | Government | Wallet | Merchant | Unknown",
    "name": "string",
    "aliases": ["string"],
    "address": {},
    "country": "string",
    "accountNumberMasked": "string",
    "routingNumber": "string",
    "bic": "string",
    "ibanMasked": "string",
    "walletAddress": "string",
    "relationshipToCustomer": "KnownCustomer | RelatedParty | Vendor | Payroll | Customer | Family | Unknown | Other",
    "counterpartyRiskRating": "Low | Medium | High | Prohibited | Unknown",
    "screeningStatus": "NotScreened | Clear | PotentialMatch | ConfirmedMatch | FalsePositive",
    "firstSeenDate": "date",
    "lastSeenDate": "date",
    "transactionCount": "integer",
    "totalTransactionAmountUsd": "decimal"
  }
]

⸻

9. Screening events: sanctions, watchlists, PEP, adverse media

This overlaps with KYC, but AML needs event-level screening for transactions and counterparties.

"screeningEvents": [
  {
    "screeningEventId": "string",
    "screeningType": "Customer | Counterparty | Transaction | PaymentMessage | Vessel | Goods | WalletAddress | BatchRescreening | Other",
    "screenedEntityType": "Party | Account | Transaction | Counterparty | Wallet | Vessel | Goods | Other",
    "screenedEntityId": "string",
    "screeningDateTime": "datetime",
    "provider": "string",
    "screeningListSetVersion": "string",
    "screeningScope": [
      "OFAC_SDN",
      "OFAC_NonSDN",
      "UN",
      "EU",
      "UK_HMT",
      "Canada",
      "PEP",
      "AdverseMedia",
      "InternalWatchlist",
      "LawEnforcement",
      "CryptoSanctions",
      "Other"
    ],
    "inputAttributes": {
      "name": "string",
      "aliases": ["string"],
      "dateOfBirth": "date",
      "country": "string",
      "address": "string",
      "identifier": "string",
      "freeText": "string"
    },
    "overallStatus": "Clear | PotentialMatch | ConfirmedMatch | FalsePositive | PendingReview | Error",
    "matches": [
      {
        "matchId": "string",
        "listName": "string",
        "listRecordId": "string",
        "matchedName": "string",
        "matchScore": "decimal",
        "matchedFields": ["Name", "DOB", "Country", "Address", "Identifier", "BIC", "Wallet", "Text"],
        "matchStrength": "Weak | Medium | Strong | Exact",
        "program": "Sanctions | PEP | AdverseMedia | Internal | Other",
        "disposition": "Pending | FalsePositive | TrueMatch | Escalated | Cleared",
        "dispositionReason": "string",
        "dispositionedBy": "string",
        "dispositionDateTime": "datetime"
      }
    ],
    "actionTaken": "NoAction | Hold | Block | Reject | Escalate | Release | FileOFACReport | Other"
  }
]

⸻

10. Transaction monitoring

10.1 Monitoring run

"transactionMonitoringRun": {
  "runId": "string",
  "runType": "RealTime | NearRealTime | DailyBatch | WeeklyBatch | MonthlyBatch | Backtest | Lookback | Tuning | Other",
  "runDateTime": "datetime",
  "monitoringSystem": "string",
  "systemVersion": "string",
  "dataWindowStart": "datetime",
  "dataWindowEnd": "datetime",
  "scenarioSetVersion": "string",
  "modelVersion": "string",
  "status": "Started | Completed | Failed | Partial",
  "transactionCountProcessed": "integer",
  "alertsGeneratedCount": "integer",
  "exceptions": []
}

10.2 Scenario / rule definition

"rules": [
  {
    "ruleId": "string",
    "ruleName": "string",
    "ruleType": "Threshold | Velocity | PeerComparison | Network | Behavioral | MachineLearning | Sanctions | Typology | Suppression | Other",
    "description": "string",
    "typologyIds": ["string"],
    "applicableSegments": ["Retail", "Commercial", "PrivateBanking", "MSB", "Crypto", "Correspondent", "Other"],
    "applicableProducts": ["Checking", "Wire", "ACH", "Cash", "Card", "Crypto", "TradeFinance", "Other"],
    "parameters": [
      {
        "parameterName": "string",
        "parameterValue": "string",
        "dataType": "String | Decimal | Integer | Boolean | Date | Duration",
        "effectiveDate": "date",
        "approvedBy": "string"
      }
    ],
    "thresholds": [
      {
        "thresholdName": "string",
        "thresholdValue": "decimal",
        "currency": "string",
        "lookbackPeriodDays": "integer",
        "aggregationLevel": "Customer | Account | Household | Counterparty | Branch | PeerGroup | Wallet | Other"
      }
    ],
    "suppressionLogic": {
      "enabledIndicator": "boolean",
      "suppressionCriteria": "string",
      "suppressionDurationDays": "integer"
    },
    "riskWeight": "decimal",
    "severityMapping": {
      "low": "decimal",
      "medium": "decimal",
      "high": "decimal",
      "critical": "decimal"
    },
    "status": "Draft | Active | Retired | Suspended",
    "validationStatus": "NotValidated | Validated | NeedsReview | Failed",
    "owner": "string",
    "approvalDate": "date"
  }
]

⸻

11. AML typologies

"typologies": [
  {
    "typologyId": "string",
    "typologyName": "Structuring | FunnelAccount | RapidMovementOfFunds | Layering | ShellCompany | TradeBasedMoneyLaundering | HumanTrafficking | ElderExploitation | TerroristFinancing | SanctionsEvasion | FraudProceeds | Cybercrime | Ransomware | TaxEvasion | Narcotics | Corruption | Other",
    "description": "string",
    "redFlags": [
      "Multiple cash deposits below reporting threshold",
      "Funds moved out shortly after receipt",
      "Transactions inconsistent with customer profile",
      "Use of high-risk jurisdictions",
      "Multiple unrelated counterparties",
      "Round-dollar wires",
      "Rapid in-and-out crypto movement"
    ],
    "associatedRules": ["string"],
    "associatedRiskFactors": ["string"],
    "regulatoryReferences": ["string"],
    "status": "Active | Retired | Emerging"
  }
]

⸻

12. Alerts

"alerts": [
  {
    "alertId": "string",
    "sourceSystemAlertId": "string",
    "alertType": "TransactionMonitoring | Sanctions | PEP | AdverseMedia | Fraud | KYCRefresh | LawEnforcement | ManualReferral | Crypto | Other",
    "source": "Rule | Model | Screening | EmployeeReferral | CustomerComplaint | LawEnforcement | ExternalVendor | Other",
    "customerId": "string",
    "accountIds": ["string"],
    "transactionIds": ["string"],
    "counterpartyIds": ["string"],
    "ruleIds": ["string"],
    "typologyIds": ["string"],
    "alertDateTime": "datetime",
    "lookbackStartDate": "date",
    "lookbackEndDate": "date",
    "alertScore": "decimal",
    "severity": "Low | Medium | High | Critical",
    "priority": "Low | Medium | High | Critical",
    "alertStatus": "New | Open | Assigned | InReview | Escalated | Closed | Suppressed | Merged",
    "assignedQueue": "string",
    "assignedTo": "string",
    "slaDueDateTime": "datetime",
    "triggeringFacts": [
      {
        "factType": "ThresholdExceeded | Velocity | Pattern | ScreeningMatch | RiskChange | PeerOutlier | NetworkLink | ManualNote | Other",
        "description": "string",
        "metricName": "string",
        "metricValue": "decimal",
        "thresholdValue": "decimal",
        "supportingTransactionIds": ["string"]
      }
    ],
    "disposition": {
      "dispositionType": "FalsePositive | UnusualButExplained | EscalatedToCase | SARRecommended | NoSAR | Duplicate | Suppressed | Other",
      "reason": "string",
      "decisionedBy": "string",
      "decisionDateTime": "datetime"
    }
  }
]

⸻

13. Case management

"cases": [
  {
    "caseId": "string",
    "sourceCaseId": "string",
    "caseType": "AMLInvestigation | SARInvestigation | SanctionsReview | PEPReview | AdverseMediaReview | CTRReview | FraudLinkedAML | OFACBlocking | LawEnforcementRequest | ExitReview | Other",
    "customerId": "string",
    "relatedPartyIds": ["string"],
    "relatedAccountIds": ["string"],
    "relatedTransactionIds": ["string"],
    "relatedAlertIds": ["string"],
    "relatedScreeningEventIds": ["string"],
    "caseOpenDateTime": "datetime",
    "caseCloseDateTime": "datetime",
    "status": "Open | PendingInfo | PendingReview | Escalated | PendingSAR | PendingOFAC | Closed | Reopened",
    "priority": "Low | Medium | High | Critical",
    "assignedTo": "string",
    "assignedQueue": "string",
    "caseSummary": "string",
    "caseNarrative": "string",
    "suspectedActivityTypes": [
      "MoneyLaundering",
      "Structuring",
      "TerroristFinancing",
      "Fraud",
      "SanctionsEvasion",
      "HumanTrafficking",
      "ElderExploitation",
      "Cybercrime",
      "Ransomware",
      "Narcotics",
      "Corruption",
      "TaxEvasion",
      "Other"
    ],
    "riskFactorsObserved": ["string"],
    "lawEnforcementContactIndicator": "boolean",
    "informationSharing": {
      "section314aMatchIndicator": "boolean",
      "section314bSharedIndicator": "boolean",
      "sharedWithInstitutions": ["string"],
      "sharingDate": "date"
    },
    "actions": [],
    "approvals": [],
    "disposition": {}
  }
]

⸻

14. Investigation details

"investigation": {
  "investigationId": "string",
  "caseId": "string",
  "investigationType": "InitialReview | FullInvestigation | Lookback | NetworkAnalysis | EDDReview | ExitReview | Other",
  "investigatorId": "string",
  "startDateTime": "datetime",
  "endDateTime": "datetime",
  "scope": {
    "customerIds": ["string"],
    "accountIds": ["string"],
    "transactionIds": ["string"],
    "counterpartyIds": ["string"],
    "dateRangeStart": "date",
    "dateRangeEnd": "date",
    "products": ["string"],
    "jurisdictions": ["string"]
  },
  "findings": [
    {
      "findingId": "string",
      "findingType": "SuspiciousPattern | CustomerExplanation | DocumentationGap | SanctionsRisk | NetworkLink | KYCMismatch | ExpectedActivityMismatch | LawEnforcementInfo | Other",
      "description": "string",
      "supportingEvidenceIds": ["string"],
      "confidence": "Low | Medium | High"
    }
  ],
  "customerContact": [
    {
      "contactDateTime": "datetime",
      "contactMethod": "Phone | Email | Branch | Letter | Portal | NotContacted",
      "contactPurpose": "RequestExplanation | RequestDocumentation | VerifyActivity | Other",
      "summary": "string",
      "documentsRequested": ["string"],
      "documentsReceived": ["string"]
    }
  ],
  "evidence": [
    {
      "evidenceId": "string",
      "evidenceType": "TransactionSummary | Statement | WireMessage | CheckImage | KYCRecord | Document | PublicRecord | NewsArticle | BlockchainGraph | Screenshot | AnalystNote | Other",
      "description": "string",
      "source": "Core | LOS | KYC | Vendor | PublicSource | Analyst | Other",
      "storageUri": "string",
      "hash": "string",
      "createdDateTime": "datetime"
    }
  ],
  "recommendation": {
    "recommendationType": "CloseNoSAR | FileSAR | ContinueMonitoring | EDD | RestrictAccount | ExitRelationship | FileOFAC | Other",
    "rationale": "string",
    "recommendedBy": "string",
    "recommendationDateTime": "datetime"
  }
}

⸻

15. SAR support

SAR data should be highly permissioned. FinCEN warns that SAR disclosure is prohibited, including disclosure of information that would reveal a SAR has been filed.  ￼

"sar": {
  "sarId": "string",
  "caseId": "string",
  "bsaEfilingTrackingId": "string",
  "filingInstitutionId": "string",
  "filingType": "Initial | ContinuingActivity | CorrectedAmended | JointFiling",
  "filingStatus": "NotStarted | Draft | PendingApproval | Filed | Accepted | Rejected | Amended | Withdrawn",
  "filingDate": "date",
  "detectionDate": "date",
  "activityStartDate": "date",
  "activityEndDate": "date",
  "continuingActivityIndicator": "boolean",
  "priorSarIds": ["string"],
  "totalSuspiciousAmount": "decimal",
  "suspiciousActivityTypes": [
    "Structuring",
    "MoneyLaundering",
    "TerroristFinancing",
    "Fraud",
    "IdentityTheft",
    "ElderFinancialExploitation",
    "HumanTrafficking",
    "CyberEvent",
    "SanctionsEvasion",
    "Other"
  ],
  "subjectParties": [
    {
      "partyId": "string",
      "subjectRole": "KnownSubject | UnknownSubject | Beneficiary | Conductor | Originator | Business | Other",
      "relationshipToInstitution": "Customer | NonCustomer | Employee | Vendor | Unknown"
    }
  ],
  "involvedAccounts": ["string"],
  "involvedTransactions": ["string"],
  "narrative": {
    "narrativeText": "string",
    "narrativeTemplateVersion": "string",
    "preparedBy": "string",
    "reviewedBy": "string",
    "approvedBy": "string"
  },
  "decision": {
    "sarDecision": "File | DoNotFile | ContinueMonitoring | Escalate",
    "decisionReason": "string",
    "decisionDateTime": "datetime",
    "decisionedBy": "string",
    "approvalChain": [
      {
        "approverId": "string",
        "approvalStatus": "Approved | Rejected | ReturnedForRevision",
        "approvalDateTime": "datetime",
        "comments": "string"
      }
    ]
  },
  "confidentiality": {
    "sarConfidentialIndicator": true,
    "accessGroup": "SARRestricted",
    "disclosureProhibitedIndicator": true
  },
  "retention": {
    "retainUntilDate": "date",
    "legalHoldIndicator": "boolean"
  }
}

⸻

16. CTR support

CTR reporting requires aggregation of cash transactions and parties involved in the transaction. FinCEN provides electronic filing instructions for Currency Transaction Reports, and BSA E-Filing supports BSA forms electronically.  ￼

"ctr": {
  "ctrId": "string",
  "filingInstitutionId": "string",
  "bsaEfilingTrackingId": "string",
  "filingStatus": "NotStarted | Draft | PendingApproval | Filed | Accepted | Rejected | Amended",
  "filingDate": "date",
  "businessDate": "date",
  "aggregationWindow": {
    "startDateTime": "datetime",
    "endDateTime": "datetime"
  },
  "cashInTotal": "decimal",
  "cashOutTotal": "decimal",
  "totalCashAmount": "decimal",
  "currency": "USD",
  "transactions": ["string"],
  "conductors": [
    {
      "partyId": "string",
      "customerIndicator": "boolean",
      "onBehalfOfPartyIds": ["string"],
      "identificationDocumentId": "string"
    }
  ],
  "personsInvolved": [
    {
      "partyId": "string",
      "role": "PersonConductingTransaction | PersonOnWhoseBehalfTransactionConducted | CommonCarrier | Other"
    }
  ],
  "exemption": {
    "exemptCustomerIndicator": "boolean",
    "exemptionId": "string",
    "exemptionType": "PhaseI | PhaseII | Payroll | NonListedBusiness | Other",
    "exemptionVerifiedDate": "date"
  },
  "approval": {
    "preparedBy": "string",
    "approvedBy": "string",
    "approvalDateTime": "datetime"
  },
  "retention": {
    "retainUntilDate": "date",
    "legalHoldIndicator": "boolean"
  }
}

⸻

17. OFAC blocking, rejection, and reporting

"ofacAction": {
  "ofacActionId": "string",
  "relatedScreeningEventId": "string",
  "relatedTransactionId": "string",
  "relatedCaseId": "string",
  "actionType": "Block | Reject | Release | Escalate | LicenseReview | Report",
  "actionDateTime": "datetime",
  "sanctionsProgram": "string",
  "blockedPropertyIndicator": "boolean",
  "rejectedTransactionIndicator": "boolean",
  "blockedAmount": "decimal",
  "currency": "string",
  "blockedAccountId": "string",
  "ofacReportingRequiredIndicator": "boolean",
  "ofacReportType": "InitialBlockedProperty | RejectedTransaction | AnnualBlockedProperty | Other",
  "ofacReportStatus": "NotStarted | Draft | Filed | Accepted | Rejected | Amended",
  "ofacReportFilingDate": "date",
  "ofacReportReferenceNumber": "string",
  "license": {
    "licenseRequiredIndicator": "boolean",
    "licenseNumber": "string",
    "licenseStatus": "Requested | Granted | Denied | Expired | NotApplicable"
  },
  "decision": {
    "decisionedBy": "string",
    "decisionDateTime": "datetime",
    "decisionReason": "string",
    "legalReviewIndicator": "boolean"
  }
}

⸻

18. Customer expected activity profile

"expectedActivityProfile": {
  "expectedActivityProfileId": "string",
  "customerId": "string",
  "effectiveDate": "date",
  "source": "KYC | RelationshipManager | CustomerAttestation | Model | HistoricalBehavior | ManualOverride",
  "expectedMonthlyTransactionCount": "integer",
  "expectedMonthlyVolumeUsd": "decimal",
  "expectedCashInMonthlyUsd": "decimal",
  "expectedCashOutMonthlyUsd": "decimal",
  "expectedWireInMonthlyUsd": "decimal",
  "expectedWireOutMonthlyUsd": "decimal",
  "expectedACHMonthlyUsd": "decimal",
  "expectedCheckMonthlyUsd": "decimal",
  "expectedCardMonthlyUsd": "decimal",
  "expectedCryptoMonthlyUsd": "decimal",
  "expectedInternationalActivityIndicator": "boolean",
  "expectedCountries": ["string"],
  "expectedCounterpartyTypes": ["Individual", "Business", "Government", "FinancialInstitution", "Unknown"],
  "expectedPurposeOfActivity": "string",
  "lastReviewedDate": "date",
  "reviewedBy": "string"
}

⸻

19. Network / entity resolution

Modern AML systems increasingly need network analytics.

"entityResolution": {
  "entityClusterId": "string",
  "clusterType": "CustomerHousehold | BusinessGroup | CounterpartyNetwork | DeviceNetwork | WalletCluster | AddressCluster | PhoneEmailCluster | Other",
  "memberEntities": [
    {
      "entityType": "Customer | Party | Account | Counterparty | Wallet | Device | Address | Phone | Email",
      "entityId": "string",
      "confidenceScore": "decimal",
      "linkReason": "SharedAddress | SharedPhone | SharedDevice | CommonCounterparty | Ownership | Control | WalletHeuristic | Manual | Other"
    }
  ],
  "riskSummary": {
    "clusterRiskRating": "Low | Medium | High | Prohibited | Unknown",
    "clusterRiskScore": "decimal",
    "riskDrivers": ["string"]
  }
}

⸻

20. Model and analytics outputs

"modelScore": {
  "modelScoreId": "string",
  "modelId": "string",
  "modelVersion": "string",
  "entityType": "Customer | Account | Transaction | Counterparty | Case | Cluster",
  "entityId": "string",
  "scoreDateTime": "datetime",
  "score": "decimal",
  "riskBand": "Low | Medium | High | Critical",
  "features": [
    {
      "featureName": "string",
      "featureValue": "decimal|string|boolean",
      "featureImportance": "decimal"
    }
  ],
  "reasonCodes": ["string"],
  "explainability": {
    "method": "SHAP | LIME | RuleContribution | Scorecard | Other",
    "topDrivers": ["string"]
  },
  "decisionUse": "AlertGeneration | Prioritization | Suppression | RiskRating | InvestigationSupport | Other"
}

⸻

21. Model governance

"modelGovernance": {
  "modelId": "string",
  "modelName": "string",
  "modelType": "RulesEngine | LogisticRegression | GradientBoosting | GraphModel | AnomalyDetection | NLP | VendorBlackBox | Other",
  "owner": "string",
  "businessPurpose": "TransactionMonitoring | AlertPrioritization | SanctionsScreening | FraudAMLConvergence | RiskRating | Other",
  "developmentDataPeriod": {
    "startDate": "date",
    "endDate": "date"
  },
  "validation": {
    "validationStatus": "NotValidated | Validated | ConditionallyApproved | Failed | Expired",
    "validationDate": "date",
    "validator": "string",
    "validationReportDocumentId": "string",
    "limitations": ["string"]
  },
  "performanceMetrics": {
    "precision": "decimal",
    "recall": "decimal",
    "falsePositiveRate": "decimal",
    "alertConversionRate": "decimal",
    "sarConversionRate": "decimal",
    "populationStabilityIndex": "decimal",
    "driftScore": "decimal"
  },
  "changeManagement": {
    "changeId": "string",
    "changeDescription": "string",
    "approvedBy": "string",
    "approvalDate": "date",
    "deploymentDate": "date",
    "rollbackPlan": "string"
  }
}

⸻

22. Watchlists and reference data

"watchlist": {
  "watchlistId": "string",
  "watchlistType": "Sanctions | PEP | AdverseMedia | InternalBlacklist | LawEnforcement | HighRiskJurisdiction | HighRiskMCC | HighRiskWallet | HighRiskCounterparty | Other",
  "provider": "OFAC | UN | EU | UK | Internal | Vendor | Other",
  "listVersion": "string",
  "effectiveDateTime": "datetime",
  "records": [
    {
      "recordId": "string",
      "name": "string",
      "aliases": ["string"],
      "entityType": "Individual | Organization | Vessel | Aircraft | Wallet | Country | Other",
      "countries": ["string"],
      "identifiers": [],
      "programs": ["string"],
      "status": "Active | Removed | Archived"
    }
  ]
}

⸻

23. AML risk assessment

"amlRiskAssessment": {
  "riskAssessmentId": "string",
  "assessmentType": "Enterprise | Customer | Product | Channel | Geography | BusinessLine | Vendor | Model | Other",
  "scope": "string",
  "assessmentDate": "date",
  "methodologyVersion": "string",
  "inherentRiskRating": "Low | Medium | High | Critical",
  "controlEffectivenessRating": "Strong | Satisfactory | NeedsImprovement | Weak",
  "residualRiskRating": "Low | Medium | High | Critical",
  "riskFactors": [
    {
      "factorType": "Customer | Product | Service | Geography | Channel | Transaction | Sanctions | Fraud | Vendor | Regulatory | Other",
      "description": "string",
      "inherentRiskScore": "decimal",
      "controlScore": "decimal",
      "residualRiskScore": "decimal"
    }
  ],
  "issues": [
    {
      "issueId": "string",
      "description": "string",
      "severity": "Low | Medium | High | Critical",
      "owner": "string",
      "targetRemediationDate": "date",
      "status": "Open | InProgress | Remediated | AcceptedRisk"
    }
  ],
  "approval": {
    "approvedBy": "string",
    "approvalDate": "date",
    "committee": "string"
  }
}

⸻

24. Quality assurance and testing

FFIEC examination guidance includes transaction testing of suspicious activity monitoring and reporting processes to determine whether policies, procedures, and processes are adequate and effectively implemented.  ￼

"qualityAssurance": {
  "qaReviewId": "string",
  "reviewType": "AlertQA | CaseQA | SARQA | CTRQA | RuleTuning | DataQuality | ModelValidation | Lookback | IndependentTesting | Other",
  "sampleSelectionMethod": "Random | RiskBased | Stratified | Judgmental | FullPopulation",
  "reviewPeriodStart": "date",
  "reviewPeriodEnd": "date",
  "sampledAlertIds": ["string"],
  "sampledCaseIds": ["string"],
  "sampledReportIds": ["string"],
  "reviewerId": "string",
  "reviewDate": "date",
  "findings": [
    {
      "findingId": "string",
      "findingType": "DocumentationGap | IncorrectDisposition | MissedSAR | LateFiling | DataIssue | ControlGap | ModelIssue | Other",
      "severity": "Low | Medium | High | Critical",
      "description": "string",
      "rootCause": "People | Process | Data | Technology | Policy | Vendor | Other",
      "remediationAction": "string",
      "owner": "string",
      "dueDate": "date",
      "status": "Open | InProgress | Closed"
    }
  ],
  "qaOutcome": "Pass | PassWithFindings | Fail | NeedsRemediation"
}

⸻

25. Data lineage and audit

"audit": {
  "createdDateTime": "datetime",
  "createdBy": "string",
  "lastUpdatedDateTime": "datetime",
  "lastUpdatedBy": "string",
  "policyVersion": "string",
  "dataLineage": [
    {
      "fieldPath": "string",
      "source": "CoreBanking | PaymentProcessor | WireSystem | ACHSystem | CardProcessor | KYC | Vendor | Analyst | Model | Calculated | Imported",
      "sourceSystem": "string",
      "sourceRecordId": "string",
      "captureDateTime": "datetime",
      "transformationApplied": "string",
      "confidenceScore": "decimal"
    }
  ],
  "changeHistory": [
    {
      "changeId": "string",
      "entityType": "Transaction | Alert | Case | SAR | CTR | Rule | Model | Watchlist | Other",
      "entityId": "string",
      "fieldPath": "string",
      "oldValueHash": "string",
      "newValueHash": "string",
      "changedBy": "string",
      "changeDateTime": "datetime",
      "changeReason": "string"
    }
  ],
  "accessHistory": [
    {
      "accessId": "string",
      "entityType": "Case | SAR | CTR | OFAC | Customer | Other",
      "entityId": "string",
      "accessedBy": "string",
      "accessDateTime": "datetime",
      "accessPurpose": "Investigation | QA | Audit | Exam | Legal | Support | Other"
    }
  ]
}

⸻

26. Field-level metadata pattern

AML data needs strict provenance, especially for alerts, SARs, OFAC actions, and model decisions.

{
  "value": "any",
  "source": "Core | Wire | ACH | Card | KYC | Vendor | Analyst | Model | Calculated | Imported",
  "sourceSystem": "string",
  "sourceRecordId": "string",
  "capturedDateTime": "datetime",
  "effectiveDate": "date",
  "confidenceScore": "decimal",
  "verifiedIndicator": "boolean",
  "verificationMethod": "System | Analyst | Vendor | Document | ExternalSource | Other",
  "sensitivity": "Public | Internal | Confidential | NPI | SARRestricted | OFACRestricted | LawEnforcementRestricted",
  "retentionClass": "AML | SAR | CTR | OFAC | Case | Transaction | Audit",
  "lastUpdatedDateTime": "datetime",
  "lastUpdatedBy": "string"
}

⸻

27. Recommended relational/domain model

AMLProgram
 ├── Institution
 ├── CustomerAMLProfile
 ├── Account
 ├── Transaction
 │    ├── WireDetails
 │    ├── ACHDetails
 │    ├── CashDetails
 │    ├── CheckDetails
 │    ├── CardDetails
 │    ├── CryptoDetails
 │    └── TradeFinanceDetails
 ├── Counterparty
 ├── ScreeningEvent
 │    └── ScreeningMatch
 ├── TransactionMonitoringRun
 ├── Rule
 ├── Typology
 ├── Alert
 │    ├── TriggeringFact
 │    └── AlertDisposition
 ├── Case
 │    ├── CaseAction
 │    ├── CaseApproval
 │    └── CaseDisposition
 ├── Investigation
 │    ├── Finding
 │    ├── Evidence
 │    └── Recommendation
 ├── SAR
 ├── CTR
 ├── OFACAction
 ├── ExpectedActivityProfile
 ├── EntityResolutionCluster
 ├── ModelScore
 ├── ModelGovernance
 ├── Watchlist
 ├── AMLRiskAssessment
 ├── QualityAssuranceReview
 ├── AuditEvent
 └── Extension

⸻

28. Integration coverage matrix

AML use case	Schema areas required
Real-time transaction screening	Transaction, counterparty, screening event, OFAC action
Batch transaction monitoring	Transaction, customer AML profile, expected activity, rules, alerts
Cash structuring detection	Cash details, aggregation keys, CTR candidates, alerts, cases
Wire monitoring	Wire details, originator, beneficiary, intermediary banks, countries, screening
ACH monitoring	ACH details, ODFI/RDFI, SEC code, return code, velocity
Sanctions interdiction	Screening event, match disposition, block/reject, OFAC report
PEP/adverse media monitoring	Customer profile, screening event, case, EDD trigger
Crypto AML	Crypto details, wallet risk, blockchain analytics, travel rule, screening
Trade-based AML	Trade finance details, goods, vessel, ports, invoices, sanctions screening
SAR investigation	Alerts, case, investigation, evidence, narrative, SAR decision
CTR filing	Cash details, aggregation, conductor, person-on-behalf-of, exemption
Law-enforcement requests	Case, information sharing, restricted evidence, audit
Model governance	Rule, model score, validation, tuning, performance, change control
Examiner/audit support	QA, audit, lineage, rule versions, case dispositions, filings

⸻

29. Key enumerations to standardize

CustomerRiskRating
AccountType
TransactionType
TransactionStatus
TransactionDirection
PaymentRail
Channel
CounterpartyType
ScreeningType
ScreeningStatus
MatchDisposition
OFACActionType
AlertType
AlertStatus
AlertDisposition
CaseType
CaseStatus
CaseDisposition
InvestigationType
FindingType
SARFilingType
SARFilingStatus
SuspiciousActivityType
CTRFilingStatus
CTRPersonRole
RuleType
TypologyType
ModelType
RiskFactorType
QAReviewType
RetentionClass
SensitivityClassification

⸻

30. MVP AML schema vs. enterprise AML schema

MVP AML schema

For a fintech, small bank, or vendor starting point:

CustomerAMLProfile
Account
Transaction
Counterparty
ScreeningEvent
Alert
Case
SARDecision
CTRRecord
OFACAction
Audit

Enterprise AML schema

For a large bank or full AML vendor platform:

CustomerAMLProfile
Account
Transaction
PaymentRailDetails
Counterparty
ScreeningEvent
Watchlist
TransactionMonitoringRun
Rule
Typology
Alert
Case
Investigation
Evidence
SAR
CTR
OFACAction
ExpectedActivityProfile
EntityResolution
ModelScore
ModelGovernance
AMLRiskAssessment
QualityAssurance
IndependentTesting
Audit
DataLineage
Retention
Extensions

⸻

31. Suggested API resource model

POST   /aml/transactions
GET    /aml/transactions/{transactionId}
POST   /aml/transactions/batch
POST   /aml/screening-events
GET    /aml/screening-events/{screeningEventId}
PATCH  /aml/screening-events/{id}/matches/{matchId}
POST   /aml/monitoring-runs
GET    /aml/monitoring-runs/{runId}
POST   /aml/alerts
GET    /aml/alerts/{alertId}
PATCH  /aml/alerts/{alertId}
POST   /aml/alerts/{alertId}/disposition
POST   /aml/cases
GET    /aml/cases/{caseId}
PATCH  /aml/cases/{caseId}
POST   /aml/cases/{caseId}/actions
POST   /aml/cases/{caseId}/evidence
POST   /aml/cases/{caseId}/recommendations
POST   /aml/sars
GET    /aml/sars/{sarId}
PATCH  /aml/sars/{sarId}
POST   /aml/sars/{sarId}/approve
POST   /aml/sars/{sarId}/file
POST   /aml/ctrs
GET    /aml/ctrs/{ctrId}
PATCH  /aml/ctrs/{ctrId}
POST   /aml/ctrs/{ctrId}/file
POST   /aml/ofac-actions
GET    /aml/ofac-actions/{ofacActionId}
POST   /aml/rules
PATCH  /aml/rules/{ruleId}
POST   /aml/models/{modelId}/scores
POST   /aml/qa-reviews
GET    /aml/audit

⸻

32. Recommended AML schema layers

Layer 1: Transaction & Counterparty Data
Accounts, transactions, payment rail details, counterparties, devices, channels.
Layer 2: Screening & Interdiction
Sanctions, PEP, adverse media, watchlists, wallet screening, match disposition, OFAC actions.
Layer 3: Monitoring & Detection
Rules, scenarios, typologies, expected activity, model scores, alerts, peer groups.
Layer 4: Investigation & Case Management
Alerts, cases, evidence, analyst actions, findings, recommendations, approvals.
Layer 5: Regulatory Reporting
SAR, CTR, OFAC reports, BSA E-Filing references, confidentiality, retention.
Layer 6: Governance & Assurance
Model governance, rule tuning, QA, independent testing, audit, lineage, policy versions.

⸻

33. Critical implementation recommendations

Keep KYC and AML connected but separate.
KYC provides identity, risk, expected activity, and beneficial ownership. AML consumes that context but should maintain its own event, alert, case, and reporting records.

Use immutable transaction records.
Transactions may be enriched, normalized, and dispositioned, but the original transaction payload should remain preserved.

Model alerts separately from cases.
Many alerts close as false positives. Some cases contain many alerts. Some SARs arise from multiple cases or lookbacks.

Treat SAR data as restricted.
SAR existence, narrative, decisioning, and related metadata should be segmented with strong access control. FinCEN explicitly prohibits disclosure of SAR filing information.  ￼

Support real-time and batch monitoring.
Sanctions interdiction may need real-time holds; suspicious activity monitoring is often batch or near-real-time.

Store scenario version and model version with every alert.
Without this, historical examiner/audit reconstruction becomes painful.

Build CTR aggregation deliberately.
Cash transaction aggregation is not just a transaction field; it requires business-date grouping, conductor/on-behalf-of parties, exemptions, branch/teller context, and amendment handling.

Do not overfit to one vendor.
Most banks have multiple upstream systems: core, card processor, ACH, wire, teller, digital banking, loan servicing, brokerage, crypto partner, KYC, case-management, and BSA filing tools.

Design for fraud/AML convergence.
Fraud and AML signals increasingly overlap: mule accounts, elder exploitation, romance scams, cybercrime, ransomware, account takeover, synthetic identity, and scam proceeds.

Add data quality controls as first-class objects.
Poor transaction descriptions, missing counterparties, bad country codes, stale KYC, incomplete payment messages, and duplicated transactions can all break AML monitoring.

⸻

34. Final canonical AML domains

A comprehensive AML schema should include:

1. Institution and AML program metadata
2. Customer AML profile
3. Account profile
4. Transaction master
5. Payment rail details
6. Counterparties
7. Originators and beneficiaries
8. Intermediary institutions
9. Device/session/channel data
10. Customer expected activity
11. Screening events
12. Sanctions matches
13. PEP/adverse media matches
14. Watchlists and reference data
15. OFAC blocking/rejection actions
16. Transaction monitoring runs
17. Rules and scenarios
18. Typologies/red flags
19. Model scores
20. Alert generation
21. Alert triage and disposition
22. Case management
23. Investigation findings
24. Evidence management
25. Customer contact / explanation
26. SAR decisioning
27. SAR filing support
28. CTR aggregation
29. CTR filing support
30. Exemptions
31. Law-enforcement requests
32. Section 314(a)/(b) information sharing
33. Entity resolution / network analytics
34. Crypto/blockchain analytics
35. Trade finance AML
36. Model governance
37. Rule tuning
38. Quality assurance
39. Independent testing
40. Enterprise AML risk assessment
41. Data quality controls
42. Audit and lineage
43. Retention and legal hold
44. Access control and confidentiality
45. Extensions

This schema should support the majority of U.S. banks, credit unions, MSBs, fintechs, AML vendors, case-management tools, sanctions-screening platforms, transaction-monitoring engines, and regulatory-reporting workflows.