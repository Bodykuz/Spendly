import SwiftUI

struct LinkBankView: View {
    @Environment(\.dismiss) private var dismiss
    @StateObject private var vm = BanksViewModel(api: AppEnvironment.shared.api)

    var body: some View {
        NavigationStack {
            Group {
                if vm.institutions.isEmpty {
                    VStack(spacing: 12) {
                        ProgressView()
                        Text("Ładuję listę banków…").foregroundStyle(.secondary)
                    }.frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    List {
                        Section {
                            ForEach(vm.filteredInstitutions) { inst in
                                Button {
                                    Task {
                                        await vm.link(institution: inst)
                                        dismiss()
                                    }
                                } label: {
                                    InstitutionRow(institution: inst)
                                }
                            }
                        } footer: {
                            Text("Wybierając bank, nastąpi przekierowanie do bezpiecznej strony Twojego banku, gdzie udzielisz zgody PSD2 na dostęp do danych tylko-do-odczytu.")
                        }
                    }
                    .searchable(text: $vm.searchText, prompt: "Szukaj banku")
                }
            }
            .navigationTitle("Dodaj bank")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Anuluj") { dismiss() }
                }
            }
            .task { await vm.loadInstitutions() }
        }
    }
}

private struct InstitutionRow: View {
    let institution: InstitutionDTO
    var body: some View {
        HStack(spacing: 12) {
            AsyncImage(url: institution.logo.flatMap(URL.init(string:))) { img in
                img.resizable().scaledToFit()
            } placeholder: {
                Image(systemName: "building.columns.fill").foregroundStyle(.indigo)
            }
            .frame(width: 40, height: 40)
            .background(Color(.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 10))

            VStack(alignment: .leading) {
                Text(institution.name).font(.body)
                if let days = institution.transactionTotalDays {
                    Text("Historia do \(days) dni").font(.caption).foregroundStyle(.secondary)
                }
            }
            Spacer()
            Image(systemName: "chevron.right").foregroundStyle(.tertiary)
        }
        .padding(.vertical, 2)
    }
}
