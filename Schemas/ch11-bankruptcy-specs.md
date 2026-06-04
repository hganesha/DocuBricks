Below is a comprehensive canonical schema for U.S. Chapter 11 bankruptcy filings and case administration. It is designed for law firms, debtor advisors, claims agents, bankruptcy courts, restructuring platforms, lenders, distressed-debt investors, trustees, U.S. Trustee reporting workflows, and vendor systems.

It covers:

petition preparation, debtor metadata, affiliates, creditors, schedules, statements of financial affairs, executory contracts, claims, noticing, docketing, first-day motions, DIP financing, cash collateral, monthly operating reports, plan/disclosure statement, voting, confirmation, distributions, post-confirmation reporting, and audit.

This is not legal advice; it is a data architecture reference.

⸻

1. Standards and source anchors

A U.S. Chapter 11 schema should be grounded in:

U.S. Bankruptcy Court official forms.
The U.S. Courts maintain official bankruptcy forms, including Chapter 11-related voluntary petition forms, attachments, creditor lists, notices, schedules, statements, and proof-of-claim forms. Official Bankruptcy Forms are approved by the Judicial Conference and must be used under Bankruptcy Rule 9009.  ￼

Federal Rules of Bankruptcy Procedure.
Rule 3016 governs Chapter 11 plans and disclosure statements, including that a Chapter 11 plan or modification must be dated and identify the proposing entity.  ￼ Rule 2002 governs notices, including various notices to creditors, equity security holders, and other parties in Chapter 11 cases.  ￼

PACER / CM/ECF court records.
PACER provides electronic public access to federal court records and more than one billion documents filed in federal courts; a case schema should therefore preserve court, case, docket, document, filing, and ECF metadata.  ￼

U.S. Trustee Program operating reports.
The U.S. Trustee Program requires Chapter 11 debtors-in-possession and trustees, other than small business and Subchapter V cases, to file monthly operating reports and post-confirmation reports using uniform, data-embedded forms in districts where the U.S. Trustee Program operates.  ￼

Chapter 11 process basics.
Chapter 11 generally allows a business debtor, and sometimes an individual debtor, to reorganize or liquidate under court supervision; the U.S. trustee monitors the debtor in possession’s business operations and submission of operating reports and fees.  ￼

⸻

2. Top-level canonical object

{
  "chapter11Case": {
    "caseMetadata": {},
    "debtors": [],
    "jointAdministration": {},
    "venueAndJurisdiction": {},
    "professionals": [],
    "partiesInInterest": [],
    "creditors": [],
    "equityHolders": [],
    "assets": [],
    "liabilities": [],
    "schedules": {},
    "statementOfFinancialAffairs": {},
    "executoryContractsAndLeases": [],
    "firstDayRelief": {},
    "cashManagement": {},
    "dipFinancing": {},
    "cashCollateral": {},
    "claimsRegister": {},
    "noticing": {},
    "docket": {},
    "motionsAndOrders": [],
    "adversaryProceedings": [],
    "avoidanceActions": [],
    "operatingReports": [],
    "planAndDisclosureStatement": {},
    "solicitationAndVoting": {},
    "confirmation": {},
    "distributions": [],
    "postConfirmation": {},
    "caseClosing": {},
    "compliance": {},
    "audit": {},
    "extensions": {}
  }
}

⸻

3. Core design principles

A good Chapter 11 schema should be:

Case-centric and debtor-aware.
One Chapter 11 proceeding may involve many affiliated debtors, jointly administered cases, separate estates, separate schedules, separate claims, and consolidated plan treatment.

Court/docket-native.
Every material event should link to court, case number, docket number, filing party, document, hearing, objection deadline, order, and service information.

Creditor- and claim-centric.
Chapter 11 administration depends on creditor matrices, scheduled claims, filed proofs of claim, amended claims, transferred claims, objections, allowed claims, disputed claims, voting classes, and distributions.

Estate-accounting ready.
The schema must support assets, liabilities, cash, DIP budgets, professional fees, monthly operating reports, post-confirmation reports, and distributions.

Plan-treatment aware.
Claims and interests must map into plan classes, impaired/unimpaired status, voting eligibility, treatment, recovery, and distribution mechanics.

Audit-friendly.
Court filings, claims, ballots, notices, professional invoices, and distribution decisions must be traceable.

⸻

4. Case metadata

"caseMetadata": {
  "caseId": "string",
  "courtCaseNumber": "string",
  "leadCaseNumber": "string",
  "chapter": "11",
  "subchapterVIndicator": "boolean",
  "smallBusinessCaseIndicator": "boolean",
  "singleAssetRealEstateIndicator": "boolean",
  "caseTitle": "string",
  "court": {
    "courtId": "string",
    "courtName": "string",
    "district": "string",
    "division": "string",
    "state": "string",
    "cmEcfCourtCode": "string"
  },
  "judge": {
    "judgeId": "string",
    "name": "string"
  },
  "filingType": "Voluntary | Involuntary | Converted | Transferred",
  "petitionDate": "date",
  "orderForReliefDate": "date",
  "conversionDate": "date",
  "dismissalDate": "date",
  "closingDate": "date",
  "reopeningDate": "date",
  "caseStatus": "Draft | Filed | Active | Confirmed | Effective | Dismissed | Converted | Closed | Reopened",
  "natureOfBusiness": "string",
  "naicsCode": "string",
  "primaryIndustry": "string",
  "caseComplexity": "MegaCase | Complex | Standard | SmallBusiness | SubchapterV",
  "claimsAgentAppointedIndicator": "boolean",
  "claimsAgentName": "string",
  "pacerUrl": "string",
  "claimsAgentWebsiteUrl": "string"
}

⸻

5. Debtor schema

"debtors": [
  {
    "debtorId": "string",
    "caseNumber": "string",
    "isLeadDebtor": "boolean",
    "debtorType": "Corporation | LLC | Partnership | Individual | Trust | NonProfit | GovernmentEntity | Other",
    "legalName": "string",
    "dbaNames": ["string"],
    "formerNames": [
      {
        "name": "string",
        "usedFromDate": "date",
        "usedToDate": "date"
      }
    ],
    "taxIdentifiers": [
      {
        "type": "EIN | SSN | ITIN | ForeignTaxId | Other",
        "maskedValue": "string",
        "issuingCountry": "string"
      }
    ],
    "addresses": [
      {
        "addressType": "PrincipalPlaceOfBusiness | Mailing | RegisteredAgent | Service | Former | Other",
        "streetLine1": "string",
        "streetLine2": "string",
        "city": "string",
        "state": "string",
        "postalCode": "string",
        "country": "string"
      }
    ],
    "businessDescription": "string",
    "ownership": {
      "parentDebtorId": "string",
      "ultimateParentName": "string",
      "organizationalStructureDescription": "string"
    },
    "authorizedSigner": {
      "name": "string",
      "title": "string",
      "authorizationDocumentId": "string"
    },
    "petitionForm": {
      "officialForm": "B101 | B201 | B201A | Other",
      "documentId": "string",
      "signedDate": "date",
      "filedDate": "date"
    },
    "estimatedAssetsRange": "0-50K | 50K-100K | 100K-500K | 500K-1M | 1M-10M | 10M-50M | 50M-100M | 100M-500M | 500M-1B | 1B-10B | 10BPlus",
    "estimatedLiabilitiesRange": "same-enum-as-assets",
    "estimatedCreditorCountRange": "1-49 | 50-99 | 100-199 | 200-999 | 1000-5000 | 5001-10000 | 10000Plus"
  }
]

⸻

6. Joint administration and affiliated cases

"jointAdministration": {
  "jointAdministrationRequestedIndicator": "boolean",
  "jointAdministrationGrantedIndicator": "boolean",
  "leadDebtorId": "string",
  "leadCaseNumber": "string",
  "memberDebtorCaseNumbers": ["string"],
  "orderDocketNumber": "string",
  "proceduralConsolidationIndicator": "boolean",
  "substantiveConsolidationRequestedIndicator": "boolean",
  "substantiveConsolidationGrantedIndicator": "boolean",
  "relatedCases": [
    {
      "relatedCaseId": "string",
      "caseNumber": "string",
      "court": "string",
      "relationshipType": "Affiliate | Parent | Subsidiary | RelatedAdversary | PriorBankruptcy | ForeignProceeding | Other",
      "status": "Active | Closed | Dismissed | Converted | Unknown"
    }
  ]
}

⸻

7. Venue and jurisdiction

"venueAndJurisdiction": {
  "venueBasis": [
    "Domicile",
    "Residence",
    "PrincipalPlaceOfBusiness",
    "PrincipalAssets",
    "AffiliateCasePending",
    "Other"
  ],
  "venueDistrict": "string",
  "jurisdictionStatement": "string",
  "foreignProceedingIndicator": "boolean",
  "chapter15RelatedIndicator": "boolean",
  "principalAssetsLocation": "string",
  "principalPlaceOfBusinessLocation": "string",
  "venueChallengeFiledIndicator": "boolean",
  "venueTransferMotionDocketNumber": "string"
}

⸻

8. Professionals and fiduciaries

"professionals": [
  {
    "professionalId": "string",
    "partyId": "string",
    "role": "DebtorCounsel | ConflictsCounsel | FinancialAdvisor | InvestmentBanker | ClaimsAgent | NoticingAgent | Auctioneer | RealEstateBroker | TaxAdvisor | Auditor | CommitteeCounsel | CommitteeFinancialAdvisor | Trustee | Examiner | Ombudsman | Other",
    "firmName": "string",
    "leadProfessionalName": "string",
    "retentionApplicationDocketNumber": "string",
    "retentionOrderDocketNumber": "string",
    "retentionEffectiveDate": "date",
    "retentionStatus": "Proposed | Approved | Denied | Withdrawn | Terminated",
    "compensationArrangement": "Hourly | FlatFee | Contingency | SuccessFee | MonthlyFee | Other",
    "feeApplications": [
      {
        "feeApplicationId": "string",
        "periodStart": "date",
        "periodEnd": "date",
        "feesRequested": "decimal",
        "expensesRequested": "decimal",
        "feesAllowed": "decimal",
        "expensesAllowed": "decimal",
        "docketNumber": "string",
        "orderDocketNumber": "string",
        "status": "Filed | Objected | Approved | Reduced | Denied | Paid"
      }
    ]
  }
]

⸻

9. Parties in interest

"partiesInInterest": [
  {
    "partyId": "string",
    "partyType": "Individual | Organization | Government | FinancialInstitution | Committee | Trustee | EquityHolder | Landlord | Vendor | Customer | Employee | Insurer | TaxAuthority | Other",
    "name": "string",
    "roles": [
      "Debtor",
      "Creditor",
      "EquityHolder",
      "SecuredLender",
      "DIPLender",
      "PrepetitionAgent",
      "IndentureTrustee",
      "Landlord",
      "ContractCounterparty",
      "Employee",
      "Retiree",
      "CommitteeMember",
      "U.S.Trustee",
      "StateRegulator",
      "TaxAuthority",
      "ClaimsAgent",
      "Other"
    ],
    "addresses": [],
    "contactPoints": [],
    "taxIdentifierMasked": "string",
    "insiderIndicator": "boolean",
    "relatedDebtorIds": ["string"],
    "servicePreferences": {
      "serviceMethod": "ECF | Email | Mail | Overnight | PersonalService | Publication | Other",
      "email": "string",
      "noticeOnlyIndicator": "boolean"
    }
  }
]

⸻

10. Creditors and creditor matrix

"creditors": [
  {
    "creditorId": "string",
    "partyId": "string",
    "debtorId": "string",
    "creditorName": "string",
    "creditorType": "Secured | PriorityUnsecured | GeneralUnsecured | Trade | Bondholder | Landlord | LitigationClaimant | TaxAuthority | Employee | Retiree | Customer | Other",
    "insiderIndicator": "boolean",
    "matrixAddress": {},
    "noticeAddress": {},
    "paymentAddress": {},
    "claimAmountScheduled": "decimal",
    "claimStatusScheduled": "Contingent | Unliquidated | Disputed | Undisputed | Unknown",
    "securedIndicator": "boolean",
    "collateralDescription": "string",
    "priorityBasis": "Wages | Taxes | Deposits | DomesticSupport | Administrative | Other",
    "top20UnsecuredIndicator": "boolean",
    "committeeEligibleIndicator": "boolean",
    "mailingMatrixSource": "DebtorBooks | VendorMaster | ClaimsAgent | Manual | Other",
    "duplicateGroupId": "string"
  }
]

The creditor matrix is operationally critical because it drives initial case notices, meeting notices, bar date notices, plan solicitation packages, and other Rule 2002 notice workflows. Rule 2002 contains detailed notice requirements for creditors, equity security holders, and other parties in interest.  ￼

⸻

11. Equity holders

"equityHolders": [
  {
    "equityHolderId": "string",
    "partyId": "string",
    "debtorId": "string",
    "securityType": "CommonStock | PreferredStock | MembershipInterest | PartnershipInterest | Warrant | Option | RestrictedStock | BondConvertible | Other",
    "classOrSeries": "string",
    "sharesOrUnits": "decimal",
    "percentageOwnership": "decimal",
    "recordDate": "date",
    "beneficialOwnerIndicator": "boolean",
    "registeredHolderName": "string",
    "brokerOrNomineeName": "string",
    "noticeRequiredIndicator": "boolean"
  }
]

⸻

12. Assets

"assets": [
  {
    "assetId": "string",
    "debtorId": "string",
    "assetType": "Cash | BankAccount | AccountsReceivable | Inventory | Equipment | RealProperty | LeaseholdInterest | IntellectualProperty | LitigationClaim | InsurancePolicy | Investment | EquityInterest | IntercompanyReceivable | TaxRefund | Deposit | Vehicle | Other",
    "description": "string",
    "bookValue": "decimal",
    "estimatedMarketValue": "decimal",
    "valuationDate": "date",
    "valuationMethod": "BookValue | Appraisal | MarketComparable | DCF | DebtorEstimate | Unknown",
    "scheduledValue": "decimal",
    "scheduleReference": "ScheduleA/B | Other",
    "encumberedIndicator": "boolean",
    "lienIds": ["string"],
    "location": {},
    "ownershipInterest": "FeeOwned | Leased | PartiallyOwned | BeneficialInterest | Disputed | Other",
    "dispositionStatus": "Retained | Sold | Abandoned | Surrendered | Transferred | Unknown",
    "saleMotionDocketNumber": "string",
    "saleOrderDocketNumber": "string"
  }
]

⸻

13. Liabilities

"liabilities": [
  {
    "liabilityId": "string",
    "debtorId": "string",
    "creditorId": "string",
    "liabilityType": "SecuredDebt | PriorityTax | PriorityWage | GeneralUnsecured | BondDebt | LeaseObligation | LitigationClaim | EnvironmentalClaim | PensionOPEB | IntercompanyPayable | CustomerDeposit | AdministrativeExpense | Other",
    "scheduledAmount": "decimal",
    "bookAmount": "decimal",
    "petitionDateAmount": "decimal",
    "contingentIndicator": "boolean",
    "unliquidatedIndicator": "boolean",
    "disputedIndicator": "boolean",
    "securedIndicator": "boolean",
    "priorityIndicator": "boolean",
    "priorityBasis": "string",
    "maturityDate": "date",
    "interestRate": "decimal",
    "governingDocumentIds": ["string"],
    "relatedClaimIds": ["string"],
    "scheduleReference": "ScheduleD | ScheduleE/F | Other"
  }
]

⸻

14. Liens and collateral

"liens": [
  {
    "lienId": "string",
    "debtorId": "string",
    "securedPartyId": "string",
    "collateralAssetIds": ["string"],
    "lienType": "Mortgage | UCC | StatutoryLien | JudgmentLien | TaxLien | PossessoryLien | SecurityInterest | Other",
    "perfectionStatus": "Perfected | Unperfected | Disputed | Unknown",
    "perfectionMethod": "UCC1 | MortgageRecording | Possession | Control | CertificateOfTitle | Statute | Other",
    "recordingJurisdiction": "string",
    "filingNumber": "string",
    "filingDate": "date",
    "priority": "First | Second | Junior | PariPassu | Disputed | Unknown",
    "amountSecured": "decimal",
    "avoidanceChallengeIndicator": "boolean"
  }
]

⸻

15. Schedules

"schedules": {
  "debtorId": "string",
  "filingStatus": "NotStarted | Draft | Filed | Amended | Waived | NotApplicable",
  "filedDate": "date",
  "amendedDate": "date",
  "declarationDocumentId": "string",
  "scheduleA_B": {
    "realAndPersonalProperty": ["assetId"]
  },
  "scheduleD": {
    "securedClaims": ["liabilityId"]
  },
  "scheduleE_F": {
    "priorityAndGeneralUnsecuredClaims": ["liabilityId"]
  },
  "scheduleG": {
    "executoryContractsAndUnexpiredLeases": ["contractId"]
  },
  "scheduleH": {
    "codebtors": [
      {
        "partyId": "string",
        "creditorId": "string",
        "claimDescription": "string"
      }
    ]
  },
  "summaryOfAssetsAndLiabilities": {
    "totalAssets": "decimal",
    "totalSecuredClaims": "decimal",
    "totalPriorityClaims": "decimal",
    "totalUnsecuredClaims": "decimal",
    "totalLiabilities": "decimal"
  },
  "amendments": [
    {
      "amendmentId": "string",
      "amendmentDate": "date",
      "docketNumber": "string",
      "changedSections": ["string"],
      "reason": "string"
    }
  ]
}

⸻

16. Statement of financial affairs

"statementOfFinancialAffairs": {
  "debtorId": "string",
  "filingStatus": "NotStarted | Draft | Filed | Amended",
  "filedDate": "date",
  "grossRevenue": [
    {
      "period": "CurrentYear | PriorYear1 | PriorYear2",
      "amount": "decimal",
      "source": "string"
    }
  ],
  "paymentsToCreditors": [
    {
      "paymentId": "string",
      "payeePartyId": "string",
      "paymentDate": "date",
      "amount": "decimal",
      "paymentType": "DebtPayment | InsiderPayment | PreferencePeriodPayment | Other",
      "description": "string"
    }
  ],
  "legalProceedings": [
    {
      "proceedingId": "string",
      "caption": "string",
      "court": "string",
      "caseNumber": "string",
      "status": "Pending | Stayed | Settled | Judgment | Closed",
      "claimAmount": "decimal"
    }
  ],
  "transfers": [
    {
      "transferId": "string",
      "transfereePartyId": "string",
      "transferDate": "date",
      "assetDescription": "string",
      "value": "decimal",
      "transferType": "Sale | Gift | Foreclosure | Repossession | Assignment | InsiderTransfer | Other"
    }
  ],
  "setoffs": [],
  "losses": [],
  "giftsOrCharitableContributions": [],
  "financialAccountsClosed": [],
  "safeDepositBoxes": [],
  "booksAndRecords": [],
  "environmentalInformation": {},
  "amendments": []
}

⸻

17. Executory contracts and unexpired leases

"executoryContractsAndLeases": [
  {
    "contractId": "string",
    "debtorId": "string",
    "counterpartyId": "string",
    "contractType": "RealPropertyLease | EquipmentLease | SupplyAgreement | CustomerContract | LicenseAgreement | EmploymentAgreement | CollectiveBargainingAgreement | FranchiseAgreement | InsurancePolicy | Derivative | Other",
    "contractDescription": "string",
    "contractDate": "date",
    "expirationDate": "date",
    "monthlyPaymentAmount": "decimal",
    "cureAmountAsserted": "decimal",
    "cureAmountScheduled": "decimal",
    "assumptionStatus": "Undecided | Assumed | Rejected | Assigned | Expired | Disputed",
    "assumptionMotionDocketNumber": "string",
    "rejectionMotionDocketNumber": "string",
    "orderDocketNumber": "string",
    "effectiveDateOfAssumptionOrRejection": "date",
    "rejectionDamageClaimId": "string",
    "assignmentBuyerPartyId": "string"
  }
]

⸻

18. First-day relief

"firstDayRelief": {
  "firstDayDeclarationDocumentId": "string",
  "firstDayHearingDateTime": "datetime",
  "secondDayHearingDateTime": "datetime",
  "motions": [
    {
      "motionId": "string",
      "motionType": "JointAdministration | CashManagement | DIPFinancing | CashCollateral | Wages | Taxes | Utilities | CriticalVendors | CustomerPrograms | Insurance | NOL | ClaimsAgent | Noticing | RejectionProcedures | SaleProcedures | Other",
      "title": "string",
      "docketNumber": "string",
      "filedDate": "date",
      "interimOrderDocketNumber": "string",
      "finalOrderDocketNumber": "string",
      "status": "Filed | InterimGranted | FinalGranted | Denied | Withdrawn | Continued | Objected",
      "objectionDeadline": "datetime",
      "hearingDateTime": "datetime",
      "reliefRequestedSummary": "string",
      "reliefGrantedSummary": "string"
    }
  ]
}

⸻

19. Cash management

"cashManagement": {
  "debtorId": "string",
  "cashManagementMotionDocketNumber": "string",
  "cashManagementOrderDocketNumber": "string",
  "bankAccounts": [
    {
      "bankAccountId": "string",
      "debtorId": "string",
      "bankName": "string",
      "accountNumberMasked": "string",
      "accountType": "Operating | Payroll | Tax | Deposit | Escrow | DIP | Disbursement | Other",
      "petitionDateBalance": "decimal",
      "currentBalance": "decimal",
      "currency": "string",
      "authorizedSigners": ["partyId"],
      "isDebtorInPossessionAccount": "boolean",
      "closedIndicator": "boolean"
    }
  ],
  "intercompanyTransferProcedures": {
    "approvedIndicator": "boolean",
    "description": "string",
    "reportingRequiredIndicator": "boolean"
  },
  "investmentGuidelines": "string"
}

⸻

20. DIP financing

"dipFinancing": {
  "dipFacilityId": "string",
  "borrowerDebtorIds": ["string"],
  "guarantorDebtorIds": ["string"],
  "agentPartyId": "string",
  "lenderPartyIds": ["string"],
  "facilityType": "Revolver | TermLoan | DelayedDraw | ABL | PrimingDIP | JuniorDIP | RollUp | Other",
  "commitmentAmount": "decimal",
  "approvedAmountInterim": "decimal",
  "approvedAmountFinal": "decimal",
  "petitionDatePrepetitionDebtRolledUp": "decimal",
  "interestRateDescription": "string",
  "maturityDate": "date",
  "budgetDocumentId": "string",
  "interimOrderDocketNumber": "string",
  "finalOrderDocketNumber": "string",
  "approvedCharges": {
    "adequateProtectionPayments": "decimal",
    "commitmentFees": "decimal",
    "exitFees": "decimal",
    "professionalFeeCarveOut": "decimal"
  },
  "milestones": [
    {
      "milestoneType": "PlanFiling | DisclosureStatementApproval | SaleBidDeadline | Auction | Confirmation | EffectiveDate | Other",
      "dueDate": "date",
      "status": "Pending | Met | Missed | Extended | Waived"
    }
  ],
  "covenants": [
    {
      "covenantId": "string",
      "description": "string",
      "testFrequency": "Weekly | Monthly | Quarterly | Milestone | Other",
      "status": "InCompliance | Breach | Waived | Unknown"
    }
  ]
}

⸻

21. Cash collateral

"cashCollateral": {
  "cashCollateralUseRequestedIndicator": "boolean",
  "securedParties": ["partyId"],
  "interimOrderDocketNumber": "string",
  "finalOrderDocketNumber": "string",
  "budgetDocumentId": "string",
  "permittedUseDescription": "string",
  "adequateProtection": [
    {
      "partyId": "string",
      "protectionType": "ReplacementLien | SuperpriorityClaim | PeriodicPayment | Reporting | Insurance | Other",
      "description": "string",
      "amount": "decimal"
    }
  ],
  "budgetVarianceReports": [
    {
      "reportId": "string",
      "periodStart": "date",
      "periodEnd": "date",
      "actualReceipts": "decimal",
      "budgetedReceipts": "decimal",
      "actualDisbursements": "decimal",
      "budgetedDisbursements": "decimal",
      "variancePercent": "decimal",
      "complianceStatus": "Compliant | NonCompliant | Waived"
    }
  ]
}

⸻

22. Claims register

Proof of Claim Official Form 410 is part of the official bankruptcy forms ecosystem and is commonly used for creditor claim filing.  ￼

"claimsRegister": {
  "barDates": [
    {
      "barDateId": "string",
      "barDateType": "General | Governmental | RejectionDamages | Administrative | Section503b9 | AmendedSchedules | Other",
      "deadlineDateTime": "datetime",
      "orderDocketNumber": "string",
      "noticeDocketNumber": "string",
      "appliesToDebtorIds": ["string"],
      "exceptions": ["string"]
    }
  ],
  "claims": [
    {
      "claimId": "string",
      "claimNumber": "string",
      "amendmentNumber": "integer",
      "debtorId": "string",
      "creditorId": "string",
      "filedByPartyId": "string",
      "filedDate": "date",
      "receivedMethod": "Electronic | Mail | HandDelivery | ECF | ClaimsAgentPortal | Other",
      "claimType": "Secured | Priority | GeneralUnsecured | Administrative | RejectionDamages | 503b9 | Tax | Equity | Other",
      "assertedAmount": "decimal",
      "securedAmount": "decimal",
      "priorityAmount": "decimal",
      "unsecuredAmount": "decimal",
      "unliquidatedIndicator": "boolean",
      "contingentIndicator": "boolean",
      "disputedIndicator": "boolean",
      "basisOfClaim": "TradeDebt | Loan | Bond | Lease | Litigation | Taxes | Wages | Benefits | GoodsReceived20Days | Contract | Other",
      "collateralDescription": "string",
      "priorityBasis": "string",
      "attachments": ["documentId"],
      "signature": {
        "signedByName": "string",
        "signedByTitle": "string",
        "signedDate": "date"
      },
      "status": "Filed | Amended | Superseded | Objected | Allowed | Disallowed | Withdrawn | Transferred | Estimated | Expunged | Reclassified | Reduced",
      "allowedAmount": "decimal",
      "allowedSecuredAmount": "decimal",
      "allowedPriorityAmount": "decimal",
      "allowedUnsecuredAmount": "decimal",
      "objections": [
        {
          "objectionId": "string",
          "objectionType": "Omnibus | Substantive | Duplicate | LateFiled | NoLiability | Reclassify | Reduce | InsufficientDocumentation | Other",
          "docketNumber": "string",
          "filedDate": "date",
          "responseDeadline": "datetime",
          "hearingDateTime": "datetime",
          "status": "Pending | Sustained | Overruled | Settled | Withdrawn",
          "orderDocketNumber": "string",
          "resolvedAmount": "decimal"
        }
      ],
      "transfers": [
        {
          "transferId": "string",
          "transferorPartyId": "string",
          "transfereePartyId": "string",
          "transferNoticeDocketNumber": "string",
          "transferDate": "date",
          "status": "NoticeFiled | Objected | Effective | Reversed"
        }
      ],
      "planClassId": "string",
      "distributionTreatmentId": "string"
    }
  ]
}

⸻

23. Noticing and service

"noticing": {
  "serviceLists": [
    {
      "serviceListId": "string",
      "listType": "CreditorMatrix | Rule2002List | MasterServiceList | LimitedNoticeList | EquityHolderList | BallotSolicitationList | ClaimsObjectionList | Other",
      "createdDate": "date",
      "source": "Debtor | ClaimsAgent | Court | Manual | Other",
      "parties": [
        {
          "partyId": "string",
          "addressId": "string",
          "email": "string",
          "serviceMethod": "ECF | Email | FirstClassMail | Overnight | Publication | PersonalService | Other",
          "noticeOnlyIndicator": "boolean"
        }
      ]
    }
  ],
  "notices": [
    {
      "noticeId": "string",
      "noticeType": "CaseCommencement | MeetingOfCreditors | BarDate | Motion | Hearing | PlanSolicitation | ConfirmationHearing | EffectiveDate | Distribution | Other",
      "relatedDocketNumber": "string",
      "documentId": "string",
      "servedDate": "date",
      "servedBy": "Debtor | ClaimsAgent | Court | Other",
      "serviceListId": "string",
      "recipientCount": "integer",
      "certificateOfServiceDocketNumber": "string",
      "publicationNoticeIndicator": "boolean",
      "publicationDetails": []
    }
  ]
}

⸻

24. Docket and court documents

"docket": {
  "docketEntries": [
    {
      "docketEntryId": "string",
      "caseNumber": "string",
      "docketNumber": "string",
      "filedDateTime": "datetime",
      "enteredDateTime": "datetime",
      "filedByPartyId": "string",
      "title": "string",
      "description": "string",
      "documentType": "Petition | Schedule | SOFA | Motion | Objection | Order | Notice | CertificateOfService | Transcript | HearingNotice | Plan | DisclosureStatement | BallotReport | ClaimObjection | FeeApplication | Other",
      "relatedDocketNumbers": ["string"],
      "documentIds": ["string"],
      "hearingIds": ["string"],
      "deadlines": [
        {
          "deadlineType": "Objection | Response | Reply | CureObjection | Voting | AssumptionDesignation | Other",
          "deadlineDateTime": "datetime"
        }
      ],
      "ecfTransactionId": "string",
      "pacerDocumentNumber": "string",
      "sealedIndicator": "boolean",
      "restrictedAccessIndicator": "boolean"
    }
  ],
  "documents": [
    {
      "documentId": "string",
      "docketNumber": "string",
      "fileName": "string",
      "mimeType": "application/pdf",
      "pageCount": "integer",
      "storageUri": "string",
      "hash": "string",
      "ocrTextAvailableIndicator": "boolean",
      "extractedData": {},
      "confidentiality": "Public | Redacted | Sealed | HighlyConfidential | Privileged"
    }
  ],
  "hearings": [
    {
      "hearingId": "string",
      "hearingDateTime": "datetime",
      "courtroom": "string",
      "judge": "string",
      "hearingType": "FirstDay | SecondDay | Omnibus | Confirmation | DisclosureStatement | Sale | ClaimObjection | FeeApplication | StatusConference | Other",
      "agendaDocumentId": "string",
      "status": "Scheduled | Continued | Held | Cancelled | ResolvedByCertification",
      "outcomeSummary": "string"
    }
  ]
}

⸻

25. Motions and orders

"motionsAndOrders": [
  {
    "matterId": "string",
    "matterType": "Motion | Application | Objection | Stipulation | Adversary | ContestedMatter | Other",
    "title": "string",
    "movantPartyId": "string",
    "relatedDebtorIds": ["string"],
    "motionDocketNumber": "string",
    "filedDate": "date",
    "reliefRequested": "string",
    "objectionDeadline": "datetime",
    "objections": [
      {
        "objectionId": "string",
        "objectorPartyId": "string",
        "docketNumber": "string",
        "filedDate": "date",
        "status": "Pending | Resolved | Overruled | Sustained | Withdrawn"
      }
    ],
    "hearings": ["hearingId"],
    "order": {
      "orderDocketNumber": "string",
      "enteredDate": "date",
      "orderType": "Interim | Final | Agreed | Scheduling | Denial | Other",
      "grantedIndicator": "boolean",
      "summaryOfReliefGranted": "string"
    },
    "status": "Filed | Pending | Granted | Denied | Withdrawn | Settled | Continued"
  }
]

⸻

26. Adversary proceedings

"adversaryProceedings": [
  {
    "adversaryId": "string",
    "adversaryCaseNumber": "string",
    "mainCaseNumber": "string",
    "plaintiffPartyIds": ["string"],
    "defendantPartyIds": ["string"],
    "complaintDocketNumber": "string",
    "filedDate": "date",
    "causesOfAction": [
      "Preference",
      "FraudulentTransfer",
      "EquitableSubordination",
      "DeclaratoryJudgment",
      "BreachOfContract",
      "ClaimObjection",
      "LienAvoidance",
      "Dischargeability",
      "Other"
    ],
    "amountSought": "decimal",
    "status": "Pending | Stayed | Settled | Judgment | Dismissed | Closed",
    "settlementAmount": "decimal",
    "judgmentAmount": "decimal",
    "relatedClaimIds": ["string"],
    "relatedAssetIds": ["string"]
  }
]

⸻

27. Avoidance actions

"avoidanceActions": [
  {
    "avoidanceActionId": "string",
    "debtorId": "string",
    "targetPartyId": "string",
    "actionType": "Preference | FraudulentTransfer | UnauthorizedPostpetitionTransfer | Setoff | LienAvoidance | Other",
    "lookbackPeriodStart": "date",
    "lookbackPeriodEnd": "date",
    "transferIds": ["string"],
    "grossAmount": "decimal",
    "defenses": [
      "OrdinaryCourse",
      "NewValue",
      "ContemporaneousExchange",
      "SubsequentNewValue",
      "SafeHarbor",
      "Other"
    ],
    "demandLetterDate": "date",
    "complaintAdversaryId": "string",
    "status": "Identified | DemandSent | Filed | Settled | Judgment | Abandoned | ReleasedUnderPlan",
    "recoveryAmount": "decimal"
  }
]

⸻

28. Monthly operating reports and post-confirmation reports

The U.S. Trustee Program requires uniform monthly operating reports and post-confirmation reports for many Chapter 11 cases, using data-embedded forms.  ￼

"operatingReports": [
  {
    "reportId": "string",
    "debtorId": "string",
    "reportType": "MonthlyOperatingReport | PostConfirmationReport | SmallBusinessMOR | SubchapterVReport | Other",
    "reportingPeriodStart": "date",
    "reportingPeriodEnd": "date",
    "filedDate": "date",
    "docketNumber": "string",
    "formVersion": "string",
    "cash": {
      "beginningCashBalance": "decimal",
      "receipts": "decimal",
      "disbursements": "decimal",
      "endingCashBalance": "decimal",
      "restrictedCash": "decimal"
    },
    "incomeStatement": {
      "grossRevenue": "decimal",
      "costOfGoodsSold": "decimal",
      "operatingExpenses": "decimal",
      "restructuringExpenses": "decimal",
      "netIncomeLoss": "decimal"
    },
    "balanceSheet": {
      "totalAssets": "decimal",
      "totalLiabilities": "decimal",
      "equityDeficit": "decimal"
    },
    "accountsReceivable": {
      "grossReceivables": "decimal",
      "receivablesOver90Days": "decimal",
      "badDebtReserve": "decimal"
    },
    "taxCompliance": {
      "taxReturnsFiledIndicator": "boolean",
      "postpetitionTaxesCurrentIndicator": "boolean",
      "taxDelinquenciesDescription": "string"
    },
    "insuranceCompliance": {
      "insuranceMaintainedIndicator": "boolean",
      "policyLapsesDescription": "string"
    },
    "bankAccountCompliance": {
      "dipAccountsEstablishedIndicator": "boolean",
      "allReceiptsDepositedIntoDipAccountsIndicator": "boolean"
    },
    "professionalFeesPaid": "decimal",
    "ustQuarterlyFeesAccrued": "decimal",
    "ustQuarterlyFeesPaid": "decimal",
    "certification": {
      "certifiedByName": "string",
      "title": "string",
      "certifiedDate": "date"
    },
    "attachments": ["documentId"]
  }
]

⸻

29. Plan and disclosure statement

"planAndDisclosureStatement": {
  "planId": "string",
  "planProponentPartyIds": ["string"],
  "planType": "Reorganization | Liquidation | SalePlan | Prepackaged | Prenegotiated | SubchapterV | Other",
  "planDocketNumber": "string",
  "planFiledDate": "date",
  "planVersion": "string",
  "amendedPlanDocketNumbers": ["string"],
  "disclosureStatementRequiredIndicator": "boolean",
  "disclosureStatementDocketNumber": "string",
  "disclosureStatementApprovalOrderDocketNumber": "string",
  "solicitationProceduresOrderDocketNumber": "string",
  "planClasses": [
    {
      "classId": "string",
      "classNumber": "string",
      "className": "string",
      "claimOrInterestType": "Administrative | PriorityTax | OtherPriority | Secured | GeneralUnsecured | Convenience | Subordinated | Equity | Intercompany | Other",
      "impairedIndicator": "boolean",
      "entitledToVoteIndicator": "boolean",
      "deemedAcceptReject": "DeemedAccept | DeemedReject | Solicited | NotApplicable",
      "estimatedClaimAmount": "decimal",
      "treatmentSummary": "string",
      "projectedRecoveryPercentLow": "decimal",
      "projectedRecoveryPercentHigh": "decimal",
      "distributionTreatmentId": "string"
    }
  ],
  "meansForImplementation": [
    "NewDebt",
    "NewEquity",
    "AssetSale",
    "LiquidatingTrust",
    "LitigationTrust",
    "ExitFinancing",
    "EquityRightsOffering",
    "ManagementIncentivePlan",
    "Other"
  ],
  "releases": {
    "debtorReleaseIndicator": "boolean",
    "thirdPartyReleaseIndicator": "boolean",
    "exculpationIndicator": "boolean",
    "injunctionIndicator": "boolean",
    "optOutRequiredIndicator": "boolean",
    "releaseDescription": "string"
  },
  "effectiveDateConditions": [
    {
      "conditionId": "string",
      "description": "string",
      "status": "Pending | Satisfied | Waived | Failed"
    }
  ]
}

Rule 3016 requires Chapter 11 plans or modifications to be dated and to identify the proponent. It also governs filing of disclosure statements and related Chapter 11 plan materials.  ￼

⸻

30. Solicitation and voting

"solicitationAndVoting": {
  "solicitationId": "string",
  "solicitationStartDate": "date",
  "votingDeadline": "datetime",
  "recordDate": "date",
  "solicitationAgentPartyId": "string",
  "solicitationPackages": [
    {
      "packageId": "string",
      "recipientPartyId": "string",
      "classId": "string",
      "serviceMethod": "Email | Mail | Overnight | Nominee | Publication | Other",
      "servedDate": "date",
      "ballotId": "string"
    }
  ],
  "ballots": [
    {
      "ballotId": "string",
      "claimId": "string",
      "creditorId": "string",
      "classId": "string",
      "ballotType": "MasterBallot | BeneficialHolderBallot | DirectCreditorBallot | OptOutOnly | Other",
      "receivedDateTime": "datetime",
      "vote": "Accept | Reject | Abstain | Invalid",
      "votingAmount": "decimal",
      "votingClaimCount": "integer",
      "temporaryAllowanceAmount": "decimal",
      "defectStatus": "Valid | Defective | Late | Duplicate | Superseded | Unresolved",
      "optOutOfReleaseIndicator": "boolean",
      "signatureName": "string"
    }
  ],
  "votingReport": {
    "docketNumber": "string",
    "filedDate": "date",
    "classes": [
      {
        "classId": "string",
        "acceptingAmount": "decimal",
        "rejectingAmount": "decimal",
        "acceptingCount": "integer",
        "rejectingCount": "integer",
        "acceptedByAmountIndicator": "boolean",
        "acceptedByNumberIndicator": "boolean",
        "classAcceptedIndicator": "boolean"
      }
    ]
  }
}

⸻

31. Confirmation

"confirmation": {
  "confirmationHearingId": "string",
  "confirmationHearingDateTime": "datetime",
  "confirmationObjectionDeadline": "datetime",
  "confirmationObjections": [
    {
      "objectionId": "string",
      "objectorPartyId": "string",
      "docketNumber": "string",
      "status": "Pending | Resolved | Overruled | Sustained | Withdrawn"
    }
  ],
  "confirmationOrderDocketNumber": "string",
  "confirmationDate": "date",
  "effectiveDate": "date",
  "substantialConsummationDate": "date",
  "planConfirmedIndicator": "boolean",
  "cramdownIndicator": "boolean",
  "classesConfirmedOverRejection": ["classId"],
  "findings": {
    "goodFaithIndicator": "boolean",
    "bestInterestsTestSatisfiedIndicator": "boolean",
    "feasibilitySatisfiedIndicator": "boolean",
    "absolutePriorityIssuesResolvedIndicator": "boolean"
  },
  "appeals": [
    {
      "appealId": "string",
      "noticeOfAppealDocketNumber": "string",
      "appellantPartyId": "string",
      "status": "Pending | Dismissed | Affirmed | Reversed | Settled"
    }
  ]
}

⸻

32. Distributions

"distributions": [
  {
    "distributionId": "string",
    "planId": "string",
    "distributionDate": "date",
    "distributionType": "Cash | NewEquity | NewDebt | Warrants | TrustInterests | AssetDistribution | Other",
    "distributionTreatmentId": "string",
    "recipientPartyId": "string",
    "claimId": "string",
    "classId": "string",
    "allowedClaimAmount": "decimal",
    "distributionAmount": "decimal",
    "currency": "string",
    "recoveryPercent": "decimal",
    "withholdingAmount": "decimal",
    "reserveIndicator": "boolean",
    "reserveReason": "DisputedClaim | Undeliverable | TaxWithholding | PendingDocumentation | Other",
    "paymentMethod": "Check | ACH | Wire | DTC | BookEntry | Other",
    "paymentReference": "string",
    "clearedDate": "date",
    "voidedDate": "date",
    "reissuedDistributionId": "string"
  }
]

⸻

33. Post-confirmation administration

"postConfirmation": {
  "reorganizedDebtorIds": ["string"],
  "liquidatingTrust": {
    "createdIndicator": "boolean",
    "trustName": "string",
    "trusteePartyId": "string",
    "trustAgreementDocumentId": "string",
    "trustEffectiveDate": "date"
  },
  "planAdministrator": {
    "partyId": "string",
    "name": "string",
    "appointmentDocumentId": "string"
  },
  "claimsReconciliationStatus": {
    "totalClaimsFiled": "integer",
    "claimsAllowed": "integer",
    "claimsDisallowed": "integer",
    "claimsUnresolved": "integer",
    "claimsReserveAmount": "decimal"
  },
  "postConfirmationReports": ["reportId"],
  "finalDecree": {
    "motionDocketNumber": "string",
    "orderDocketNumber": "string",
    "enteredDate": "date"
  }
}

⸻

34. Case closing

"caseClosing": {
  "closingStatus": "Open | ReadyForFinalDecree | FinalDecreeEntered | Closed | Reopened",
  "finalReportFiledIndicator": "boolean",
  "finalReportDocketNumber": "string",
  "finalDecreeMotionDocketNumber": "string",
  "finalDecreeOrderDocketNumber": "string",
  "caseClosedDate": "date",
  "reopenedDate": "date",
  "reopenReason": "AdministerAsset | ResolveClaim | CorrectOrder | Litigation | Other",
  "remainingMatters": [
    {
      "matterType": "Claims | Adversary | Distribution | FeeApplication | Appeal | Other",
      "description": "string",
      "status": "Open | Resolved"
    }
  ]
}

⸻

35. Compliance and restricted information

"compliance": {
  "privacyAndRedaction": {
    "piiRedactionRequiredIndicator": "boolean",
    "minorNamesRedactedIndicator": "boolean",
    "taxIdsRedactedIndicator": "boolean",
    "financialAccountNumbersRedactedIndicator": "boolean",
    "sealedDocuments": ["documentId"]
  },
  "ustCompliance": {
    "initialDebtorInterviewDate": "date",
    "meetingOfCreditorsDate": "date",
    "quarterlyFeesCurrentIndicator": "boolean",
    "operatingReportsCurrentIndicator": "boolean",
    "insuranceCurrentIndicator": "boolean",
    "taxesCurrentIndicator": "boolean"
  },
  "deadlines": [
    {
      "deadlineId": "string",
      "deadlineType": "Schedules | SOFA | BarDate | GovernmentBarDate | Exclusivity | PlanFiling | DisclosureStatement | Voting | Confirmation | MOR | USTFee | Other",
      "deadlineDateTime": "datetime",
      "sourceDocketNumber": "string",
      "status": "Pending | Met | Missed | Extended | Waived"
    }
  ],
  "exclusivity": {
    "planExclusivityDeadline": "date",
    "solicitationExclusivityDeadline": "date",
    "extensions": [
      {
        "motionDocketNumber": "string",
        "orderDocketNumber": "string",
        "newDeadline": "date"
      }
    ],
    "terminatedIndicator": "boolean"
  }
}

⸻

36. Audit and provenance

"audit": {
  "createdDateTime": "datetime",
  "createdBy": "string",
  "lastUpdatedDateTime": "datetime",
  "lastUpdatedBy": "string",
  "dataLineage": [
    {
      "fieldPath": "string",
      "source": "DebtorBooks | Petition | Schedules | SOFA | ClaimForm | ClaimsAgent | CMECF | PACER | USTForm | Professional | Manual | OCR | Other",
      "sourceSystem": "string",
      "sourceRecordId": "string",
      "sourceDocketNumber": "string",
      "captureDateTime": "datetime",
      "confidenceScore": "decimal"
    }
  ],
  "changeHistory": [
    {
      "changeId": "string",
      "entityType": "Debtor | Creditor | Claim | Asset | Liability | Docket | Ballot | Distribution | Other",
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
      "entityType": "Case | Claim | Document | Ballot | Distribution | PrivilegedMaterial | Other",
      "entityId": "string",
      "accessedBy": "string",
      "accessDateTime": "datetime",
      "accessPurpose": "CaseAdministration | Filing | ClaimsReview | Distribution | Audit | Litigation | Other"
    }
  ]
}

⸻

37. Field-level metadata pattern

For bankruptcy systems, many values change as schedules are amended, claims are filed, objections are resolved, and plans become effective. Add field-level metadata to critical attributes:

{
  "value": "any",
  "source": "DebtorBooks | Petition | Schedule | SOFA | Claim | CourtOrder | ClaimsAgent | USTReport | Manual | Calculated",
  "sourceDocumentId": "string",
  "sourceDocketNumber": "string",
  "effectiveDate": "date",
  "capturedDateTime": "datetime",
  "verifiedIndicator": "boolean",
  "verificationMethod": "CourtFiled | ReconciledToBooks | ClaimsAgentReview | CourtOrder | ManualReview | Other",
  "confidenceScore": "decimal",
  "sensitivity": "Public | Redacted | Sealed | Privileged | Confidential | PII | Tax | Banking",
  "lastUpdatedBy": "string",
  "lastUpdatedDateTime": "datetime"
}

⸻

38. Recommended relational / domain model

Chapter11Case
 ├── Court
 ├── Debtor
 │    ├── DebtorAddress
 │    ├── DebtorIdentifier
 │    └── AffiliateRelationship
 ├── Party
 │    ├── PartyRole
 │    ├── Address
 │    └── ContactPoint
 ├── Creditor
 ├── EquityHolder
 ├── Asset
 ├── Liability
 ├── Lien
 ├── Schedule
 ├── StatementOfFinancialAffairs
 ├── ExecutoryContractLease
 ├── FirstDayMotion
 ├── CashManagementAccount
 ├── DIPFacility
 ├── CashCollateralBudget
 ├── Claim
 │    ├── ClaimAmendment
 │    ├── ClaimObjection
 │    └── ClaimTransfer
 ├── ServiceList
 ├── Notice
 ├── DocketEntry
 │    ├── Document
 │    └── Hearing
 ├── MotionMatter
 │    ├── Objection
 │    └── Order
 ├── AdversaryProceeding
 ├── AvoidanceAction
 ├── OperatingReport
 ├── Plan
 │    ├── PlanClass
 │    ├── Treatment
 │    └── EffectiveDateCondition
 ├── Ballot
 ├── VotingReport
 ├── Confirmation
 ├── Distribution
 ├── PostConfirmationReport
 ├── FinalDecree
 ├── Deadline
 ├── ComplianceEvent
 ├── AuditEvent
 └── Extension

⸻

39. Integration coverage matrix

Use case	Schema areas required
Petition preparation	Case metadata, debtor, venue, petition form, creditor matrix, estimated assets/liabilities
Jointly administered cases	Debtors, lead case, affiliate relationships, related cases
Creditor matrix / noticing	Parties, creditors, service lists, notices, certificate of service
Schedules and SOFA	Assets, liabilities, contracts, transfers, litigation, financial accounts
Claims agent platform	Creditors, bar dates, proofs of claim, objections, transfers, service
Court docket ingestion	Court, case, docket entries, documents, hearings, orders
First-day hearing	First-day motions, interim/final orders, objection deadlines
DIP financing	DIP facility, lenders, milestones, budget, covenants, orders
Cash collateral	secured parties, budgets, adequate protection, variance reports
Operating reports	cash, income statement, balance sheet, taxes, insurance, UST fees
Plan process	plan, disclosure statement, classes, treatment, releases
Solicitation and voting	ballots, record date, voting deadlines, tabulation report
Confirmation	objections, confirmation order, cramdown, effective date
Distributions	allowed claims, class treatment, payment method, reserves
Post-confirmation trust	liquidating trust, plan administrator, claim reconciliation
Litigation	adversary proceedings, avoidance actions, settlements, judgments
Audit/examiner review	docket source, document hash, change history, access history

⸻

40. Key enumerations to standardize

CaseStatus
FilingType
DebtorType
CaseComplexity
PartyType
PartyRole
CreditorType
ClaimType
ClaimStatus
PriorityBasis
AssetType
LiabilityType
LienType
ScheduleSection
SOFASection
ContractType
AssumptionRejectionStatus
MotionType
OrderType
NoticeType
ServiceMethod
DocketDocumentType
HearingType
BarDateType
PlanType
PlanClassType
ImpairmentStatus
VotingStatus
BallotType
DistributionType
PaymentMethod
OperatingReportType
DeadlineType
ConfidentialityLevel
SourceSystemType

⸻

41. MVP schema vs. enterprise schema

MVP Chapter 11 schema

For a law-firm intake, claims-monitoring, or distressed-investment tool:

Case
Debtor
Court
DocketEntry
Document
Creditor
Claim
PlanClass
Notice
Deadline
OperatingReport
Audit

Enterprise Chapter 11 schema

For a claims agent, debtor-side restructuring platform, court data platform, or bank workout system:

Case
Court
Debtor
Affiliates
Party
Creditor
EquityHolder
Assets
Liabilities
Liens
Schedules
SOFA
ExecutoryContracts
FirstDayRelief
CashManagement
DIPFinancing
CashCollateral
ClaimsRegister
ClaimsObjections
ClaimsTransfers
Noticing
Docket
Documents
Hearings
Motions
Orders
AdversaryProceedings
AvoidanceActions
OperatingReports
Plan
DisclosureStatement
Solicitation
Ballots
VotingReport
Confirmation
Distributions
PostConfirmationTrust
CaseClosing
Compliance
Audit
Extensions

⸻

42. Suggested API resource model

POST   /chapter11/cases
GET    /chapter11/cases/{caseId}
PATCH  /chapter11/cases/{caseId}
POST   /chapter11/cases/{id}/debtors
POST   /chapter11/cases/{id}/parties
POST   /chapter11/cases/{id}/creditors
POST   /chapter11/cases/{id}/equity-holders
POST   /chapter11/cases/{id}/assets
POST   /chapter11/cases/{id}/liabilities
POST   /chapter11/cases/{id}/contracts
POST   /chapter11/cases/{id}/docket-entries
POST   /chapter11/cases/{id}/documents
POST   /chapter11/cases/{id}/hearings
POST   /chapter11/cases/{id}/claims
PATCH  /chapter11/cases/{id}/claims/{claimId}
POST   /chapter11/cases/{id}/claims/{claimId}/objections
POST   /chapter11/cases/{id}/claims/{claimId}/transfers
POST   /chapter11/cases/{id}/notices
POST   /chapter11/cases/{id}/service-lists
POST   /chapter11/cases/{id}/motions
PATCH  /chapter11/cases/{id}/motions/{matterId}
POST   /chapter11/cases/{id}/orders
POST   /chapter11/cases/{id}/operating-reports
POST   /chapter11/cases/{id}/plans
POST   /chapter11/cases/{id}/ballots
POST   /chapter11/cases/{id}/voting-reports
POST   /chapter11/cases/{id}/confirmation
POST   /chapter11/cases/{id}/distributions
POST   /chapter11/cases/{id}/post-confirmation-reports
GET    /chapter11/cases/{id}/deadlines
GET    /chapter11/cases/{id}/audit

⸻

43. Recommended schema layers

Layer 1: Petition and Case Intake
Court, case, debtors, venue, petition metadata, affiliates, creditor matrix.
Layer 2: Estate Data
Assets, liabilities, liens, schedules, SOFA, executory contracts, leases.
Layer 3: Court Administration
Docket, documents, hearings, motions, objections, orders, notices, service lists.
Layer 4: Claims Administration
Bar dates, proofs of claim, amendments, objections, transfers, allowed claims.
Layer 5: Financing and Operations
Cash management, DIP financing, cash collateral, budgets, operating reports, UST fees.
Layer 6: Plan and Solicitation
Disclosure statement, plan classes, treatment, ballots, releases, voting report.
Layer 7: Confirmation and Post-Confirmation
Confirmation order, effective date, distributions, trusts, final decree, case closing.
Layer 8: Audit, Compliance, and Security
Redaction, sealed material, source docketing, data lineage, access history, retention.

⸻

44. Critical implementation recommendations

Separate scheduled claims from filed claims.
A scheduled liability is debtor-provided; a proof of claim is creditor-filed; an allowed claim is a legal/resulting status often determined through reconciliation, objection, settlement, or court order.

Model each debtor estate separately.
Even jointly administered cases may not be substantively consolidated. Assets, liabilities, claims, contracts, bank accounts, and distributions often belong to specific debtors.

Treat the docket as a source-of-truth event stream.
Most important case events appear as docket entries: filings, objections, notices, certificates of service, hearing agendas, orders, transcripts, plans, and reports.

Do not flatten plan treatment.
Claims map to classes, classes map to treatment, and treatment maps to distributions. This is a many-to-many problem in complex cases.

Keep notices and service evidence first-class.
Notice defects can affect bar dates, claim objections, plan voting, releases, and confirmation.

Support amendments and supersession.
Petitions, schedules, SOFA, claims, plans, disclosure statements, ballots, and orders may all be amended or superseded.

Preserve document hashes and docket provenance.
Bankruptcy case administration is document-heavy. Every extracted field should point back to a document, docket number, page, or claims-agent record where possible.

Handle sealed, redacted, privileged, and restricted data.
PII, tax identifiers, bank account numbers, employee data, customer lists, sale bids, and privileged investigation materials need security classification.

Build deadlines as a shared service.
Chapter 11 involves schedules deadlines, UST reporting, claims bar dates, objections, bid deadlines, cure objections, voting deadlines, confirmation objections, exclusivity deadlines, and plan milestones.

⸻

45. Final canonical domains

A comprehensive Chapter 11 bankruptcy schema should include:

1. Case metadata
2. Court and judge
3. Debtors
4. Affiliates and jointly administered cases
5. Venue and jurisdiction
6. Professionals and fiduciaries
7. Parties in interest
8. Creditors
9. Equity holders
10. Creditor matrix
11. Assets
12. Liabilities
13. Liens and collateral
14. Schedules
15. Statement of financial affairs
16. Executory contracts and unexpired leases
17. Codebtors and guarantors
18. First-day motions
19. Cash management
20. DIP financing
21. Cash collateral
22. Budgets and variance reports
23. U.S. Trustee compliance
24. Monthly operating reports
25. Post-confirmation reports
26. Claims register
27. Bar dates
28. Proofs of claim
29. Claim amendments
30. Claim objections
31. Claim transfers
32. Noticing and service lists
33. Docket entries
34. Court documents
35. Hearings
36. Motions and contested matters
37. Orders
38. Adversary proceedings
39. Avoidance actions
40. Asset sales
41. Plan
42. Disclosure statement
43. Plan classes
44. Releases and injunctions
45. Solicitation packages
46. Ballots
47. Voting report
48. Confirmation
49. Effective date
50. Distributions
51. Reserves
52. Liquidating trust / plan administrator
53. Final decree and case closing
54. Appeals
55. Compliance and redaction
56. Deadlines
57. Data lineage
58. Audit and access history
59. Retention and legal hold
60. Extensions

This schema should support most U.S. Chapter 11 workflows across debtor counsel, restructuring advisors, claims agents, noticing vendors, court-data vendors, lenders, credit investors, and post-confirmation administrators.