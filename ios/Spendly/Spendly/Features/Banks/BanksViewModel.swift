import AuthenticationServices
import Combine
import Foundation
import UIKit

@MainActor
final class BanksViewModel: ObservableObject {
    @Published var connections: [BankConnectionDTO] = []
    @Published var institutions: [InstitutionDTO] = []
    @Published var isLoading = false
    @Published var error: String? = nil
    @Published var searchText: String = ""

    private let api: APIClient
    private var authSession: ASWebAuthenticationSession?
    private var contextProvider = AuthContextProvider()

    var filteredInstitutions: [InstitutionDTO] {
        guard !searchText.isEmpty else { return institutions }
        let q = searchText.lowercased()
        return institutions.filter { $0.name.lowercased().contains(q) }
    }

    init(api: APIClient) { self.api = api }

    func loadConnections() async {
        do {
            let list: [BankConnectionDTO] = try await api.send(API.connections)
            connections = list
        } catch {
            self.error = error.localizedDescription
        }
    }

    func loadInstitutions() async {
        do {
            let list: [InstitutionDTO] = try await api.send(API.institutions())
            institutions = list.sorted { $0.name < $1.name }
        } catch {
            self.error = error.localizedDescription
        }
    }

    /// Initiates the PSD2 consent flow for the selected institution.
    /// Uses ASWebAuthenticationSession so the redirect back to the custom
    /// URL scheme is captured by Apple in a sandboxed way.
    func link(institution: InstitutionDTO) async {
        isLoading = true
        defer { isLoading = false }
        do {
            let redirect = "\(AppEnvironment.callbackScheme)://bank/callback"
            let resp: LinkBankResponseDTO = try await api.send(
                API.linkBank(institutionId: institution.id, redirectUri: redirect)
            )
            guard let url = URL(string: resp.consentUrl) else {
                error = "Nieprawidłowy URL zgody."
                return
            }

            try await openBankConsent(url: url)
            // Give backend a moment to pick up the callback, then refresh
            try? await Task.sleep(nanoseconds: 600_000_000)
            await loadConnections()

            if let conn = connections.first(where: { $0.id == resp.connectionId }),
               conn.status == .linked {
                try await sync(connection: conn)
            }
        } catch {
            self.error = error.localizedDescription
        }
    }

    func remove(connection: BankConnectionDTO) async {
        do {
            try await api.sendVoid(API.removeConnection(id: connection.id))
            await loadConnections()
        } catch { self.error = error.localizedDescription }
    }

    func reconnect(connection: BankConnectionDTO) async {
        do {
            let resp: LinkBankResponseDTO = try await api.send(API.reconnect(id: connection.id))
            if let url = URL(string: resp.consentUrl) {
                try await openBankConsent(url: url)
                await loadConnections()
            }
        } catch { self.error = error.localizedDescription }
    }

    func sync(connection: BankConnectionDTO) async throws {
        let _: [String: Int] = try await api.send(API.syncConnection(id: connection.id))
        await loadConnections()
    }

    // MARK: - ASWebAuthenticationSession bridge

    private func openBankConsent(url: URL) async throws {
        try await withCheckedThrowingContinuation { (cont: CheckedContinuation<Void, Error>) in
            let scheme = AppEnvironment.callbackScheme
            let session = ASWebAuthenticationSession(
                url: url, callbackURLScheme: scheme
            ) { callback, err in
                if let err {
                    cont.resume(throwing: err)
                    return
                }
                _ = callback  // AppEnvironment's onOpenURL will see the deep link as well.
                cont.resume()
            }
            session.presentationContextProvider = contextProvider
            session.prefersEphemeralWebBrowserSession = false
            self.authSession = session
            if !session.start() {
                cont.resume(throwing: APIError.invalidResponse)
            }
        }
    }
}

private final class AuthContextProvider: NSObject, ASWebAuthenticationPresentationContextProviding {
    func presentationAnchor(for _: ASWebAuthenticationSession) -> ASPresentationAnchor {
        UIApplication.shared.connectedScenes
            .compactMap { ($0 as? UIWindowScene)?.keyWindow }
            .first ?? ASPresentationAnchor()
    }
}
