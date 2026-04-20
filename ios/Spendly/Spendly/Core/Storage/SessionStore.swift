import Combine
import Foundation

@MainActor
final class SessionStore: ObservableObject {
    @Published private(set) var user: UserDTO? = nil
    @Published private(set) var isAuthenticated: Bool = false

    private let keychain: KeychainStore
    private let accessKey = "access_token"
    private let refreshKey = "refresh_token"

    init(keychain: KeychainStore) {
        self.keychain = keychain
        self.isAuthenticated = keychain.get(accessKey) != nil
    }

    var accessToken: String? { keychain.get(accessKey) }
    var refreshToken: String? { keychain.get(refreshKey) }

    func store(auth: AuthResponseDTO) {
        keychain.set(auth.tokens.accessToken, for: accessKey)
        keychain.set(auth.tokens.refreshToken, for: refreshKey)
        user = auth.user
        isAuthenticated = true
    }

    func updateTokens(_ tokens: TokenPairDTO) {
        keychain.set(tokens.accessToken, for: accessKey)
        keychain.set(tokens.refreshToken, for: refreshKey)
    }

    func updateUser(_ user: UserDTO) {
        self.user = user
    }

    func signOut() {
        keychain.remove(accessKey)
        keychain.remove(refreshKey)
        user = nil
        isAuthenticated = false
    }
}
