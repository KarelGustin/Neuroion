//
//  LocationService.swift
//  NeuroionApp
//
//  Location event tracking service
//

import Foundation
import CoreLocation
import Combine

class LocationService: NSObject, ObservableObject {
    @Published var isEnabled = false
    
    private let locationManager = CLLocationManager()
    private let apiClient = APIClient.shared
    private var token: String?
    private var deviceId: String?
    
    private var homeLocation: CLLocation?
    private var isAtHome = false
    
    override init() {
        super.init()
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyHundredMeters
        locationManager.allowsBackgroundLocationUpdates = true
    }
    
    func configure(token: String, deviceId: String) {
        self.token = token
        self.deviceId = deviceId
    }
    
    func startMonitoring() {
        guard isEnabled else { return }
        
        locationManager.requestWhenInUseAuthorization()
        locationManager.startMonitoringSignificantLocationChanges()
    }
    
    func stopMonitoring() {
        locationManager.stopMonitoringSignificantLocationChanges()
    }
    
    private func checkLocation(_ location: CLLocation) {
        // Simple home detection - in production, use geofencing
        if let home = homeLocation {
            let distance = location.distance(from: home)
            let threshold: CLLocationDistance = 100 // meters
            
            if distance < threshold && !isAtHome {
                isAtHome = true
                sendEvent(eventType: "arriving_home", location: location)
            } else if distance >= threshold && isAtHome {
                isAtHome = false
                sendEvent(eventType: "leaving_home", location: location)
            }
        } else {
            // First location - set as home
            homeLocation = location
            isAtHome = true
        }
    }
    
    private func sendEvent(eventType: String, location: CLLocation) {
        guard let token = token else { return }
        
        Task {
            do {
                let event = LocationEvent(
                    eventType: eventType,
                    timestamp: Date(),
                    metadata: [
                        "latitude": AnyCodable(location.coordinate.latitude),
                        "longitude": AnyCodable(location.coordinate.longitude),
                    ]
                )
                
                let request = EventRequest(
                    eventType: "location",
                    location: event,
                    healthSummary: nil
                )
                
                _ = try await apiClient.request(
                    endpoint: "/events",
                    method: "POST",
                    body: request,
                    token: token
                ) as EventResponse
            } catch {
                print("Error sending location event: \(error)")
            }
        }
    }
}

extension LocationService: CLLocationManagerDelegate {
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        if let location = locations.last {
            checkLocation(location)
        }
    }
    
    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        print("Location error: \(error)")
    }
}
