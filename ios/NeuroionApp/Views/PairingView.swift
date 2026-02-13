//
//  PairingView.swift
//  NeuroionApp
//
//  When not connected: single "Scan QR code" button. Opens camera; scanning a Neuroion pairing QR connects the app.
//

import AVFoundation
import SwiftUI
import UIKit

// MARK: - Pairing payload from QR (neuroion://pair?base=...&code=...)

struct NeuroionPairQRPayload {
    let baseURL: String
    let pairingCode: String
}

enum NeuroionPairQRParser {
    static func parse(_ string: String) -> NeuroionPairQRPayload? {
        guard let url = URL(string: string) else { return nil }
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let query = components.queryItems else { return nil }
        let base = query.first(where: { $0.name == "base" })?.value
        let code = query.first(where: { $0.name == "code" })?.value
        guard let baseURL = base?.removingPercentEncoding, !baseURL.isEmpty,
              let pairingCode = code?.trimmingCharacters(in: .whitespacesAndNewlines), !pairingCode.isEmpty else {
            return nil
        }
        let normalizedBase = baseURL.hasSuffix("/") ? String(baseURL.dropLast()) : baseURL
        return NeuroionPairQRPayload(baseURL: normalizedBase, pairingCode: pairingCode)
    }
}

// MARK: - PairingView

struct PairingView: View {
    @EnvironmentObject var authManager: AuthManager
    @ObservedObject private var connectionManager = ConnectionManager.shared
    @State private var showScanner = false
    @State private var isPairing = false
    @State private var errorMessage: String?

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                Image(systemName: "house.fill")
                    .font(.system(size: 60))
                    .foregroundColor(.blue)

                Text("Neuroion")
                    .font(.largeTitle)
                    .fontWeight(.bold)

                Text("Connect to your Homebase")
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                Button(action: { showScanner = true }) {
                    Label("Scan QR code", systemImage: "qrcode.viewfinder")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding()
                }
                .buttonStyle(.borderedProminent)
                .padding(.horizontal, 24)
                .disabled(isPairing)

                if isPairing {
                    ProgressView("Koppelen…")
                        .padding(.top, 8)
                }

                if let error = errorMessage {
                    Text(error)
                        .font(.caption)
                        .foregroundColor(.red)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 24)
                }

                Text("Scan de QR-code die op het Setup-scherm van Neuroion wordt getoond.")
                    .font(.caption2)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)

                Spacer(minLength: 40)
            }
            .padding(.vertical, 32)
        }
        .sheet(isPresented: $showScanner) {
            QRScannerView(
                onScan: handleScannedPayload,
                onCancel: { showScanner = false }
            )
        }
    }

    private func handleScannedPayload(_ payload: NeuroionPairQRPayload) {
        showScanner = false
        errorMessage = nil
        isPairing = true

        connectionManager.baseURL = payload.baseURL

        Task {
            do {
                let deviceId = UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString
                try await authManager.pair(deviceId: deviceId, pairingCode: payload.pairingCode)
                await MainActor.run { isPairing = false }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    isPairing = false
                }
            }
        }
    }
}

// MARK: - QR scanner (camera)

struct QRScannerView: View {
    @Environment(\.dismiss) private var dismiss
    let onScan: (NeuroionPairQRPayload) -> Void
    let onCancel: () -> Void

    var body: some View {
        PairingQRScannerViewControllerRepresentable(
            onScan: { payload in
                onScan(payload)
                dismiss()
            },
            onCancel: {
                onCancel()
                dismiss()
            }
        )
        .ignoresSafeArea()
    }
}

private struct PairingQRScannerViewControllerRepresentable: UIViewControllerRepresentable {
    let onScan: (NeuroionPairQRPayload) -> Void
    let onCancel: () -> Void

    func makeUIViewController(context: Context) -> PairingQRScannerViewController {
        PairingQRScannerViewController(onScan: onScan, onCancel: onCancel)
    }

    func updateUIViewController(_ uiViewController: PairingQRScannerViewController, context: Context) {}
}

private final class PairingQRScannerViewController: UIViewController {
    private let onScan: (NeuroionPairQRPayload) -> Void
    private let onCancel: () -> Void
    private var captureSession: AVCaptureSession?
    private var previewLayer: AVCaptureVideoPreviewLayer?
    private var hasHandledResult = false
    private let sessionQueue = DispatchQueue(label: "neuroion.qrscanner.session")
    private var cameraUnavailableLabel: UILabel?

    init(onScan: @escaping (NeuroionPairQRPayload) -> Void, onCancel: @escaping () -> Void) {
        self.onScan = onScan
        self.onCancel = onCancel
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    private static let scanFrameSize: CGFloat = 260

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black

        let cancelButton = UIButton(type: .system)
        cancelButton.setTitle("Annuleren", for: .normal)
        cancelButton.setTitleColor(.white, for: .normal)
        cancelButton.addTarget(self, action: #selector(cancelTapped), for: .touchUpInside)
        cancelButton.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(cancelButton)
        NSLayoutConstraint.activate([
            cancelButton.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 16),
            cancelButton.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 16),
        ])

        let label = UILabel()
        label.text = "Scan de Neuroion QR-code"
        label.textColor = .white
        label.font = .preferredFont(forTextStyle: .headline)
        label.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(label)
        NSLayoutConstraint.activate([
            label.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            label.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -24),
        ])

        let unavailableLabel = UILabel()
        unavailableLabel.text = "Camera niet beschikbaar"
        unavailableLabel.textColor = .white
        unavailableLabel.font = .preferredFont(forTextStyle: .body)
        unavailableLabel.textAlignment = .center
        unavailableLabel.numberOfLines = 0
        unavailableLabel.translatesAutoresizingMaskIntoConstraints = false
        unavailableLabel.isHidden = true
        view.addSubview(unavailableLabel)
        NSLayoutConstraint.activate([
            unavailableLabel.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            unavailableLabel.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            unavailableLabel.leadingAnchor.constraint(greaterThanOrEqualTo: view.leadingAnchor, constant: 24),
            unavailableLabel.trailingAnchor.constraint(lessThanOrEqualTo: view.trailingAnchor, constant: -24),
        ])
        cameraUnavailableLabel = unavailableLabel

        let outlineView = UIView()
        outlineView.backgroundColor = .clear
        outlineView.layer.borderColor = UIColor.white.cgColor
        outlineView.layer.borderWidth = 2.5
        outlineView.layer.cornerRadius = 14
        outlineView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(outlineView)
        NSLayoutConstraint.activate([
            outlineView.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            outlineView.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            outlineView.widthAnchor.constraint(equalToConstant: Self.scanFrameSize),
            outlineView.heightAnchor.constraint(equalToConstant: Self.scanFrameSize),
        ])
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        requestCameraPermissionThenSetup()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        sessionQueue.async { [weak self] in
            self?.captureSession?.stopRunning()
        }
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        previewLayer?.frame = view.bounds
    }

    @objc private func cancelTapped() {
        onCancel()
    }

    private func showCameraUnavailable() {
        DispatchQueue.main.async { [weak self] in
            self?.cameraUnavailableLabel?.isHidden = false
        }
    }

    /// Call on main thread. Asks for camera permission (shows system dialog if needed), then sets up session.
    private func requestCameraPermissionThenSetup() {
        let status = AVCaptureDevice.authorizationStatus(for: .video)
        switch status {
        case .authorized:
            sessionQueue.async { [weak self] in
                self?.setupAndStartSession()
            }
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                DispatchQueue.main.async {
                    if granted {
                        self?.sessionQueue.async {
                            self?.setupAndStartSession()
                        }
                    } else {
                        self?.showCameraUnavailable()
                    }
                }
            }
        case .denied, .restricted:
            showCameraUnavailable()
        @unknown default:
            showCameraUnavailable()
        }
    }

    /// Run on sessionQueue. Creates session, then adds preview layer on main, then starts session.
    private func setupAndStartSession() {
        let session = AVCaptureSession()
        session.sessionPreset = .high

        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else {
            showCameraUnavailable()
            return
        }
        guard let input = try? AVCaptureDeviceInput(device: device), session.canAddInput(input) else {
            showCameraUnavailable()
            return
        }
        session.addInput(input)

        let output = AVCaptureMetadataOutput()
        guard session.canAddOutput(output) else {
            showCameraUnavailable()
            return
        }
        session.addOutput(output)
        output.metadataObjectTypes = [.qr]
        output.setMetadataObjectsDelegate(self, queue: DispatchQueue.main)

        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            let layer = AVCaptureVideoPreviewLayer(session: session)
            layer.videoGravity = .resizeAspectFill
            layer.frame = self.view.bounds
            self.view.layer.insertSublayer(layer, at: 0)
            self.previewLayer = layer
            self.captureSession = session
            self.sessionQueue.async {
                session.startRunning()
            }
        }
    }
}

extension PairingQRScannerViewController: AVCaptureMetadataOutputObjectsDelegate {
    func metadataOutput(_ output: AVCaptureMetadataOutput, didOutput metadataObjects: [AVMetadataObject], from connection: AVCaptureConnection) {
        guard !hasHandledResult,
              let obj = metadataObjects.first as? AVMetadataMachineReadableCodeObject,
              let string = obj.stringValue,
              let payload = NeuroionPairQRParser.parse(string) else { return }
        hasHandledResult = true
        captureSession?.stopRunning()
        onScan(payload)
    }
}
