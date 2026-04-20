import Combine
import Foundation
import SwiftUI

/// Globally reachable app dependencies. Held as `@StateObject` in `SpendlyApp`
/// but also exposed via `AppEnvironment.shared` so view-model `init()`s can
/// reach the API client without prop-drilling.
@MainActor
final class AppEnvironment: ObservableObject {
    static let shared = AppEnvironment()

    let session: SessionStore
    let api: APIClient

    @Published var pendingBankCallback: BankCallbackResult? = nil

    init() {
        let session = SessionStore(keychain: KeychainStore())
        let baseURL = URL(string: Self.backendBaseURL)!
        self.session = session
        self.api = APIClient(baseURL: baseURL, session: session)
    }

    static var backendBaseURL: String {
        if let v = Bundle.main.object(forInfoDictionaryKey: "APIBaseURL") as? String,
           !v.isEmpty {
            return v
        }
        return "http://localhost:8000"
    }

    static var callbackScheme: String {
        if let v = Bundle.main.object(forInfoDictionaryKey: "BankCallbackScheme") as? String,
           !v.isEmpty {
            return v
        }
        return "spendly"
    }

    func handleDeepLink(_ url: URL) {
        guard url.scheme == Self.callbackScheme, url.host == "bank" else { return }
        let components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        let params = components?.queryItems?.reduce(into: [String: String]()) { acc, it in
            if let v = it.value { acc[it.name] = v }
        } ?? [:]
        pendingBankCallback = BankCallbackResult(
            status: params["status"] ?? "unknown",
            connectionId: params["connection_id"],
            error: params["error"]
        )
    }
}

struct BankCallbackResult: Equatable {
    let status: String
    let connectionId: String?
    let error: String?
}
