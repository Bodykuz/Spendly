import SwiftUI

struct BudgetsView: View {
    @StateObject private var vm = BudgetsViewModel(api: AppEnvironment.shared.api)
    @State private var addingBudget = false
    @State private var addingGoal = false

    var body: some View {
        NavigationStack {
            List {
                Section("Budżety miesięczne") {
                    if vm.budgets.isEmpty {
                        Text("Brak budżetów. Dodaj pierwszy.")
                            .foregroundStyle(.secondary)
                    }
                    ForEach(vm.budgets) { b in
                        BudgetRow(budget: b, categories: vm.categories)
                            .swipeActions {
                                Button(role: .destructive) {
                                    Task { await vm.deleteBudget(b.id) }
                                } label: { Label("Usuń", systemImage: "trash") }
                            }
                    }
                    Button { addingBudget = true } label: {
                        Label("Dodaj budżet", systemImage: "plus.circle.fill")
                    }
                }

                Section("Cele oszczędnościowe") {
                    if vm.goals.isEmpty {
                        Text("Brak celów. Dodaj pierwszy.").foregroundStyle(.secondary)
                    }
                    ForEach(vm.goals) { g in
                        GoalRow(goal: g)
                            .swipeActions {
                                Button(role: .destructive) {
                                    Task { await vm.deleteGoal(g.id) }
                                } label: { Label("Usuń", systemImage: "trash") }
                            }
                    }
                    Button { addingGoal = true } label: {
                        Label("Dodaj cel", systemImage: "plus.circle.fill")
                    }
                }
            }
            .navigationTitle("Budżety i cele")
            .refreshable { await vm.load() }
            .task { await vm.load() }
            .sheet(isPresented: $addingBudget) {
                AddBudgetSheet(categories: vm.categories.filter { !$0.isIncome }) { cat, amt in
                    Task { await vm.createBudget(categoryId: cat.id, amount: amt) }
                    addingBudget = false
                }
            }
            .sheet(isPresented: $addingGoal) {
                AddGoalSheet { name, target, date in
                    Task { await vm.createGoal(name: name, target: target, date: date) }
                    addingGoal = false
                }
            }
        }
    }
}

private struct BudgetRow: View {
    let budget: BudgetDTO
    let categories: [CategoryDTO]

    var category: CategoryDTO? { categories.first { $0.id == budget.categoryId } }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Circle().fill(Money.colorFromHex(category?.color ?? "#6366F1"))
                    .frame(width: 10, height: 10)
                Text(category?.name ?? "Kategoria").bold()
                Spacer()
                Text("\(Money.format(budget.spent, currency: budget.currency)) / \(Money.format(budget.amount, currency: budget.currency))")
                    .font(.caption).foregroundStyle(.secondary)
            }
            ProgressView(value: min(budget.pctUsed, 100) / 100)
                .tint(budget.pctUsed >= 100 ? .red : (budget.pctUsed >= 80 ? .orange : .indigo))
        }
        .padding(.vertical, 4)
    }
}

private struct GoalRow: View {
    let goal: GoalDTO
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Circle().fill(Money.colorFromHex(goal.color)).frame(width: 10, height: 10)
                Text(goal.name).bold()
                Spacer()
                Text("\(Int(goal.pctComplete))%")
                    .font(.caption).foregroundStyle(.secondary)
            }
            ProgressView(value: min(goal.pctComplete, 100) / 100).tint(.indigo)
            Text("\(Money.format(goal.currentAmount, currency: goal.currency)) / \(Money.format(goal.targetAmount, currency: goal.currency))")
                .font(.caption).foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
    }
}

private struct AddBudgetSheet: View {
    let categories: [CategoryDTO]
    var onSubmit: (CategoryDTO, Decimal) -> Void
    @State private var selected: CategoryDTO?
    @State private var amountText: String = ""
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Picker("Kategoria", selection: $selected) {
                    Text("Wybierz…").tag(CategoryDTO?.none)
                    ForEach(categories) { c in Text(c.name).tag(CategoryDTO?.some(c)) }
                }
                TextField("Kwota (PLN)", text: $amountText)
                    .keyboardType(.decimalPad)
            }
            .navigationTitle("Nowy budżet")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) { Button("Anuluj") { dismiss() } }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Zapisz") {
                        if let cat = selected,
                           let amount = Decimal(string: amountText.replacingOccurrences(of: ",", with: ".")) {
                            onSubmit(cat, amount)
                        }
                    }.disabled(selected == nil || amountText.isEmpty)
                }
            }
        }
    }
}

private struct AddGoalSheet: View {
    var onSubmit: (String, Decimal, Date?) -> Void
    @State private var name = ""
    @State private var amountText = ""
    @State private var hasDate = false
    @State private var date = Date().addingTimeInterval(60 * 60 * 24 * 365)
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                TextField("Nazwa celu", text: $name)
                TextField("Kwota docelowa (PLN)", text: $amountText).keyboardType(.decimalPad)
                Toggle("Mam datę docelową", isOn: $hasDate)
                if hasDate {
                    DatePicker("Data", selection: $date, displayedComponents: .date)
                }
            }
            .navigationTitle("Nowy cel")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) { Button("Anuluj") { dismiss() } }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Zapisz") {
                        if let amount = Decimal(string: amountText.replacingOccurrences(of: ",", with: ".")) {
                            onSubmit(name, amount, hasDate ? date : nil)
                        }
                    }.disabled(name.isEmpty || amountText.isEmpty)
                }
            }
        }
    }
}
