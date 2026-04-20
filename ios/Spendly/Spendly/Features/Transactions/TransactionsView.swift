import SwiftUI

struct TransactionsView: View {
    @StateObject private var vm = TransactionsViewModel(api: AppEnvironment.shared.api)

    var body: some View {
        NavigationStack {
            List {
                Section {
                    filterBar
                }
                ForEach(groupedKeys, id: \.self) { date in
                    Section(date) {
                        ForEach(grouped[date] ?? []) { tx in
                            NavigationLink(value: tx) {
                                TransactionRow(tx: tx)
                            }
                        }
                    }
                }
                if vm.hasMore {
                    HStack { Spacer(); ProgressView(); Spacer() }
                        .onAppear { Task { await vm.loadMore() } }
                }
            }
            .navigationTitle("Transakcje")
            .navigationDestination(for: TransactionDTO.self) { tx in
                TransactionDetailView(tx: tx, vm: vm)
            }
            .searchable(text: $vm.search, prompt: "Szukaj…")
            .onChange(of: vm.search) { _, _ in vm.debouncedSearch() }
            .refreshable { await vm.loadFirst() }
            .task {
                await vm.loadCategories()
                await vm.loadFirst()
            }
        }
    }

    private var filterBar: some View {
        HStack {
            Picker("", selection: Binding(
                get: {
                    if vm.onlyExpenses { return "expenses" }
                    if vm.onlyIncome { return "income" }
                    return "all"
                },
                set: { newVal in
                    vm.onlyExpenses = (newVal == "expenses")
                    vm.onlyIncome = (newVal == "income")
                    Task { await vm.loadFirst() }
                }
            )) {
                Text("Wszystko").tag("all")
                Text("Wydatki").tag("expenses")
                Text("Przychody").tag("income")
            }
            .pickerStyle(.segmented)
        }
        .listRowBackground(Color.clear)
    }

    private var grouped: [String: [TransactionDTO]] {
        let df = DateFormatter()
        df.locale = Locale(identifier: "pl_PL")
        df.dateFormat = "EEEE, d MMMM"
        return Dictionary(grouping: vm.transactions) { df.string(from: $0.bookingDate).capitalized }
    }

    private var groupedKeys: [String] {
        let df = DateFormatter()
        df.locale = Locale(identifier: "pl_PL")
        df.dateFormat = "EEEE, d MMMM"
        return grouped.keys.sorted { lhs, rhs in
            let a = grouped[lhs]?.first?.bookingDate ?? .distantPast
            let b = grouped[rhs]?.first?.bookingDate ?? .distantPast
            return a > b
        }
    }
}

struct TransactionRow: View {
    let tx: TransactionDTO
    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(Money.colorFromHex(tx.category?.color ?? "#6B7280").opacity(0.18))
                .frame(width: 36, height: 36)
                .overlay(
                    Image(systemName: Self.systemIcon(for: tx.category?.icon ?? "tag"))
                        .foregroundStyle(Money.colorFromHex(tx.category?.color ?? "#6B7280"))
                )
            VStack(alignment: .leading, spacing: 2) {
                Text(tx.counterpartyName ?? tx.description ?? "Transakcja")
                    .lineLimit(1)
                HStack(spacing: 6) {
                    Text(tx.category?.name ?? "Bez kategorii")
                        .font(.caption).foregroundStyle(.secondary)
                    if tx.isSubscription {
                        Image(systemName: "repeat.circle.fill").foregroundStyle(.pink)
                            .font(.caption2)
                    }
                    if tx.isSalary {
                        Image(systemName: "briefcase.fill").foregroundStyle(.green)
                            .font(.caption2)
                    }
                }
            }
            Spacer()
            Text(Money.format(tx.amount, currency: tx.currency))
                .bold()
                .foregroundStyle(tx.amount >= 0 ? .green : .primary)
        }
        .contentShape(Rectangle())
    }

    static func systemIcon(for slug: String) -> String {
        switch slug {
        case "shopping-cart": return "cart.fill"
        case "utensils": return "fork.knife"
        case "car": return "car.fill"
        case "fuel": return "fuelpump.fill"
        case "home": return "house.fill"
        case "bolt": return "bolt.fill"
        case "repeat": return "repeat"
        case "music": return "music.note"
        case "bag": return "bag.fill"
        case "heart": return "heart.fill"
        case "plane": return "airplane"
        case "cash": return "banknote.fill"
        case "receipt": return "doc.text.fill"
        case "landmark": return "building.columns.fill"
        case "briefcase": return "briefcase.fill"
        case "arrow-down-circle": return "arrow.down.circle.fill"
        case "swap": return "arrow.left.arrow.right"
        case "target": return "target"
        default: return "tag"
        }
    }
}
