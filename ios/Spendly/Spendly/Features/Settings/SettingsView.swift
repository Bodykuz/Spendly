import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var env: AppEnvironment
    @EnvironmentObject var session: SessionStore
    @State private var showingBanks = false

    var body: some View {
        NavigationStack {
            List {
                if let u = session.user {
                    Section {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(u.fullName ?? "—").font(.headline)
                            Text(u.email).foregroundStyle(.secondary)
                        }.padding(.vertical, 4)
                    }
                }

                Section("Dane finansowe") {
                    Button { showingBanks = true } label: {
                        Label("Połączone banki", systemImage: "building.columns.fill")
                    }
                }

                Section("Prywatność") {
                    Link(destination: URL(string: "https://spendly.app/privacy")!) {
                        Label("Polityka prywatności", systemImage: "hand.raised.fill")
                    }
                    Link(destination: URL(string: "https://spendly.app/terms")!) {
                        Label("Regulamin", systemImage: "doc.text.fill")
                    }
                }

                Section {
                    Button(role: .destructive) {
                        session.signOut()
                    } label: {
                        Label("Wyloguj", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                }

                Section {
                    Text("Spendly \(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "0.1.0")")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .center)
                }
            }
            .navigationTitle("Konto")
            .sheet(isPresented: $showingBanks) {
                NavigationStack { BanksView() }
                    .environmentObject(env)
                    .environmentObject(session)
            }
        }
    }
}
