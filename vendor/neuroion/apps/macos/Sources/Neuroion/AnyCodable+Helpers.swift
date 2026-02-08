import NeuroionKit
import NeuroionProtocol
import Foundation

// Prefer the NeuroionKit wrapper to keep gateway request payloads consistent.
typealias AnyCodable = NeuroionKit.AnyCodable
typealias InstanceIdentity = NeuroionKit.InstanceIdentity

extension AnyCodable {
    var stringValue: String? { self.value as? String }
    var boolValue: Bool? { self.value as? Bool }
    var intValue: Int? { self.value as? Int }
    var doubleValue: Double? { self.value as? Double }
    var dictionaryValue: [String: AnyCodable]? { self.value as? [String: AnyCodable] }
    var arrayValue: [AnyCodable]? { self.value as? [AnyCodable] }

    var foundationValue: Any {
        switch self.value {
        case let dict as [String: AnyCodable]:
            dict.mapValues { $0.foundationValue }
        case let array as [AnyCodable]:
            array.map(\.foundationValue)
        default:
            self.value
        }
    }
}

extension NeuroionProtocol.AnyCodable {
    var stringValue: String? { self.value as? String }
    var boolValue: Bool? { self.value as? Bool }
    var intValue: Int? { self.value as? Int }
    var doubleValue: Double? { self.value as? Double }
    var dictionaryValue: [String: NeuroionProtocol.AnyCodable]? { self.value as? [String: NeuroionProtocol.AnyCodable] }
    var arrayValue: [NeuroionProtocol.AnyCodable]? { self.value as? [NeuroionProtocol.AnyCodable] }

    var foundationValue: Any {
        switch self.value {
        case let dict as [String: NeuroionProtocol.AnyCodable]:
            dict.mapValues { $0.foundationValue }
        case let array as [NeuroionProtocol.AnyCodable]:
            array.map(\.foundationValue)
        default:
            self.value
        }
    }
}
