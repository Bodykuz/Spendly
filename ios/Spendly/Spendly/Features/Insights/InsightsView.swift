import SwiftUI

struct InsightsView: View {
    @StateObject private var vm = InsightsViewModel(api: AppEnvironment.shared.api)

    var body: some View {
        NavigationStack {
            Group {
                if vm.insights.isEmpty && !vm.isLoading {
                    ContentUnavailableView(
                        "Jeszcze zbieramy dane",
                        systemImage: "sparkles",
                        description: Text("Po połączeniu kont i kilku dniach użytkowania zobaczysz tu subskrypcje, cykliczne płatności i nietypowe wydatki.")
                    )
                } else {
                    ScrollView {
                        VStack(spacing: 12) {
                            ForEach(vm.insights) { ins in
                                InsightCard(insight: ins)
                            }
                        }.padding()
                    }
                }
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Insights")
            .refreshable { await vm.load() }
            .task { await vm.load() }
        }
    }
}

private struct InsightCard: View {
    let insight: InsightDTO

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Circle()
                .fill(tint.opacity(0.18))
                .frame(width: 40, height: 40)
                .overlay(Image(systemName: icon).foregroundStyle(tint))
            VStack(alignment: .leading, spacing: 4) {
                Text(insight.title).font(.headline)
                Text(insight.body).font(.subheadline).foregroundStyle(.secondary)
                if let amt = insight.amount, let cur = insight.currency {
                    Text(Money.format(amt, currency: cur))
                        .font(.subheadline.bold())
                        .padding(.top, 2)
                }
            }
            Spacer()
        }
        .padding()
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 14))
    }

    private var tint: Color {
        switch insight.severity {
        case "warning": return .orange
        case "positive": return .green
        default: return .indigo
        }
    }
    private var icon: String {
        switch insight.kind {
        case "subscription": return "repeat.circle.fill"
        case "recurring":    return "calendar.badge.clock"
        case "salary":       return "briefcase.fill"
        case "unusual_expense": return "exclamationmark.triangle.fill"
        case "budget_warning": return "target"
        case "savings_tip":  return "lightbulb.fill"
        default: return "sparkles"
        }
    }
}
