import SwiftUI

struct TransactionDetailView: View {
    let tx: TransactionDTO
    @ObservedObject var vm: TransactionsViewModel
    @State private var pickingCategory = false

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 6) {
                    Text(tx.counterpartyName ?? tx.description ?? "Transakcja").font(.headline)
                    Text(Money.format(tx.amount, currency: tx.currency))
                        .font(.system(size: 34, weight: .bold, design: .rounded))
                        .foregroundStyle(tx.amount >= 0 ? .green : .primary)
                    Text(tx.bookingDate.formatted(date: .long, time: .omitted))
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            Section("Kategoria") {
                Button {
                    pickingCategory = true
                } label: {
                    HStack {
                        Text(tx.category?.name ?? "Bez kategorii")
                        Spacer()
                        Image(systemName: "chevron.right").foregroundStyle(.tertiary)
                    }
                }
            }

            if let desc = tx.description, !desc.isEmpty {
                Section("Opis") { Text(desc) }
            }
            Section("Szczegóły") {
                Row(title: "Status", value: tx.status == .booked ? "Zaksięgowana" : "Oczekująca")
                if let vd = tx.valueDate {
                    Row(title: "Data waluty", value: vd.formatted(date: .abbreviated, time: .omitted))
                }
                if tx.isSubscription { Row(title: "Subskrypcja", value: "tak") }
                if tx.isRecurring { Row(title: "Płatność cykliczna", value: "tak") }
                if tx.isSalary { Row(title: "Wynagrodzenie", value: "tak") }
            }
        }
        .navigationTitle("Transakcja")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $pickingCategory) {
            CategoryPicker(categories: vm.categories, selected: tx.category) { cat in
                Task { await vm.recategorize(tx, to: cat) }
                pickingCategory = false
            }
        }
    }
}

private struct Row: View {
    let title: String; let value: String
    var body: some View {
        HStack { Text(title); Spacer(); Text(value).foregroundStyle(.secondary) }
    }
}

struct CategoryPicker: View {
    let categories: [CategoryDTO]
    let selected: CategoryDTO?
    var onPick: (CategoryDTO?) -> Void

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Button("Bez kategorii") { onPick(nil) }
                }
                Section("Wydatki") {
                    ForEach(categories.filter { !$0.isIncome }) { cat in
                        Button { onPick(cat) } label: {
                            HStack {
                                Circle().fill(Money.colorFromHex(cat.color)).frame(width: 10, height: 10)
                                Text(cat.name)
                                if selected?.id == cat.id {
                                    Spacer(); Image(systemName: "checkmark").foregroundStyle(.indigo)
                                }
                            }
                        }
                    }
                }
                Section("Przychody") {
                    ForEach(categories.filter { $0.isIncome }) { cat in
                        Button { onPick(cat) } label: {
                            HStack {
                                Circle().fill(Money.colorFromHex(cat.color)).frame(width: 10, height: 10)
                                Text(cat.name)
                                if selected?.id == cat.id {
                                    Spacer(); Image(systemName: "checkmark").foregroundStyle(.indigo)
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("Wybierz kategorię")
        }
    }
}
