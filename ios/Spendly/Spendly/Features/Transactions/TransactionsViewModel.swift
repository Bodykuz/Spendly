import Foundation

@MainActor
final class TransactionsViewModel: ObservableObject {
    @Published var transactions: [TransactionDTO] = []
    @Published var categories: [CategoryDTO] = []
    @Published var isLoading = false
    @Published var hasMore = true
    @Published var page = 1
    @Published var pageSize = 50
    @Published var search: String = ""
    @Published var onlyExpenses = false
    @Published var onlyIncome = false
    @Published var categoryFilter: CategoryDTO? = nil
    @Published var error: String? = nil

    private let api: APIClient
    private var loadTask: Task<Void, Never>?

    init(api: APIClient) { self.api = api }

    func loadFirst() async {
        page = 1; hasMore = true; transactions = []
        await load()
    }

    func loadMore() async {
        guard hasMore, !isLoading else { return }
        await load()
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let resp: TransactionPageDTO = try await api.send(
                API.transactions(
                    page: page, size: pageSize,
                    search: search.isEmpty ? nil : search,
                    categoryId: categoryFilter?.id,
                    accountId: nil,
                    onlyExpenses: onlyExpenses,
                    onlyIncome: onlyIncome
                )
            )
            transactions += resp.items
            hasMore = transactions.count < resp.total && !resp.items.isEmpty
            page += 1
        } catch {
            self.error = error.localizedDescription
        }
    }

    func loadCategories() async {
        do {
            let cats: [CategoryDTO] = try await api.send(API.categories)
            self.categories = cats
        } catch { /* silent */ }
    }

    func recategorize(_ tx: TransactionDTO, to category: CategoryDTO?) async {
        do {
            let updated: TransactionDTO = try await api.send(API.recategorize(txId: tx.id, categoryId: category?.id))
            if let idx = transactions.firstIndex(where: { $0.id == tx.id }) {
                transactions[idx] = updated
            }
        } catch { self.error = error.localizedDescription }
    }

    func debouncedSearch() {
        loadTask?.cancel()
        loadTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 350_000_000)
            guard let self, !Task.isCancelled else { return }
            await self.loadFirst()
        }
    }
}
