import Foundation
import SwiftUI

enum Money {
    static func format(_ amount: Decimal, currency: String = "PLN") -> String {
        let fmt = NumberFormatter()
        fmt.numberStyle = .currency
        fmt.currencyCode = currency
        fmt.locale = Locale(identifier: "pl_PL")
        return fmt.string(from: amount as NSNumber) ?? "\(amount) \(currency)"
    }

    static func shortMonth(_ yyyymm: String) -> String {
        let parts = yyyymm.split(separator: "-")
        guard parts.count == 2, let month = Int(parts[1]) else { return yyyymm }
        let df = DateFormatter()
        df.locale = Locale(identifier: "pl_PL")
        df.dateFormat = "LLL"
        var comps = DateComponents()
        comps.year = Int(parts[0])
        comps.month = month
        if let d = Calendar(identifier: .gregorian).date(from: comps) {
            return df.string(from: d).capitalized
        }
        return yyyymm
    }

    static func colorFromHex(_ hex: String) -> Color {
        var s = hex.hasPrefix("#") ? String(hex.dropFirst()) : hex
        if s.count == 8 { s = String(s.prefix(6)) }
        guard s.count == 6, let v = UInt64(s, radix: 16) else { return .gray }
        return Color(
            red:   Double((v & 0xFF0000) >> 16) / 255,
            green: Double((v & 0x00FF00) >> 8) / 255,
            blue:  Double(v & 0x0000FF) / 255
        )
    }
}
