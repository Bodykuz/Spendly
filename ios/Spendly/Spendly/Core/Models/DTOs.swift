import Foundation

// MARK: - Auth

struct UserDTO: Codable, Equatable, Identifiable {
    let id: String
    let email: String
    let fullName: String?
    let currency: String
    let locale: String
    let isVerified: Bool
    let createdAt: Date
}

struct TokenPairDTO: Codable, Equatable {
    let accessToken: String
    let refreshToken: String
    let tokenType: String
    let expiresIn: Int
}

struct AuthResponseDTO: Codable, Equatable {
    let user: UserDTO
    let tokens: TokenPairDTO
}

// MARK: - Banks

struct InstitutionDTO: Codable, Identifiable, Equatable {
    let id: String
    let name: String
    let bic: String?
    let logo: String?
    let country: String
    let transactionTotalDays: Int?
}

enum ConsentStatusDTO: String, Codable {
    case pending, linked, expired, revoked, error
}

struct BankConnectionDTO: Codable, Identifiable, Equatable {
    let id: String
    let institutionId: String
    let institutionName: String
    let institutionLogo: String?
    let institutionCountry: String
    let status: ConsentStatusDTO
    let consentExpiresAt: Date?
    let lastSyncedAt: Date?
    let createdAt: Date
}

struct LinkBankResponseDTO: Codable, Equatable {
    let connectionId: String
    let consentUrl: String
    let expiresAt: Date?
}

// MARK: - Accounts & Transactions

struct AccountDTO: Codable, Identifiable, Equatable {
    let id: String
    let bankConnectionId: String
    let iban: String?
    let name: String?
    let ownerName: String?
    let currency: String
    let product: String?
    let balanceAvailable: Decimal
    let balanceCurrent: Decimal
    let balanceUpdatedAt: Date?
}

struct CategoryDTO: Codable, Identifiable, Equatable {
    let id: String
    let slug: String
    let name: String
    let icon: String
    let color: String
    let isIncome: Bool
    let isSystem: Bool
}

enum TransactionStatusDTO: String, Codable { case booked, pending }

struct TransactionDTO: Codable, Identifiable, Equatable {
    let id: String
    let accountId: String
    let category: CategoryDTO?
    let amount: Decimal
    let currency: String
    let bookingDate: Date
    let valueDate: Date?
    let status: TransactionStatusDTO
    let counterpartyName: String?
    let description: String?
    let isRecurring: Bool
    let isSubscription: Bool
    let isSalary: Bool
    let notes: String?
}

struct TransactionPageDTO: Codable, Equatable {
    let items: [TransactionDTO]
    let total: Int
    let page: Int
    let size: Int
}

// MARK: - Analytics / Insights

struct MonthlyCashflowDTO: Codable, Equatable, Identifiable {
    var id: String { month }
    let month: String
    let income: Decimal
    let expense: Decimal
    let net: Decimal
}

struct CategorySpendDTO: Codable, Equatable, Identifiable {
    let categoryId: String?
    let categoryName: String
    let icon: String
    let color: String
    let amount: Decimal
    let pctOfTotal: Double
    var id: String { categoryId ?? categoryName }
}

struct DashboardDTO: Codable, Equatable {
    let currency: String
    let totalBalance: Decimal
    let monthIncome: Decimal
    let monthExpense: Decimal
    let monthNet: Decimal
    let linkedBanks: Int
    let accounts: Int
    let cashflow: [MonthlyCashflowDTO]
    let topCategories: [CategorySpendDTO]
}

struct CashflowResponseDTO: Codable, Equatable {
    let currency: String
    let months: [MonthlyCashflowDTO]
}

struct CategoryBreakdownDTO: Codable, Equatable {
    let currency: String
    let total: Decimal
    let categories: [CategorySpendDTO]
    let startDate: Date
    let endDate: Date
}

struct InsightDTO: Codable, Equatable, Identifiable {
    let id: String
    let kind: String
    let title: String
    let body: String
    let severity: String
    let amount: Decimal?
    let currency: String?
}

// MARK: - Budgets / Goals

struct BudgetDTO: Codable, Equatable, Identifiable {
    let id: String
    let categoryId: String
    let amount: Decimal
    let period: String
    let currency: String
    let spent: Decimal
    let remaining: Decimal
    let pctUsed: Double
}

struct GoalDTO: Codable, Equatable, Identifiable {
    let id: String
    let name: String
    let targetAmount: Decimal
    let currentAmount: Decimal
    let currency: String
    let targetDate: Date?
    let icon: String
    let color: String
    let pctComplete: Double
}
