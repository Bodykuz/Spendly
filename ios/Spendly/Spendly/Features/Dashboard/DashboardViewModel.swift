import Foundation

@MainActor
final class DashboardViewModel: ObservableObject {
    @Published var dashboard: DashboardDTO? = nil
    @Published var isLoading = false
    @Published var error: String? = nil

    private let api: APIClient
    init(api: APIClient) { self.api = api }

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let d: DashboardDTO = try await api.send(API.dashboard)
            dashboard = d
        } catch {
            self.error = error.localizedDescription
        }
    }
}
