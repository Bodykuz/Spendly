import XCTest
@testable import Spendly

final class MoneyFormattingTests: XCTestCase {
    func testPLNFormatting() {
        let s = Money.format(Decimal(string: "1234.50")!, currency: "PLN")
        XCTAssertTrue(s.contains("1") && s.contains("PLN") || s.contains("zł"))
    }

    func testShortMonth() {
        XCTAssertEqual(Money.shortMonth("2026-01").count > 0, true)
        XCTAssertEqual(Money.shortMonth("bad"), "bad")
    }

    func testColorFromHex() {
        _ = Money.colorFromHex("#6366F1")
        _ = Money.colorFromHex("AABBCC")
    }
}

final class KeychainTests: XCTestCase {
    func testRoundtrip() {
        let kc = KeychainStore(service: "tests.spendly.ios")
        kc.set("abc", for: "test_key")
        XCTAssertEqual(kc.get("test_key"), "abc")
        kc.remove("test_key")
        XCTAssertNil(kc.get("test_key"))
    }
}
