//
//  AgendaStore.swift
//  NeuroionApp
//
//  Local agenda cache: persisted to UserDefaults, synced to server on WebSocket connect.
//  Updated when we receive agenda_update from WebSocket (agent modified agenda).
//

import Foundation
import SwiftUI

private let agendaStorageKey = "neuroion_agenda_events"

/// Local agenda event for storage (same shape as server).
struct LocalAgendaEvent: Codable, Identifiable, Equatable {
    var id: Int
    var title: String
    var startAt: Date
    var endAt: Date
    var allDay: Bool
    var notes: String?
    var createdAt: Date
    var updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id, title, allDay, notes
        case startAt = "start_at"
        case endAt = "end_at"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }

    init(id: Int, title: String, startAt: Date, endAt: Date, allDay: Bool, notes: String?, createdAt: Date, updatedAt: Date) {
        self.id = id
        self.title = title
        self.startAt = startAt
        self.endAt = endAt
        self.allDay = allDay
        self.notes = notes
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(Int.self, forKey: .id)
        title = try c.decode(String.self, forKey: .title)
        allDay = try c.decodeIfPresent(Bool.self, forKey: .allDay) ?? false
        notes = try c.decodeIfPresent(String.self, forKey: .notes)
        let startStr = try c.decode(String.self, forKey: .startAt)
        let endStr = try c.decode(String.self, forKey: .endAt)
        startAt = Self.parseDate(startStr) ?? Date()
        endAt = Self.parseDate(endStr) ?? Date()
        createdAt = try c.decodeIfPresent(Date.self, forKey: .createdAt) ?? startAt
        updatedAt = try c.decodeIfPresent(Date.self, forKey: .updatedAt) ?? endAt
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(id, forKey: .id)
        try c.encode(title, forKey: .title)
        try c.encode(startAt, forKey: .startAt)
        try c.encode(endAt, forKey: .endAt)
        try c.encode(allDay, forKey: .allDay)
        try c.encodeIfPresent(notes, forKey: .notes)
        try c.encode(createdAt, forKey: .createdAt)
        try c.encode(updatedAt, forKey: .updatedAt)
    }

    init?(from dict: [String: Any]) {
        guard let id = dict["id"] as? Int,
              let title = dict["title"] as? String else { return nil }
        let startAtStr = dict["start_at"] as? String ?? ""
        let endAtStr = dict["end_at"] as? String ?? ""
        let allDay = dict["all_day"] as? Bool ?? false
        let notes = dict["notes"] as? String
        guard let startAt = Self.parseDate(startAtStr),
              let endAt = Self.parseDate(endAtStr) else { return nil }
        self.id = id
        self.title = title
        self.startAt = startAt
        self.endAt = endAt
        self.allDay = allDay
        self.notes = notes
        self.createdAt = startAt
        self.updatedAt = endAt
    }

    static func parseDate(_ str: String) -> Date? {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = formatter.date(from: str) { return d }
        formatter.formatOptions = [.withInternetDateTime]
        if let d = formatter.date(from: str) { return d }
        if str.count <= 10, let d = formatter.date(from: str + "T00:00:00Z") { return d }
        return nil
    }

    func toSyncDict() -> [String: Any] {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        f.timeZone = TimeZone(identifier: "UTC")!
        return [
            "id": id,
            "title": title,
            "start_at": f.string(from: startAt),
            "end_at": f.string(from: endAt),
            "all_day": allDay,
            "notes": notes as Any,
        ]
    }
}

final class AgendaStore: ObservableObject {
    static let shared = AgendaStore()

    @Published private(set) var events: [LocalAgendaEvent] = []

    private init() {
        loadFromDisk()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleAgendaUpdate(_:)),
            name: .neuroionAgendaUpdate,
            object: nil
        )
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }

    private static let jsonDecoder: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .custom { decoder in
            let c = try decoder.singleValueContainer()
            let str = try c.decode(String.self)
            let f = ISO8601DateFormatter()
            f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let d = f.date(from: str) { return d }
            f.formatOptions = [.withInternetDateTime]
            return f.date(from: str) ?? Date()
        }
        return d
    }()

    private static let jsonEncoder: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }()

    private func loadFromDisk() {
        guard let data = UserDefaults.standard.data(forKey: agendaStorageKey),
              let decoded = try? Self.jsonDecoder.decode([LocalAgendaEvent].self, from: data) else { return }
        events = decoded
    }

    private func saveToDisk() {
        guard let data = try? Self.jsonEncoder.encode(events) else { return }
        UserDefaults.standard.set(data, forKey: agendaStorageKey)
    }

    /// Merge events from server (e.g. agenda_update from WebSocket).
    func applyUpdate(_ eventsFromServer: [[String: Any]]) {
        var list = events
        for evDict in eventsFromServer {
            guard let local = LocalAgendaEvent(from: evDict) else { continue }
            if let idx = list.firstIndex(where: { $0.id == local.id }) {
                list[idx] = local
            } else {
                list.append(local)
            }
        }
        list.sort { $0.startAt < $1.startAt }
        events = list
        saveToDisk()
    }

    /// Replace with fetched events (e.g. after loading from server in AgendaView).
    func replace(with newEvents: [LocalAgendaEvent]) {
        events = newEvents.sorted { $0.startAt < $1.startAt }
        saveToDisk()
    }

    @objc private func handleAgendaUpdate(_ notification: Notification) {
        guard let userInfo = notification.userInfo,
              let eventsFromServer = userInfo["events"] as? [[String: Any]] else { return }
        DispatchQueue.main.async { [weak self] in
            self?.applyUpdate(eventsFromServer)
        }
    }

    /// Events in the given date range (for display).
    func events(from start: Date, to end: Date) -> [LocalAgendaEvent] {
        events.filter { $0.startAt < end && $0.endAt > start }
    }

    /// Sync local events to server (WebSocket agenda_sync or POST /agenda/sync).
    func syncToServer(token: String) {
        let payload = events.map { $0.toSyncDict() }
        if WebSocketService.shared.isConnected {
            WebSocketService.shared.sendAgendaSync(events: payload)
            return
        }
        Task {
            do {
                let tuples = events.map { e in (title: e.title, startAt: e.startAt, endAt: e.endAt, allDay: e.allDay, notes: e.notes) }
                _ = try await AgendaService.sync(events: tuples, token: token)
            } catch {
                NSLog("[Neuroion] agenda sync failed: %@", error.localizedDescription)
            }
        }
    }
}
