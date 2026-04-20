import Foundation

@MainActor
final class InsightsViewModel: ObservableObject {
    @Published var insights: [InsightDTO] = []
    @Published var isLoading = false
    @Published var error: String? = nil

    private let api: APIClient
    init(api: APIClient) { self.api = api }

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            insights = try await api.send(API.insights)
        } catch { self.error = error.localizedDescription }
    }
}
