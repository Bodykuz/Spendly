import SwiftUI

struct RootView: View {
    @EnvironmentObject var session: SessionStore

    var body: some View {
        Group {
            if session.isAuthenticated {
                MainTabView()
            } else {
                AuthFlowView()
            }
        }
        .animation(.easeInOut(duration: 0.25), value: session.isAuthenticated)
    }
}

struct MainTabView: View {
    var body: some View {
        TabView {
            DashboardView()
                .tabItem { Label("Pulpit", systemImage: "chart.pie.fill") }

            TransactionsView()
                .tabItem { Label("Transakcje", systemImage: "list.bullet.rectangle") }

            InsightsView()
                .tabItem { Label("Insights", systemImage: "sparkles") }

            BudgetsView()
                .tabItem { Label("Budżety", systemImage: "target") }

            SettingsView()
                .tabItem { Label("Konto", systemImage: "person.crop.circle") }
        }
    }
}
