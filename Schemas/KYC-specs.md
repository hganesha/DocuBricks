Below is a comprehensive KYC / KYB schema for U.S. banks, fintechs, lenders, payment companies, broker-dealers, wealth platforms, and vendors. It is designed to support:

CIP, CDD, EDD, beneficial ownership, KYB, sanctions screening, PEP/adverse media, fraud/device checks, document verification, digital identity proofing, risk scoring, ongoing monitoring, case management, SAR/CTR support, and auditability.

For U.S. banking, the schema should be grounded in the Bank Secrecy Act / AML framework, FinCEN’s Customer Identification Program rule, FinCEN’s Customer Due Diligence rule, FFIEC BSA/AML examination guidance, OFAC sanctions obligations, and modern digital identity practices such as NIST SP 800-63-4. CIP rules require risk-based procedures to verify customer identity to the extent reasonable and practicable, and to form a reasonable belief that the bank knows the customer’s true identity.  ￼ FinCEN’s CDD rule requires covered institutions to identify and verify beneficial owners of legal entity customers when accounts are opened, while FFIEC guidance emphasizes written risk-based procedures for beneficial ownership and ongoing CDD.  ￼

⸻

1. Top-level canonical object

{
  "kycProfile": {
    "profileId": "string",
    "profileVersion": "integer",
    "schemaVersion": "string",
    "customer": {},
    "parties": [],
    "relationships": [],
    "identity": {},
    "addresses": [],
    "contactPoints": [],
    "documents": [],
    "taxResidency": [],
    "employmentOrBusiness": {},
    "financialProfile": {},
    "sourceOfFunds": [],
    "sourceOfWealth": [],
    "beneficialOwnership": {},
    "controlPersons": [],
    "screening": {},
    "riskAssessment": {},
    "dueDiligence": {},
    "consents": [],
    "monitoring": {},
    "cases": [],
    "regulatoryReports": [],
    "audit": {},
    "extensions": {}
  }
}

⸻

2. Core design principles

A bank/vendor-grade KYC schema should be:

Party-centric.
A customer can be an individual, business, trust, government entity, nonprofit, fund, estate, joint account, or intermediary relationship. Do not model KYC as only “person fields.”

Relationship-aware.
KYC is often about relationships: beneficial owner, control person, authorized signer, trustee, settlor, protector, director, officer, guarantor, payor, payee, related business, parent company, subsidiary, intermediary, correspondent bank, or politically exposed relationship.

Risk-based.
The schema should support simplified due diligence, standard CDD, enhanced due diligence, high-risk customer workflows, ongoing monitoring, and periodic refresh.

Auditable.
Every identity attribute, verification, match decision, override, risk score, and approval should carry source, timestamp, actor, evidence, and reason.

Extensible.
KYC requirements differ by bank type, product, jurisdiction, customer segment, regulator, and risk appetite.

⸻

3. Customer / party model

3.1 Customer profile

"customer": {
  "customerId": "string",
  "customerType": "Individual | Business | Trust | Estate | GovernmentEntity | NonProfit | FinancialInstitution | Fund | Joint | Other",
  "customerSegment": "Retail | SmallBusiness | Commercial | Corporate | PrivateBanking | Wealth | CorrespondentBanking | MarketplaceSeller | Merchant | BrokerDealer | Other",
  "relationshipStatus": "Prospect | Applicant | Active | Suspended | Closed | Rejected | Offboarded",
  "relationshipStartDate": "date",
  "relationshipEndDate": "date",
  "onboardingChannel": "Branch | Online | Mobile | CallCenter | Broker | Partner | API | Batch | Other",
  "productsRequested": [
    "DepositAccount",
    "CreditCard",
    "Mortgage",
    "PersonalLoan",
    "AutoLoan",
    "BusinessLoan",
    "WireTransfer",
    "Payments",
    "MerchantServices",
    "Brokerage",
    "WealthManagement",
    "Crypto",
    "Insurance",
    "Other"
  ],
  "primaryCountryOfRelationship": "string",
  "primaryJurisdiction": "string",
  "relationshipManagerId": "string",
  "businessUnit": "string",
  "legalEntityOfBank": "string"
}

⸻

3.2 Generic party object

Use this for individuals, businesses, trusts, beneficial owners, control persons, signers, directors, related entities, and counterparties.

"parties": [
  {
    "partyId": "string",
    "partyType": "Individual | Organization | Trust | Estate | GovernmentEntity | NonProfit | Fund | Other",
    "roles": [
      "Customer",
      "Applicant",
      "BeneficialOwner",
      "ControlPerson",
      "AuthorizedSigner",
      "Director",
      "Officer",
      "Trustee",
      "Settlor",
      "Protector",
      "Beneficiary",
      "Guarantor",
      "PowerOfAttorney",
      "Nominee",
      "Intermediary",
      "ParentCompany",
      "Subsidiary",
      "Counterparty",
      "Payor",
      "Payee",
      "Other"
    ],
    "individual": {},
    "organization": {},
    "trust": {},
    "addresses": [],
    "contactPoints": [],
    "identifiers": [],
    "documents": [],
    "screening": {},
    "riskAssessment": {},
    "verification": {},
    "audit": {}
  }
]

⸻

4. Individual KYC schema

"individual": {
  "name": {
    "firstName": "string",
    "middleName": "string",
    "lastName": "string",
    "suffix": "string",
    "fullLegalName": "string",
    "preferredName": "string",
    "nativeScriptName": "string"
  },
  "aliases": [
    {
      "aliasType": "FormerName | MaidenName | Nickname | DBA | Transliteration | Other",
      "fullName": "string"
    }
  ],
  "dateOfBirth": "date",
  "placeOfBirth": {
    "city": "string",
    "stateProvince": "string",
    "countryCode": "string"
  },
  "nationalityCountries": ["string"],
  "citizenshipCountries": ["string"],
  "residencyCountries": ["string"],
  "gender": "Female | Male | NonBinary | NotSpecified | Unknown",
  "maritalStatus": "Single | Married | Divorced | Widowed | Separated | DomesticPartner | Unknown",
  "deceasedIndicator": "boolean",
  "minorIndicator": "boolean",
  "vulnerableCustomerIndicator": "boolean",
  "occupation": "string",
  "employerName": "string",
  "employmentStatus": "Employed | SelfEmployed | Retired | Student | Homemaker | Unemployed | Other",
  "industryCode": "string",
  "expectedAccountUse": "string"
}

⸻

5. Organization / KYB schema

"organization": {
  "legalName": "string",
  "tradeNames": ["string"],
  "doingBusinessAs": ["string"],
  "legalEntityType": "Corporation | LLC | Partnership | SoleProprietorship | LLP | LP | NonProfit | Trust | GovernmentEntity | Association | Fund | Bank | MSB | Other",
  "formation": {
    "formationDate": "date",
    "formationCountry": "string",
    "formationStateProvince": "string",
    "registrationNumber": "string",
    "registrationAuthority": "string"
  },
  "taxIdentifiers": [
    {
      "identifierType": "EIN | TIN | GIIN | ForeignTaxId | VAT | Other",
      "identifierValueMasked": "string",
      "issuingCountry": "string"
    }
  ],
  "businessClassification": {
    "naicsCode": "string",
    "sicCode": "string",
    "mccCode": "string",
    "businessDescription": "string",
    "regulatedBusinessIndicator": "boolean",
    "regulatedBusinessType": "Bank | BrokerDealer | MSB | MoneyTransmitter | Casino | CryptoVASP | Insurance | InvestmentAdviser | MortgageLender | Other"
  },
  "businessStatus": "Active | Inactive | Dissolved | Merged | Suspended | Unknown",
  "publicCompanyIndicator": "boolean",
  "exchangeListed": {
    "exchangeName": "string",
    "tickerSymbol": "string",
    "country": "string"
  },
  "website": "string",
  "emailDomain": "string",
  "phoneNumber": "string",
  "employeeCount": "integer",
  "annualRevenue": "decimal",
  "expectedMonthlyTransactionVolume": "decimal",
  "expectedMonthlyTransactionCount": "integer",
  "countriesOfOperation": ["string"],
  "countriesOfCustomers": ["string"],
  "highRiskActivityIndicators": [
    "CashIntensiveBusiness",
    "MoneyServicesBusiness",
    "ForeignFinancialInstitution",
    "PrivateATMOperator",
    "CannabisRelatedBusiness",
    "CryptoRelatedBusiness",
    "Gambling",
    "ArmsDefense",
    "AdultEntertainment",
    "CharityNonProfit",
    "ImportExport",
    "EmbassyConsulate",
    "PreciousMetalsStones",
    "Other"
  ]
}

⸻

6. Trust / estate schema

"trust": {
  "trustName": "string",
  "trustType": "Revocable | Irrevocable | Testamentary | Charitable | SpecialNeeds | LandTrust | ForeignTrust | Other",
  "formationDate": "date",
  "governingLawJurisdiction": "string",
  "taxIdentifierMasked": "string",
  "trustPurpose": "string",
  "trustAssetsDescription": "string",
  "trusteePartyIds": ["string"],
  "settlorPartyIds": ["string"],
  "protectorPartyIds": ["string"],
  "beneficiaryPartyIds": ["string"],
  "authorizedSignerPartyIds": ["string"]
}

⸻

7. Identity identifiers

For U.S. CIP, banks typically collect identifying information such as name, date of birth for individuals, address, and identification number, but schema design should support U.S. and foreign customers.

"identifiers": [
  {
    "identifierId": "string",
    "partyId": "string",
    "identifierType": "SSN | ITIN | EIN | PassportNumber | DriversLicense | StateId | NationalId | AlienRegistrationNumber | VisaNumber | TaxId | LEI | GIIN | DUNS | RegistrationNumber | Other",
    "identifierValueMasked": "string",
    "identifierToken": "string",
    "issuingCountry": "string",
    "issuingStateProvince": "string",
    "issueDate": "date",
    "expirationDate": "date",
    "primaryIndicator": "boolean",
    "verificationStatus": "Unverified | Verified | Failed | Expired | NotRequired | Waived",
    "verificationMethod": "Document | Database | CreditHeader | GovernmentRegistry | Vendor | Manual | Other"
  }
]

⸻

8. Address schema

"addresses": [
  {
    "addressId": "string",
    "partyId": "string",
    "addressType": "Residential | Mailing | Business | RegisteredOffice | PrincipalPlaceOfBusiness | Previous | Seasonal | Foreign | Other",
    "streetLine1": "string",
    "streetLine2": "string",
    "city": "string",
    "stateProvince": "string",
    "postalCode": "string",
    "countryCode": "string",
    "county": "string",
    "addressStartDate": "date",
    "addressEndDate": "date",
    "isPrimary": "boolean",
    "isDeliverable": "boolean",
    "isCommercialMailReceivingAgency": "boolean",
    "isPOBox": "boolean",
    "geolocation": {
      "latitude": "decimal",
      "longitude": "decimal",
      "precision": "string"
    },
    "verification": {
      "status": "Unverified | Verified | Failed | Partial | Waived",
      "method": "PostalDatabase | UtilityBill | Document | Geolocation | Vendor | Manual | Other",
      "verifiedDateTime": "datetime"
    }
  }
]

⸻

9. Contact points

"contactPoints": [
  {
    "contactPointId": "string",
    "partyId": "string",
    "type": "Email | MobilePhone | HomePhone | BusinessPhone | Fax | Website | SocialHandle | Other",
    "value": "string",
    "normalizedValue": "string",
    "countryCode": "string",
    "isPrimary": "boolean",
    "verificationStatus": "Unverified | Verified | Failed | Bounced | Disconnected",
    "verificationMethod": "OTP | EmailLink | CarrierLookup | DomainValidation | Manual | Vendor | Other",
    "verifiedDateTime": "datetime"
  }
]

⸻

10. Documents and evidence

"documents": [
  {
    "documentId": "string",
    "partyId": "string",
    "documentType": "DriversLicense | Passport | StateId | NationalId | Visa | GreenCard | UtilityBill | BankStatement | ArticlesOfIncorporation | CertificateOfGoodStanding | OperatingAgreement | PartnershipAgreement | TrustAgreement | TaxDocument | BeneficialOwnershipCertification | BoardResolution | ProofOfAddress | Other",
    "documentPurpose": "Identity | Address | EntityFormation | Authority | Ownership | Tax | SourceOfFunds | SourceOfWealth | Other",
    "documentNumberMasked": "string",
    "issuingCountry": "string",
    "issuingStateProvince": "string",
    "issueDate": "date",
    "expirationDate": "date",
    "receivedDateTime": "datetime",
    "source": "CustomerUpload | BranchScan | API | Vendor | PublicRegistry | Email | Other",
    "verification": {
      "status": "Pending | Verified | Failed | Expired | FraudSuspected | ManualReview | Waived",
      "method": "OCR | Barcode | NFC | DatabaseCheck | VisualInspection | Vendor | Manual",
      "provider": "string",
      "confidenceScore": "decimal",
      "verifiedDateTime": "datetime",
      "failureReasons": ["string"]
    },
    "fileMetadata": {
      "mimeType": "string",
      "fileSizeBytes": "integer",
      "hash": "string",
      "storageUri": "string"
    },
    "extractedData": {},
    "retentionPolicy": {
      "retainUntilDate": "date",
      "legalHoldIndicator": "boolean"
    }
  }
]

⸻

11. Identity verification and digital identity proofing

NIST SP 800-63-4 defines technical guidance for identity proofing, authentication, and federation, including assurance levels, privacy, security, and customer-experience considerations.  ￼ A bank schema does not need to copy NIST, but it should be able to record assurance outcomes.

"identityVerification": {
  "verificationId": "string",
  "partyId": "string",
  "verificationType": "CIP | CDD | EDD | Documentary | NonDocumentary | DigitalIdentity | Biometric | Database | Manual",
  "identityAssuranceLevel": "IAL1 | IAL2 | IAL3 | NotAssessed",
  "authenticatorAssuranceLevel": "AAL1 | AAL2 | AAL3 | NotAssessed",
  "federationAssuranceLevel": "FAL1 | FAL2 | FAL3 | NotAssessed",
  "verificationStatus": "NotStarted | Pending | Verified | Failed | NeedsReview | Waived",
  "verificationDateTime": "datetime",
  "verifiedAttributes": [
    "Name",
    "DateOfBirth",
    "Address",
    "SSN",
    "DocumentAuthenticity",
    "Liveness",
    "FaceMatch",
    "Phone",
    "Email",
    "BusinessRegistration",
    "BeneficialOwnership",
    "AuthorityToAct"
  ],
  "methods": [
    {
      "methodType": "DocumentScan | SelfieLiveness | NFCChip | CreditHeader | PublicRecords | BankAccountVerification | Payroll | UtilityData | BusinessRegistry | ManualReview | Other",
      "provider": "string",
      "transactionId": "string",
      "status": "Pass | Fail | Review | NotApplicable",
      "score": "decimal",
      "reasonCodes": ["string"],
      "timestamp": "datetime"
    }
  ],
  "manualReview": {
    "requiredIndicator": "boolean",
    "reviewerId": "string",
    "decision": "Approved | Rejected | Escalated | Waived",
    "decisionReason": "string",
    "decisionDateTime": "datetime"
  }
}

⸻

12. Beneficial ownership

For covered U.S. financial institutions, FinCEN’s CDD rule and FFIEC examination materials require procedures to identify and verify beneficial owners of legal entity customers.  ￼ Note that FinCEN BOI reporting under the Corporate Transparency Act is separate from bank KYC/CDD obligations. As of FinCEN’s March 2025 interim final rule, domestic U.S. entities and U.S. persons were exempted from BOI reporting to FinCEN, while certain foreign reporting companies still have BOI reporting obligations.  ￼

"beneficialOwnership": {
  "customerId": "string",
  "legalEntityCustomerIndicator": "boolean",
  "beneficialOwnershipCollectionRequired": "boolean",
  "collectionBasis": "CDDRule | BankPolicy | EDD | InvestorRequirement | JurisdictionRequirement | Other",
  "ownershipThresholdPercent": "decimal",
  "certification": {
    "certifiedByPartyId": "string",
    "certificationDateTime": "datetime",
    "certificationMethod": "Paper | Electronic | API | Verbal | Other",
    "documentId": "string"
  },
  "beneficialOwners": [
    {
      "partyId": "string",
      "ownershipPercent": "decimal",
      "ownershipType": "Direct | Indirect | Both | Unknown",
      "ownershipPath": [
        {
          "entityPartyId": "string",
          "ownedEntityPartyId": "string",
          "ownershipPercent": "decimal"
        }
      ],
      "substantialControlIndicator": "boolean",
      "controlDescription": "string",
      "verificationStatus": "Unverified | Verified | Failed | Waived | NotRequired",
      "verificationMethod": "Documentary | NonDocumentary | Registry | CustomerCertification | Vendor | Manual",
      "riskRating": "Low | Medium | High | Prohibited"
    }
  ],
  "controlPersons": [
    {
      "partyId": "string",
      "controlPersonType": "CEO | CFO | COO | ManagingMember | GeneralPartner | President | Treasurer | Trustee | SeniorManager | Other",
      "title": "string",
      "authorityDescription": "string",
      "verificationStatus": "Unverified | Verified | Failed | Waived"
    }
  ],
  "exemptions": [
    {
      "exemptionType": "PublicCompany | RegulatedFinancialInstitution | GovernmentEntity | CertainTrust | NonUSException | ProductException | Other",
      "exemptionReason": "string",
      "evidenceDocumentId": "string",
      "approvedBy": "string",
      "approvedDateTime": "datetime"
    }
  ]
}

⸻

13. Authority to act

"authorityToAct": [
  {
    "partyId": "string",
    "customerId": "string",
    "authorityType": "AuthorizedSigner | PowerOfAttorney | CorporateOfficer | Trustee | Custodian | Guardian | Agent | Administrator | Other",
    "authorityStartDate": "date",
    "authorityEndDate": "date",
    "scope": [
      "OpenAccount",
      "CloseAccount",
      "Transact",
      "WireTransfer",
      "Borrow",
      "PledgeCollateral",
      "ManageUsers",
      "ViewOnly",
      "Other"
    ],
    "authorizationDocumentIds": ["string"],
    "verificationStatus": "Pending | Verified | Failed | Revoked | Expired",
    "approvedBy": "string",
    "approvedDateTime": "datetime"
  }
]

⸻

14. Tax, FATCA, and CRS

"taxResidency": [
  {
    "partyId": "string",
    "countryCode": "string",
    "taxIdentifierType": "SSN | ITIN | EIN | ForeignTIN | GIIN | None | Other",
    "taxIdentifierMasked": "string",
    "tinUnavailableReason": "NotIssued | AppliedFor | Refused | Other",
    "taxFormType": "W9 | W8BEN | W8BENE | W8IMY | W8EXP | W8ECI | SelfCertification | Other",
    "taxFormDocumentId": "string",
    "formSignedDate": "date",
    "formExpirationDate": "date",
    "fatcaStatus": "USPerson | SpecifiedUSPerson | ForeignFinancialInstitution | NonFinancialForeignEntity | Exempt | Recalcitrant | Unknown",
    "crsStatus": "Reportable | NonReportable | PassiveNFE | ActiveNFE | FinancialInstitution | Unknown"
  }
]

⸻

15. Employment, business, and financial profile

"financialProfile": {
  "partyId": "string",
  "employment": {
    "employmentStatus": "Employed | SelfEmployed | Retired | Student | Unemployed | Homemaker | Other",
    "employerName": "string",
    "occupation": "string",
    "industry": "string",
    "annualIncome": "decimal",
    "incomeCurrency": "string"
  },
  "businessFinancials": {
    "annualRevenue": "decimal",
    "revenueCurrency": "string",
    "netWorth": "decimal",
    "assetsUnderManagement": "decimal",
    "employeeCount": "integer",
    "cashIntensiveIndicator": "boolean"
  },
  "expectedActivity": {
    "expectedMonthlyDepositsAmount": "decimal",
    "expectedMonthlyWithdrawalsAmount": "decimal",
    "expectedMonthlyTransactionCount": "integer",
    "expectedWireActivityIndicator": "boolean",
    "expectedInternationalActivityIndicator": "boolean",
    "expectedCashActivityIndicator": "boolean",
    "expectedACHActivityIndicator": "boolean",
    "expectedCheckActivityIndicator": "boolean",
    "expectedCardActivityIndicator": "boolean",
    "expectedCountries": ["string"],
    "expectedCounterpartyTypes": ["Individual", "Business", "Government", "FinancialInstitution", "Other"]
  }
}

⸻

16. Source of funds and source of wealth

"sourceOfFunds": [
  {
    "sourceId": "string",
    "partyId": "string",
    "sourceType": "Salary | BusinessRevenue | SaleOfAsset | Inheritance | InvestmentIncome | Gift | LoanProceeds | RealEstateSale | RetirementFunds | GovernmentBenefits | CryptoAssetSale | Other",
    "description": "string",
    "amount": "decimal",
    "currency": "string",
    "countryOfOrigin": "string",
    "supportingDocumentIds": ["string"],
    "verificationStatus": "Unverified | Verified | Failed | Waived",
    "riskFlags": ["string"]
  }
],
"sourceOfWealth": [
  {
    "sourceId": "string",
    "partyId": "string",
    "sourceType": "Employment | BusinessOwnership | Investments | RealEstate | Inheritance | FamilyWealth | LegalSettlement | Lottery | Other",
    "description": "string",
    "estimatedWealthAmount": "decimal",
    "currency": "string",
    "countryOfOrigin": "string",
    "supportingDocumentIds": ["string"],
    "verificationStatus": "Unverified | Verified | Failed | Waived"
  }
]

⸻

17. Screening

OFAC provides sanctions screening tools and list data, including the SDN List and consolidated non-SDN sanctions lists; OFAC notes that its sanctions search tool uses fuzzy logic but is not a substitute for appropriate due diligence.  ￼

"screening": {
  "screeningProfileId": "string",
  "partyId": "string",
  "screeningDateTime": "datetime",
  "screeningProvider": "string",
  "screeningScope": [
    "OFAC_SDN",
    "OFAC_NonSDN",
    "UN",
    "EU",
    "UK_HMT",
    "Canada",
    "PEP",
    "AdverseMedia",
    "LawEnforcement",
    "InternalBlacklist",
    "FraudConsortium",
    "Other"
  ],
  "overallScreeningStatus": "Clear | PotentialMatch | ConfirmedMatch | FalsePositive | PendingReview | Error",
  "matches": [
    {
      "matchId": "string",
      "listName": "string",
      "listType": "Sanctions | PEP | AdverseMedia | Watchlist | Internal | Other",
      "matchedName": "string",
      "matchedAttributes": ["Name", "DOB", "Address", "Country", "Identifier", "Alias"],
      "matchScore": "decimal",
      "matchStrength": "Weak | Medium | Strong | Exact",
      "disposition": "Pending | FalsePositive | TrueMatch | Escalated | Cleared",
      "dispositionReason": "string",
      "dispositionedBy": "string",
      "dispositionDateTime": "datetime",
      "evidence": {
        "sourceUrl": "string",
        "listRecordId": "string",
        "snapshotId": "string"
      }
    }
  ],
  "rescreening": {
    "frequency": "Daily | Weekly | Monthly | Quarterly | EventDriven | Other",
    "lastRescreenedDateTime": "datetime",
    "nextRescreeningDate": "date"
  }
}

⸻

18. PEP and adverse media

"pepAndAdverseMedia": {
  "partyId": "string",
  "pepStatus": "NotPEP | DomesticPEP | ForeignPEP | InternationalOrganizationPEP | CloseAssociate | FamilyMember | Unknown",
  "pepDetails": [
    {
      "positionTitle": "string",
      "country": "string",
      "organization": "string",
      "startDate": "date",
      "endDate": "date",
      "relationshipToPEP": "Self | Spouse | Parent | Child | Sibling | CloseAssociate | Other"
    }
  ],
  "adverseMediaStatus": "NoneFound | Potential | Confirmed | UnderReview",
  "adverseMediaCategories": [
    "MoneyLaundering",
    "Fraud",
    "Corruption",
    "SanctionsEvasion",
    "TaxEvasion",
    "Terrorism",
    "HumanTrafficking",
    "DrugTrafficking",
    "Cybercrime",
    "EnvironmentalCrime",
    "Other"
  ],
  "mediaArticles": [
    {
      "articleId": "string",
      "title": "string",
      "publisher": "string",
      "publicationDate": "date",
      "url": "string",
      "relevanceScore": "decimal",
      "disposition": "Relevant | NotRelevant | PendingReview"
    }
  ]
}

⸻

19. Fraud, device, and behavioral signals

"fraudSignals": {
  "partyId": "string",
  "device": {
    "deviceId": "string",
    "deviceFingerprint": "string",
    "ipAddress": "string",
    "ipCountry": "string",
    "vpnProxyTorIndicator": "boolean",
    "emulatorIndicator": "boolean",
    "jailbrokenRootedIndicator": "boolean"
  },
  "behavioral": {
    "typingPatternScore": "decimal",
    "sessionVelocityScore": "decimal",
    "copyPasteIndicator": "boolean",
    "abnormalNavigationIndicator": "boolean"
  },
  "identityFraud": {
    "syntheticIdentityRiskScore": "decimal",
    "identityTheftRiskScore": "decimal",
    "ssnIssueDateMismatchIndicator": "boolean",
    "deathMasterFileHitIndicator": "boolean",
    "addressVelocityCount": "integer",
    "phoneVelocityCount": "integer",
    "emailVelocityCount": "integer"
  },
  "fraudDecision": {
    "status": "Clear | Review | SuspectedFraud | ConfirmedFraud | Blocked",
    "reasonCodes": ["string"],
    "decisionDateTime": "datetime"
  }
}

⸻

20. Risk assessment

"riskAssessment": {
  "riskAssessmentId": "string",
  "customerId": "string",
  "assessmentType": "Initial | PeriodicRefresh | TriggerEvent | ManualReview | ProductChange | Other",
  "assessmentDateTime": "datetime",
  "methodologyVersion": "string",
  "overallRiskRating": "Low | Medium | High | Prohibited | Unknown",
  "riskScore": "decimal",
  "riskFactors": [
    {
      "factorType": "CustomerType | Geography | Product | Channel | TransactionActivity | OccupationIndustry | EntityStructure | BeneficialOwnership | Sanctions | PEP | AdverseMedia | Fraud | CashActivity | CryptoActivity | Other",
      "factorValue": "string",
      "factorScore": "decimal",
      "weight": "decimal",
      "reasonCodes": ["string"]
    }
  ],
  "riskOverrides": [
    {
      "fromRiskRating": "string",
      "toRiskRating": "string",
      "overrideReason": "string",
      "approvedBy": "string",
      "approvalDateTime": "datetime"
    }
  ],
  "decision": {
    "decisionType": "Approve | Reject | Escalate | RequestMoreInformation | Restrict | Offboard",
    "decisionReason": "string",
    "decisionedBy": "System | Analyst | Manager | Committee",
    "decisionDateTime": "datetime"
  }
}

⸻

21. CDD / EDD lifecycle

The CDD lifecycle should include understanding the nature and purpose of the customer relationship and ongoing monitoring. FFIEC guidance treats ongoing CDD as part of the bank’s risk-based AML program.  ￼

"dueDiligence": {
  "customerId": "string",
  "dueDiligenceLevel": "Simplified | Standard | Enhanced | Prohibited | NotRequired",
  "cipStatus": "NotStarted | Pending | Complete | Failed | Waived | Exception",
  "cddStatus": "NotStarted | Pending | Complete | Failed | Waived | Exception",
  "eddStatus": "NotRequired | Pending | Complete | Failed | Waived | Exception",
  "relationshipPurpose": "string",
  "expectedUseOfProducts": ["string"],
  "informationRequested": [
    {
      "requestId": "string",
      "informationType": "IdentityDocument | ProofOfAddress | BusinessRegistration | BeneficialOwnership | SourceOfFunds | SourceOfWealth | TaxForm | Explanation | Other",
      "requestDateTime": "datetime",
      "dueDate": "date",
      "status": "Requested | Received | Accepted | Rejected | Waived"
    }
  ],
  "edd": {
    "eddTriggers": [
      "HighRiskJurisdiction",
      "PEP",
      "AdverseMedia",
      "ComplexOwnership",
      "CashIntensiveBusiness",
      "MSB",
      "Crypto",
      "ForeignFinancialInstitution",
      "PrivateBanking",
      "HighTransactionVolume",
      "Other"
    ],
    "siteVisitRequiredIndicator": "boolean",
    "seniorManagementApprovalRequiredIndicator": "boolean",
    "seniorManagementApproval": {
      "approvedBy": "string",
      "approvalDateTime": "datetime",
      "approvalNotes": "string"
    },
    "enhancedNarrative": "string",
    "reviewFrequency": "Monthly | Quarterly | SemiAnnual | Annual | Biennial | EventDriven"
  }
}

⸻

22. Ongoing monitoring

"monitoring": {
  "customerId": "string",
  "monitoringStatus": "Active | Suspended | Closed | Offboarded",
  "periodicReview": {
    "reviewFrequency": "Monthly | Quarterly | SemiAnnual | Annual | Biennial | Triennial | EventDriven",
    "lastReviewDate": "date",
    "nextReviewDate": "date",
    "reviewStatus": "NotDue | Due | Overdue | InProgress | Complete | Waived"
  },
  "triggerEvents": [
    {
      "eventId": "string",
      "eventType": "AddressChange | OwnershipChange | ProductChange | RiskScoreChange | SanctionsHit | PEPHit | AdverseMediaHit | TransactionAnomaly | DormancyReactivation | NegativeNews | LawEnforcementRequest | Other",
      "eventDateTime": "datetime",
      "severity": "Low | Medium | High | Critical",
      "status": "Open | Closed | Escalated",
      "relatedCaseId": "string"
    }
  ],
  "transactionMonitoringProfile": {
    "scenarioSet": "string",
    "peerGroup": "string",
    "expectedActivityProfileId": "string",
    "lastModelScore": "decimal",
    "lastAlertDateTime": "datetime"
  }
}

⸻

23. Case management

"cases": [
  {
    "caseId": "string",
    "customerId": "string",
    "caseType": "KYCReview | SanctionsReview | PEPReview | AdverseMediaReview | FraudReview | AMLAlert | SARInvestigation | CTRReview | Offboarding | Other",
    "priority": "Low | Medium | High | Critical",
    "status": "Open | PendingCustomer | PendingInternal | Escalated | Closed | Reopened",
    "createdDateTime": "datetime",
    "createdBy": "string",
    "assignedTo": "string",
    "queue": "string",
    "slaDueDateTime": "datetime",
    "relatedPartyIds": ["string"],
    "relatedDocumentIds": ["string"],
    "relatedScreeningMatchIds": ["string"],
    "caseNarrative": "string",
    "actions": [
      {
        "actionId": "string",
        "actionType": "RequestInfo | ReviewDocument | ClearMatch | Escalate | Approve | Reject | FileSAR | FileCTR | RestrictAccount | Offboard | Other",
        "actionBy": "string",
        "actionDateTime": "datetime",
        "notes": "string"
      }
    ],
    "disposition": {
      "dispositionType": "Cleared | ConfirmedIssue | SARFiled | NoSAR | AccountRestricted | Offboarded | Rejected | Other",
      "dispositionReason": "string",
      "closedBy": "string",
      "closedDateTime": "datetime"
    }
  }
]

⸻

24. Regulatory reporting support

This schema should not replace a bank’s SAR/CTR filing platform, but it should provide the structured source data needed for investigations and reporting.

"regulatoryReports": [
  {
    "reportId": "string",
    "customerId": "string",
    "reportType": "SAR | CTR | 314a | 314b | OFACBlockingReport | OFACRejectReport | InternalEscalation | Other",
    "reportStatus": "Draft | Filed | Amended | Withdrawn | NotFiled | Pending",
    "filingDate": "date",
    "filingReferenceNumber": "string",
    "filingSystem": "BSAEfiling | Vendor | Internal | Other",
    "relatedCaseId": "string",
    "relatedTransactionIds": ["string"],
    "narrative": "string",
    "confidentialityClassification": "Restricted | HighlyRestricted",
    "retentionPolicy": {
      "retainUntilDate": "date",
      "legalHoldIndicator": "boolean"
    }
  }
]

⸻

25. Consent, privacy, and permissible purpose

"consents": [
  {
    "consentId": "string",
    "partyId": "string",
    "consentType": "IdentityVerification | CreditHeaderCheck | BiometricProcessing | ElectronicCommunications | TermsOfService | PrivacyPolicy | DataSharing | OpenBanking | TaxCertification | Other",
    "consentStatus": "Granted | Denied | Revoked | Expired",
    "consentDateTime": "datetime",
    "expirationDateTime": "datetime",
    "captureMethod": "Checkbox | ESignature | Verbal | Paper | API | Other",
    "ipAddress": "string",
    "userAgent": "string",
    "documentVersion": "string",
    "evidenceDocumentId": "string"
  }
]

⸻

26. Audit and provenance

"audit": {
  "createdDateTime": "datetime",
  "createdBy": "string",
  "lastUpdatedDateTime": "datetime",
  "lastUpdatedBy": "string",
  "dataLineage": [
    {
      "fieldPath": "string",
      "source": "Customer | Employee | Vendor | PublicRegistry | DocumentOCR | Calculated | Imported | ManualOverride",
      "sourceSystem": "string",
      "sourceRecordId": "string",
      "captureDateTime": "datetime",
      "confidenceScore": "decimal"
    }
  ],
  "changeHistory": [
    {
      "changeId": "string",
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
      "accessedBy": "string",
      "accessDateTime": "datetime",
      "accessPurpose": "Onboarding | Review | Investigation | Audit | Support | Other"
    }
  ]
}

⸻

27. Field-level metadata pattern

For regulated KYC data, important fields should support provenance and verification metadata.

{
  "value": "any",
  "source": "Customer | Document | Vendor | PublicRegistry | Employee | Calculated | Imported",
  "sourceSystem": "string",
  "sourceRecordId": "string",
  "capturedDateTime": "datetime",
  "verifiedIndicator": "boolean",
  "verificationStatus": "Unverified | Verified | Failed | Waived | Expired",
  "verificationMethod": "Documentary | NonDocumentary | Database | Registry | Manual | Other",
  "confidenceScore": "decimal",
  "sensitivity": "Public | Internal | Confidential | NPI | Restricted | Biometric | GovernmentId | TaxId",
  "retentionClass": "KYC | AML | Tax | Fraud | Consent | Audit",
  "lastUpdatedDateTime": "datetime",
  "lastUpdatedBy": "string"
}

⸻

28. Recommended relational / domain model

KYCProfile
 ├── Customer
 ├── Party
 │    ├── Individual
 │    ├── Organization
 │    ├── Trust
 │    ├── Identifier
 │    ├── Address
 │    ├── ContactPoint
 │    └── Document
 ├── PartyRelationship
 ├── BeneficialOwnership
 │    ├── BeneficialOwner
 │    ├── OwnershipPath
 │    └── ControlPerson
 ├── AuthorityToAct
 ├── IdentityVerification
 ├── TaxResidency
 ├── FinancialProfile
 ├── SourceOfFunds
 ├── SourceOfWealth
 ├── ScreeningProfile
 │    ├── SanctionsMatch
 │    ├── PEPMatch
 │    └── AdverseMediaMatch
 ├── FraudSignal
 ├── RiskAssessment
 │    ├── RiskFactor
 │    └── RiskOverride
 ├── DueDiligenceReview
 ├── PeriodicReview
 ├── MonitoringTrigger
 ├── Case
 │    ├── CaseAction
 │    └── CaseDisposition
 ├── RegulatoryReport
 ├── Consent
 ├── AuditEvent
 └── Extension

⸻

29. KYC integration coverage matrix

Use case	Schema areas required
Retail account opening	Individual, identifiers, address, contact, CIP, document verification, sanctions, fraud, risk
Business account opening	Organization, formation, business classification, beneficial ownership, control persons, KYB documents
Beneficial ownership CDD	Legal entity customer, ownership percent, control person, certification, verification
Digital onboarding	Identity verification, device, liveness, document OCR, consent, risk score
Sanctions screening	Party, aliases, identifiers, address, nationality, screening matches, disposition
PEP/adverse media	PEP details, related parties, media articles, case management
Enhanced due diligence	Source of funds, source of wealth, high-risk triggers, senior approval
Periodic KYC refresh	Monitoring, review frequency, changed attributes, updated documents
Transaction monitoring	Expected activity, risk profile, trigger events, AML cases
SAR investigation	Customer, parties, cases, narrative, related transactions, evidence
Tax compliance	Tax residency, W-9/W-8, FATCA/CRS status
Fraud prevention	Device, behavioral, synthetic identity, velocity signals
Vendor orchestration	Provider transaction IDs, verification methods, evidence, match disposition
Audit/exam support	Provenance, decision trail, policy version, actor, timestamps

⸻

30. Standard enumerations to maintain centrally

CustomerType
PartyType
PartyRole
IdentifierType
DocumentType
VerificationStatus
VerificationMethod
AddressType
ContactPointType
LegalEntityType
BusinessIndustryType
HighRiskBusinessType
BeneficialOwnerType
OwnershipType
ControlPersonType
ScreeningListType
ScreeningMatchStatus
PEPType
AdverseMediaCategory
RiskRating
RiskFactorType
DueDiligenceLevel
EDDTrigger
CaseType
CaseStatus
CaseDisposition
RegulatoryReportType
ConsentType
ProductType
JurisdictionRiskRating
ReviewFrequency

⸻

31. Minimal viable schema vs. enterprise schema

MVP KYC schema

For a fintech or bank POS onboarding flow:

Customer
Party
Individual / Organization
Identifier
Address
ContactPoint
Document
IdentityVerification
SanctionsScreening
RiskAssessment
Consent
Audit

Bank-grade enterprise schema

For a regulated bank or large vendor:

Customer
Party
Individual / Organization / Trust
PartyRelationship
BeneficialOwnership
ControlPerson
AuthorityToAct
Identifier
Address
ContactPoint
Document
IdentityVerification
TaxResidency
FinancialProfile
SourceOfFunds
SourceOfWealth
Screening
PEP
AdverseMedia
FraudSignals
RiskAssessment
CDD
EDD
PeriodicReview
OngoingMonitoring
CaseManagement
RegulatoryReports
Consent
Audit
DataLineage
Extensions

⸻

32. Suggested API resource model

POST   /kyc-profiles
GET    /kyc-profiles/{profileId}
PATCH  /kyc-profiles/{profileId}
POST   /kyc-profiles/{id}/parties
PATCH  /kyc-profiles/{id}/parties/{partyId}
POST   /kyc-profiles/{id}/documents
POST   /kyc-profiles/{id}/identity-verifications
POST   /kyc-profiles/{id}/screenings
POST   /kyc-profiles/{id}/risk-assessments
POST   /kyc-profiles/{id}/beneficial-ownership
PATCH  /kyc-profiles/{id}/beneficial-ownership/{ownerId}
POST   /kyc-profiles/{id}/due-diligence-reviews
POST   /kyc-profiles/{id}/periodic-reviews
POST   /kyc-profiles/{id}/cases
PATCH  /kyc-profiles/{id}/cases/{caseId}
POST   /kyc-profiles/{id}/regulatory-reports
POST   /kyc-profiles/{id}/consents
GET    /kyc-profiles/{id}/audit

⸻

33. Recommended schema layers

Layer 1: Identity & CIP
Individual or business identity, addresses, identifiers, documents, consent, verification.
Layer 2: CDD / KYB
Business profile, relationship purpose, expected activity, beneficial ownership, control persons.
Layer 3: Screening & Risk
Sanctions, PEP, adverse media, fraud, country/product/channel risk, risk scoring.
Layer 4: EDD & Case Management
High-risk triggers, source of funds, source of wealth, investigations, approvals, dispositions.
Layer 5: Ongoing Monitoring & Reporting
Periodic refresh, trigger events, transaction-monitoring linkage, SAR/CTR/OFAC support, audit.

⸻

34. Critical implementation recommendations

Separate customer identity from account/product.
The same customer may open deposits, cards, loans, brokerage, merchant services, and treasury products. KYC should be reusable but refreshed as risk changes.

Model beneficial ownership as a graph, not a flat table.
Complex companies may have indirect ownership through multiple entities. A graph-like ownership path is much more durable.

Keep sanctions/PEP/adverse-media decisions auditable.
False-positive disposition is one of the most important examiner-facing workflows.

Store vendor evidence, not just vendor result.
Save provider transaction ID, request/response hash, matched fields, score, policy version, list version, and reviewer decision.

Separate protected or sensitive data.
Government IDs, tax IDs, biometrics, watchlist results, SAR-related data, and adverse media evidence should have strict access controls.

Use event-driven monitoring.
Trigger review on ownership changes, address changes, new countries, abnormal activity, sanctions hits, PEP changes, product upgrades, and dormant-account reactivation.

Do not hard-code only U.S. persons.
Even U.S. banks need foreign nationals, nonresident aliens, foreign businesses, offshore trusts, foreign tax IDs, passports, visas, and non-U.S. registries.

Treat FinCEN BOI reporting and bank CDD as related but distinct.
Corporate Transparency Act BOI reporting rules have changed, but banks still need their own CDD/beneficial ownership schema to support account-opening and risk-based AML obligations.  ￼

⸻

35. Final canonical domains

A comprehensive KYC/KYB schema should include:

1. Customer profile
2. Party model
3. Individual identity
4. Organization / KYB profile
5. Trust / estate profile
6. Party relationships
7. Identifiers
8. Addresses
9. Contact points
10. Documents and evidence
11. Identity verification
12. Digital identity assurance
13. Authority to act
14. Beneficial ownership
15. Control persons
16. Tax residency / FATCA / CRS
17. Employment / occupation
18. Business classification
19. Financial profile
20. Expected activity
21. Source of funds
22. Source of wealth
23. Sanctions screening
24. PEP screening
25. Adverse media
26. Fraud/device/behavioral signals
27. Risk scoring
28. CDD
29. EDD
30. Periodic review
31. Ongoing monitoring
32. Trigger events
33. Case management
34. Regulatory reporting support
35. Consents and privacy
36. Data lineage
37. Audit trail
38. Retention/legal hold
39. Security classification
40. Extensions

This structure should support the majority of banks, fintechs, KYC vendors, onboarding platforms, AML systems, case-management tools, and regulatory reporting workflows in the U.S., while remaining flexible enough for global KYC/KYB expansion.