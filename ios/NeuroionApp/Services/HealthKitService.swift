//
//  HealthKitService.swift
//  NeuroionApp
//
//  HealthKit integration for health summaries (with explicit consent)
//

import Combine
import Foundation
import HealthKit

class HealthKitService: ObservableObject {
    @Published var isEnabled = false
    
    private let healthStore = HKHealthStore()
    private let apiClient = APIClient.shared
    private var token: String?
    
    private let readTypes: Set<HKObjectType> = [
        HKObjectType.categoryType(forIdentifier: .sleepAnalysis)!,
        HKObjectType.quantityType(forIdentifier: .activeEnergyBurned)!,
        HKObjectType.quantityType(forIdentifier: .heartRate)!,
    ]
    
    func configure(token: String) {
        self.token = token
    }
    
    func requestAuthorization() async throws {
        guard HKHealthStore.isHealthDataAvailable() else {
            throw HealthKitError.notAvailable
        }
        
        try await healthStore.requestAuthorization(toShare: Set<HKSampleType>(), read: readTypes)
    }
    
    func startMonitoring() {
        guard isEnabled else { return }
        
        // Monitor sleep data
        let sleepType = HKObjectType.categoryType(forIdentifier: .sleepAnalysis)!
        let sleepQuery = HKObserverQuery(sampleType: sleepType, predicate: nil) { [weak self] query, completionHandler, error in
            if error == nil {
                self?.fetchHealthSummary()
            }
            completionHandler()
        }
        
        healthStore.execute(sleepQuery)
    }
    
    private func fetchHealthSummary() {
        Task {
            do {
                let summary = try await calculateHealthSummary()
                try await sendHealthSummary(summary)
            } catch {
                print("Error fetching health summary: \(error)")
            }
        }
    }
    
    private func calculateHealthSummary() async throws -> HealthSummary {
        // Calculate derived summaries from HealthKit data
        // Never send raw data, only summaries
        
        let sleepScore = try await calculateSleepScore()
        let recoveryLevel = try await calculateRecoveryLevel()
        let activityLevel = try await calculateActivityLevel()
        
        return HealthSummary(
            sleepScore: sleepScore,
            recoveryLevel: recoveryLevel,
            activityLevel: activityLevel,
            summary: "Sleep: \(sleepScore)/100, Recovery: \(recoveryLevel), Activity: \(activityLevel)"
        )
    }
    
    private func calculateSleepScore() async throws -> Double {
        // Simplified - in production, use actual HealthKit queries
        return 85.0
    }
    
    private func calculateRecoveryLevel() async throws -> String {
        // Simplified - in production, use actual HealthKit queries
        return "high"
    }
    
    private func calculateActivityLevel() async throws -> String {
        // Simplified - in production, use actual HealthKit queries
        return "medium"
    }
    
    private func sendHealthSummary(_ summary: HealthSummary) async throws {
        guard let token = token else { return }
        
        let event = HealthSummaryEvent(
            sleepScore: summary.sleepScore,
            recoveryLevel: summary.recoveryLevel,
            activityLevel: summary.activityLevel,
            summary: summary.summary,
            timestamp: Date(),
            metadata: nil
        )
        
        let request = EventRequest(
            eventType: "health_summary",
            location: nil,
            healthSummary: event
        )
        
        _ = try await apiClient.request(
            endpoint: "/events",
            method: "POST",
            body: request,
            token: token
        ) as EventResponse
    }
}

enum HealthKitError: LocalizedError {
    case notAvailable
    
    var errorDescription: String? {
        switch self {
        case .notAvailable:
            return "HealthKit is not available on this device"
        }
    }
}

struct HealthSummary {
    let sleepScore: Double
    let recoveryLevel: String
    let activityLevel: String
    let summary: String
}
