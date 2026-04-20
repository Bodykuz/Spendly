import Foundation

@MainActor
final class AuthViewModel: ObservableObject {
    enum Mode { case signIn, signUp }

    @Published var mode: Mode = .signIn
    @Published var email: String = ""
    @Published var password: String = ""
    @Published var fullName: String = ""
    @Published var isLoading: Bool = false
    @Published var errorMessage: String? = nil

    private let api: APIClient
    private let session: SessionStore

    init(api: APIClient, session: SessionStore) {
        self.api = api
        self.session = session
    }

    var canSubmit: Bool {
        email.contains("@") && password.count >= 8 && !isLoading
    }

    func submit() async {
        guard canSubmit else { return }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            let endpoint: Endpoint = (mode == .signIn)
                ? API.signIn(email: email, password: password)
                : API.signUp(email: email, password: password, fullName: fullName.isEmpty ? nil : fullName)
            let auth: AuthResponseDTO = try await api.send(endpoint)
            session.store(auth: auth)
        } catch let err as APIError {
            errorMessage = err.errorDescription
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func toggleMode() {
        mode = (mode == .signIn) ? .signUp : .signIn
        errorMessage = nil
    }
}
