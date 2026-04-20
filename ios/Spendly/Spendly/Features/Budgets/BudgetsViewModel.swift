import Foundation

@MainActor
final class BudgetsViewModel: ObservableObject {
    @Published var budgets: [BudgetDTO] = []
    @Published var goals: [GoalDTO] = []
    @Published var categories: [CategoryDTO] = []
    @Published var isLoading = false
    @Published var error: String? = nil

    private let api: APIClient
    init(api: APIClient) { self.api = api }

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            async let b: [BudgetDTO] = api.send(API.budgets)
            async let g: [GoalDTO] = api.send(API.goals)
            async let c: [CategoryDTO] = api.send(API.categories)
            self.budgets = try await b
            self.goals = try await g
            self.categories = try await c
        } catch { self.error = error.localizedDescription }
    }

    func createBudget(categoryId: String, amount: Decimal) async {
        do {
            let _: BudgetDTO = try await api.send(API.createBudget(
                categoryId: categoryId, amount: amount, currency: "PLN"
            ))
            await load()
        } catch { self.error = error.localizedDescription }
    }

    func deleteBudget(_ id: String) async {
        do {
            try await api.sendVoid(API.deleteBudget(id: id))
            await load()
        } catch { self.error = error.localizedDescription }
    }

    func createGoal(name: String, target: Decimal, date: Date?) async {
        do {
            let _: GoalDTO = try await api.send(API.createGoal(name: name, target: target, currency: "PLN", targetDate: date))
            await load()
        } catch { self.error = error.localizedDescription }
    }

    func deleteGoal(_ id: String) async {
        do {
            try await api.sendVoid(API.deleteGoal(id: id))
            await load()
        } catch { self.error = error.localizedDescription }
    }
}
