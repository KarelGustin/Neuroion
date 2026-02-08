import Foundation
import Testing
@testable import Neuroion

@Suite(.serialized)
struct NeuroionConfigFileTests {
    @Test
    func configPathRespectsEnvOverride() async {
        let override = FileManager().temporaryDirectory
            .appendingPathComponent("neuroion-config-\(UUID().uuidString)")
            .appendingPathComponent("neuroion.json")
            .path

        await TestIsolation.withEnvValues(["NEUROION_CONFIG_PATH": override]) {
            #expect(NeuroionConfigFile.url().path == override)
        }
    }

    @MainActor
    @Test
    func remoteGatewayPortParsesAndMatchesHost() async {
        let override = FileManager().temporaryDirectory
            .appendingPathComponent("neuroion-config-\(UUID().uuidString)")
            .appendingPathComponent("neuroion.json")
            .path

        await TestIsolation.withEnvValues(["NEUROION_CONFIG_PATH": override]) {
            NeuroionConfigFile.saveDict([
                "gateway": [
                    "remote": [
                        "url": "ws://gateway.ts.net:19999",
                    ],
                ],
            ])
            #expect(NeuroionConfigFile.remoteGatewayPort() == 19999)
            #expect(NeuroionConfigFile.remoteGatewayPort(matchingHost: "gateway.ts.net") == 19999)
            #expect(NeuroionConfigFile.remoteGatewayPort(matchingHost: "gateway") == 19999)
            #expect(NeuroionConfigFile.remoteGatewayPort(matchingHost: "other.ts.net") == nil)
        }
    }

    @MainActor
    @Test
    func setRemoteGatewayUrlPreservesScheme() async {
        let override = FileManager().temporaryDirectory
            .appendingPathComponent("neuroion-config-\(UUID().uuidString)")
            .appendingPathComponent("neuroion.json")
            .path

        await TestIsolation.withEnvValues(["NEUROION_CONFIG_PATH": override]) {
            NeuroionConfigFile.saveDict([
                "gateway": [
                    "remote": [
                        "url": "wss://old-host:111",
                    ],
                ],
            ])
            NeuroionConfigFile.setRemoteGatewayUrl(host: "new-host", port: 2222)
            let root = NeuroionConfigFile.loadDict()
            let url = ((root["gateway"] as? [String: Any])?["remote"] as? [String: Any])?["url"] as? String
            #expect(url == "wss://new-host:2222")
        }
    }

    @Test
    func stateDirOverrideSetsConfigPath() async {
        let dir = FileManager().temporaryDirectory
            .appendingPathComponent("neuroion-state-\(UUID().uuidString)", isDirectory: true)
            .path

        await TestIsolation.withEnvValues([
            "NEUROION_CONFIG_PATH": nil,
            "NEUROION_STATE_DIR": dir,
        ]) {
            #expect(NeuroionConfigFile.stateDirURL().path == dir)
            #expect(NeuroionConfigFile.url().path == "\(dir)/neuroion.json")
        }
    }
}
