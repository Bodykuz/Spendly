import Charts
import SwiftUI

struct DashboardView: View {
    @EnvironmentObject var env: AppEnvironment
    @StateObject private var vm = DashboardViewModel(api: AppEnvironment.shared.api)

    @State private var showBanks = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    if let d = vm.dashboard {
                        balanceHero(d)
                        statsRow(d)
                        cashflowChart(d)
                        topCategories(d)
                        manageBanksCTA
                    } else if vm.isLoading {
                        ProgressView().padding(.top, 80)
                    } else {
                        EmptyStateHero {
                            showBanks = true
                        }
                    }
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Pulpit")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { showBanks = true } label: {
                        Image(systemName: "building.columns")
                    }
                }
            }
            .refreshable { await vm.load() }
            .task { await vm.load() }
            .sheet(isPresented: $showBanks) {
                NavigationStack { BanksView() }.environmentObject(env)
            }
            .onChange(of: env.pendingBankCallback) { _, _ in
                Task { await vm.load() }
            }
        }
    }

    // MARK: - Pieces

    private func balanceHero(_ d: DashboardDTO) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Łączne saldo").font(.subheadline).foregroundStyle(.secondary)
            Text(Money.format(d.totalBalance, currency: d.currency))
                .font(.system(size: 40, weight: .bold, design: .rounded))
            HStack(spacing: 12) {
                Label("\(d.linkedBanks) banków", systemImage: "building.columns.fill")
                Label("\(d.accounts) kont", systemImage: "creditcard.fill")
            }
            .font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(20)
        .background(
            LinearGradient(colors: [.indigo, .purple], startPoint: .topLeading, endPoint: .bottomTrailing)
                .opacity(0.9),
            in: RoundedRectangle(cornerRadius: 20)
        )
        .foregroundStyle(.white)
    }

    private func statsRow(_ d: DashboardDTO) -> some View {
        HStack(spacing: 12) {
            StatCard(title: "Przychody",
                     value: Money.format(d.monthIncome, currency: d.currency),
                     icon: "arrow.down.circle.fill",
                     tint: .green)
            StatCard(title: "Wydatki",
                     value: Money.format(d.monthExpense, currency: d.currency),
                     icon: "arrow.up.circle.fill",
                     tint: .red)
            StatCard(title: "Netto",
                     value: Money.format(d.monthNet, currency: d.currency),
                     icon: d.monthNet >= 0 ? "plusminus.circle.fill" : "exclamationmark.triangle.fill",
                     tint: d.monthNet >= 0 ? .indigo : .orange)
        }
    }

    private func cashflowChart(_ d: DashboardDTO) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Cashflow — 6 miesięcy").font(.headline)
            Chart {
                ForEach(d.cashflow) { m in
                    BarMark(
                        x: .value("Miesiąc", Money.shortMonth(m.month)),
                        y: .value("Przychód", NSDecimalNumber(decimal: m.income).doubleValue)
                    )
                    .foregroundStyle(.green.gradient)
                    BarMark(
                        x: .value("Miesiąc", Money.shortMonth(m.month)),
                        y: .value("Wydatek", -NSDecimalNumber(decimal: m.expense).doubleValue)
                    )
                    .foregroundStyle(.red.gradient)
                }
            }
            .frame(height: 200)
        }
        .padding()
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 16))
    }

    private func topCategories(_ d: DashboardDTO) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Największe kategorie (ten miesiąc)").font(.headline)
            if d.topCategories.isEmpty {
                Text("Brak wydatków w tym miesiącu.").foregroundStyle(.secondary)
            } else {
                ForEach(d.topCategories) { c in
                    HStack {
                        Circle().fill(Money.colorFromHex(c.color)).frame(width: 10, height: 10)
                        Text(c.categoryName)
                        Spacer()
                        Text(Money.format(c.amount, currency: d.currency)).bold()
                    }
                }
            }
        }
        .padding()
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 16))
    }

    private var manageBanksCTA: some View {
        Button { showBanks = true } label: {
            Label("Zarządzaj bankami", systemImage: "building.columns")
                .frame(maxWidth: .infinity)
                .padding()
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14))
        }
    }
}

private struct StatCard: View {
    let title: String
    let value: String
    let icon: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Image(systemName: icon).foregroundStyle(tint).font(.title3)
            Text(title).font(.caption).foregroundStyle(.secondary)
            Text(value).font(.headline).lineLimit(1).minimumScaleFactor(0.6)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 14))
    }
}

private struct EmptyStateHero: View {
    var action: () -> Void
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "building.columns.circle.fill")
                .font(.system(size: 60))
                .foregroundStyle(.indigo)
            Text("Połącz swój pierwszy bank").font(.title3.bold())
            Text("Spendly połączy się z Twoimi kontami przez bezpieczne PSD2 i zbierze wszystkie transakcje w jednym miejscu.")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
            Button("Dodaj bank", action: action)
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
        }
        .padding()
        .padding(.top, 80)
    }
}
