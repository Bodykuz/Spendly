import Foundation

enum HTTPMethod: String { case get = "GET", post = "POST", patch = "PATCH", delete = "DELETE", put = "PUT" }

struct Endpoint {
    let method: HTTPMethod
    let path: String
    var query: [URLQueryItem] = []
    var body: Data? = nil
    var requiresAuth: Bool = true
    var contentType: String = "application/json"
}

enum API {
    // Auth
    static func signUp(email: String, password: String, fullName: String?) -> Endpoint {
        let b: [String: Any?] = ["email": email, "password": password, "full_name": fullName]
        return Endpoint(method: .post, path: "/v1/auth/signup", body: try? JSONSerialization.data(withJSONObject: b.compactMapValues { $0 }), requiresAuth: false)
    }
    static func signIn(email: String, password: String) -> Endpoint {
        let b: [String: String] = ["email": email, "password": password]
        return Endpoint(method: .post, path: "/v1/auth/signin", body: try? JSONSerialization.data(withJSONObject: b), requiresAuth: false)
    }
    static func refresh(refreshToken: String) -> Endpoint {
        Endpoint(method: .post, path: "/v1/auth/refresh",
                 body: try? JSONSerialization.data(withJSONObject: ["refresh_token": refreshToken]),
                 requiresAuth: false)
    }
    static var me: Endpoint { .init(method: .get, path: "/v1/auth/me") }

    // Banks
    static func institutions(country: String = "PL") -> Endpoint {
        .init(method: .get, path: "/v1/banks/institutions", query: [.init(name: "country", value: country)])
    }
    static func linkBank(institutionId: String, redirectUri: String) -> Endpoint {
        .init(method: .post, path: "/v1/banks/link",
              body: try? JSONSerialization.data(withJSONObject: [
                  "institution_id": institutionId, "redirect_uri": redirectUri
              ]))
    }
    static var connections: Endpoint { .init(method: .get, path: "/v1/banks/connections") }
    static func connection(id: String) -> Endpoint {
        .init(method: .get, path: "/v1/banks/connections/\(id)")
    }
    static func reconnect(id: String) -> Endpoint {
        .init(method: .post, path: "/v1/banks/connections/\(id)/reconnect")
    }
    static func removeConnection(id: String) -> Endpoint {
        .init(method: .delete, path: "/v1/banks/connections/\(id)")
    }
    static func syncConnection(id: String) -> Endpoint {
        .init(method: .post, path: "/v1/banks/connections/\(id)/sync")
    }

    // Accounts / Transactions
    static var accounts: Endpoint { .init(method: .get, path: "/v1/accounts") }
    static func transactions(page: Int, size: Int, search: String?, categoryId: String?, accountId: String?, onlyExpenses: Bool = false, onlyIncome: Bool = false) -> Endpoint {
        var q: [URLQueryItem] = [
            .init(name: "page", value: "\(page)"),
            .init(name: "size", value: "\(size)"),
        ]
        if let s = search, !s.isEmpty { q.append(.init(name: "search", value: s)) }
        if let c = categoryId { q.append(.init(name: "category_id", value: c)) }
        if let a = accountId { q.append(.init(name: "account_id", value: a)) }
        if onlyExpenses { q.append(.init(name: "only_expenses", value: "true")) }
        if onlyIncome { q.append(.init(name: "only_income", value: "true")) }
        return Endpoint(method: .get, path: "/v1/transactions", query: q)
    }
    static func recategorize(txId: String, categoryId: String?) -> Endpoint {
        let body: [String: Any] = categoryId.map { ["category_id": $0] } ?? ["category_id": NSNull()]
        return Endpoint(method: .patch, path: "/v1/transactions/\(txId)/category",
                        body: try? JSONSerialization.data(withJSONObject: body))
    }
    static var categories: Endpoint { .init(method: .get, path: "/v1/transactions/categories/list") }

    // Analytics
    static var dashboard: Endpoint { .init(method: .get, path: "/v1/analytics/dashboard") }
    static func cashflow(months: Int) -> Endpoint {
        .init(method: .get, path: "/v1/analytics/cashflow", query: [.init(name: "months", value: "\(months)")])
    }
    static var categoryBreakdown: Endpoint { .init(method: .get, path: "/v1/analytics/categories") }

    // Insights
    static var insights: Endpoint { .init(method: .get, path: "/v1/insights") }

    // Budgets / Goals
    static var budgets: Endpoint { .init(method: .get, path: "/v1/budgets") }
    static func createBudget(categoryId: String, amount: Decimal, currency: String) -> Endpoint {
        let b: [String: Any] = ["category_id": categoryId, "amount": "\(amount)", "currency": currency, "period": "monthly"]
        return .init(method: .post, path: "/v1/budgets", body: try? JSONSerialization.data(withJSONObject: b))
    }
    static func deleteBudget(id: String) -> Endpoint {
        .init(method: .delete, path: "/v1/budgets/\(id)")
    }

    static var goals: Endpoint { .init(method: .get, path: "/v1/goals") }
    static func createGoal(name: String, target: Decimal, currency: String, targetDate: Date?) -> Endpoint {
        let df = ISO8601DateFormatter()
        var b: [String: Any] = ["name": name, "target_amount": "\(target)", "currency": currency]
        if let td = targetDate {
            b["target_date"] = String(df.string(from: td).prefix(10))
        }
        return .init(method: .post, path: "/v1/goals", body: try? JSONSerialization.data(withJSONObject: b))
    }
    static func deleteGoal(id: String) -> Endpoint {
        .init(method: .delete, path: "/v1/goals/\(id)")
    }
}
