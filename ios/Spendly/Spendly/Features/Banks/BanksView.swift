import SwiftUI

struct BanksView: View {
    @EnvironmentObject var env: AppEnvironment
    @StateObject private var vm = BanksViewModel(api: AppEnvironment.shared.api)
    @State private var showingLink = false

    var body: some View {
        NavigationStack {
            List {
                Section("Połączone banki") {
                    if vm.connections.isEmpty {
                        Text("Nie masz jeszcze połączonych banków.")
                            .foregroundStyle(.secondary)
                    }
                    ForEach(vm.connections) { conn in
                        BankRow(conn: conn) {
                            Task { await vm.remove(connection: conn) }
                        } onReconnect: {
                            Task { await vm.reconnect(connection: conn) }
                        } onSync: {
                            Task { try? await vm.sync(connection: conn) }
                        }
                    }
                }
            }
            .navigationTitle("Banki")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { showingLink = true } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .refreshable { await vm.loadConnections() }
            .task { await vm.loadConnections() }
            .sheet(isPresented: $showingLink) {
                LinkBankView().environmentObject(env)
            }
            .onChange(of: env.pendingBankCallback) { _, _ in
                Task { await vm.loadConnections() }
            }
        }
    }
}

private struct BankRow: View {
    let conn: BankConnectionDTO
    var onRemove: () -> Void
    var onReconnect: () -> Void
    var onSync: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            AsyncImage(url: conn.institutionLogo.flatMap(URL.init(string:))) { img in
                img.resizable().scaledToFit()
            } placeholder: {
                Image(systemName: "building.columns.fill")
                    .foregroundStyle(.indigo)
            }
            .frame(width: 44, height: 44)
            .background(Color(.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 10))

            VStack(alignment: .leading, spacing: 2) {
                Text(conn.institutionName).font(.headline)
                HStack(spacing: 6) {
                    StatusPill(status: conn.status)
                    if let last = conn.lastSyncedAt {
                        Text("Ostatnia synchronizacja: \(last.formatted(.relative(presentation: .named)))")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
            Spacer()
            Menu {
                Button("Synchronizuj", action: onSync)
                if conn.status == .expired || conn.status == .error {
                    Button("Ponów zgodę", action: onReconnect)
                }
                Button("Odłącz bank", role: .destructive, action: onRemove)
            } label: { Image(systemName: "ellipsis.circle") }
        }
        .padding(.vertical, 4)
    }
}

private struct StatusPill: View {
    let status: ConsentStatusDTO
    var body: some View {
        let (label, color): (String, Color) = {
            switch status {
            case .linked:   return ("Aktywne", .green)
            case .pending:  return ("Oczekuje", .orange)
            case .expired:  return ("Wygasłe", .red)
            case .revoked:  return ("Odłączone", .gray)
            case .error:    return ("Błąd", .red)
            }
        }()
        Text(label)
            .font(.caption2.bold())
            .padding(.horizontal, 8).padding(.vertical, 2)
            .background(color.opacity(0.18), in: Capsule())
            .foregroundStyle(color)
    }
}
