import SwiftUI
import CoreMotion
import Combine
import Network

// -----------------------------------------
// 軽量なOSC(UDP)送信クライアント
// -----------------------------------------
class OSCClient {
    private var connection: NWConnection?
    
    func connect(ip: String, port: UInt16) {
        connection?.cancel()
        
        let host = NWEndpoint.Host(ip)
        let port = NWEndpoint.Port(rawValue: port)!
        connection = NWConnection(host: host, port: port, using: .udp)
        connection?.start(queue: .global())
    }
    
    // 10個の精鋭特徴量(Float)をOSCフォーマットにエンコードして送信
    func sendFeatures(_ features: [Double]) {
        guard let connection = connection, connection.state == .ready else { return }
        
        var data = Data()
        let address = "/step/features"
        
        // 1. アドレスを書き込み、4の倍数になるようNull(0)パディング
        data.append(address.data(using: .utf8)!)
        data.append(0)
        while data.count % 4 != 0 { data.append(0) }
        
        // 2. タイプタグ（,ffffffffff）を書き込みパディング (10個)
        var typeString = ","
        for _ in features { typeString += "f" }
        data.append(typeString.data(using: .utf8)!)
        data.append(0)
        while data.count % 4 != 0 { data.append(0) }
        
        // 3. Float32値をビッグエンディアンで書き込み
        for feature in features {
            var bigEndian = Float32(feature).bitPattern.bigEndian
            data.append(Data(bytes: &bigEndian, count: MemoryLayout<UInt32>.size))
        }
        
        connection.send(content: data, completion: .contentProcessed({ error in
            if let error = error {
                print("OSC Send Error: \(error)")
            }
        }))
    }
}

// -----------------------------------------
// 構造体 (方向不変な10項目に最適化)
// -----------------------------------------
struct StepRecord {
    let stepNum: Int
    let timestamp: String
    let peak_g: Double
    let step_interval: Double
    let step_interval_var_5: Double
    let peak_g_var_5: Double
    let gyro_norm_at_peak: Double
    let gyro_norm_rms: Double      // ★ 新設 (向き不変)
    let gyro_norm_std: Double      // ★ 新設 (向き不変)
    let lr_asymmetry: Double
    let heading_change: Double
    let step_length: Double
}

// -----------------------------------------
// Motion Step Manager
// -----------------------------------------
class MotionStepManager: ObservableObject {
    private let motionManager = CMMotionManager()
    let oscClient = OSCClient()
    
    @Published var stepStatus: String = "静止中"
    @Published var lastStepTime: String = "---"
    @Published var currentG: Double = 0.0
    @Published var stepCount: Int = 0
    @Published var isRecording: Bool = false
    
    private var stepHistory: [StepRecord] = []
    
    // --- LPF & 動的閾値パラメータ ---
    private let alpha: Double = 0.45             // LPFの強さ
    private var filteredG: Double = 0.0
    
    private var dynamicThreshold: Double = 0.15  // 初期閾値
    private let baseNoiseFloor: Double = 0.15    // 固定下限値
    private let decayRate: Double = 0.97         // 減衰率 (50Hz環境)
    private let bumpFactor: Double = 0.5         // ピーク検知時の閾値跳ね上げ率
    
    // --- 非対称ウィンドウバッファ ---
    private let bufferSize = 7                   // 過去5、現在1、未来1
    private let targetIndex = 5
    
    private var magnitudeBuffer: [Double] = []
    private var timeBuffer: [Date] = []
    
    // --- 【改修】方向不変(Rotation-Invariant)用バッファ ---
    // X,Y,Z個別のバッファを全廃し、合成ベクトル(ノルム)専用バッファのみ保持
    private var longGyroNormBuffer: [Double] = []
    private let longBufferSize = 50              // 直近1秒分 (50Hz × 50)
    
    private let cooldownTime: TimeInterval = 0.35 // 連打防止を少し延長
    private var pastIntervals: [Double] = []
    private var pastPeaks: [Double] = []
    private var lastPeakG: Double = 0.0
    private var lastDetectedTime: Date = Date.distantPast
    
    // --- 進行方向(旋回)検出用 ---
    private var lastStepYaw: Double? = nil
    
    // --- 歩幅推定 (Kim's Method & 1歩目対策) 用 ---
    private var stepAccelSum: Double = 0.0       // 1ステップ間の加速度絶対値の累積
    private var stepSampleCount: Int = 0         // 1ステップ間のサンプル数
    private let stepLengthK: Double = 0.5        // キャリブレーション係数
    private let defaultStepLength: Double = 0.60 // 1歩目（停止後の再開時）に適用するデフォルト歩幅（メートル）
    
    func startTracking(targetIP: String) {
        oscClient.connect(ip: targetIP, port: 5005)
        
        guard motionManager.isDeviceMotionAvailable else {
            self.stepStatus = "DeviceMotion利用不可"
            return
        }
        
        // バッファ初期化
        magnitudeBuffer.removeAll()
        timeBuffer.removeAll()
        longGyroNormBuffer.removeAll()
        pastIntervals.removeAll()
        pastPeaks.removeAll()
        stepHistory.removeAll()
        
        stepCount = 0
        lastDetectedTime = Date.distantPast
        lastPeakG = 0.0
        filteredG = 0.0
        dynamicThreshold = baseNoiseFloor
        lastStepYaw = nil
        stepAccelSum = 0.0
        stepSampleCount = 0
        isRecording = true
        stepStatus = "監視中..."
        
        // 更新間隔50Hz
        motionManager.deviceMotionUpdateInterval = 0.02
        
        motionManager.startDeviceMotionUpdates(to: .main) { [weak self] dmData, error in
            guard let self = self, let dm = dmData else { return }
            
            // 1. 重力方向への投影（内積）: スマホの姿勢に関わらず常に地球基準の上下加速度を抽出
            let ax = dm.userAcceleration.x
            let ay = dm.userAcceleration.y
            let az = dm.userAcceleration.z
            let gx = dm.gravity.x
            let gy = dm.gravity.y
            let gz = dm.gravity.z
            
            let verticalAccel = ax * gx + ay * gy + az * gz
            let rawG = verticalAccel // ※波形を見てピークが負になる場合は -verticalAccel にする
            
            // 2. 指数移動平均(EMA)によるローパスフィルタ
            self.filteredG = (self.alpha * rawG) + ((1.0 - self.alpha) * self.filteredG)
            self.currentG = self.filteredG
            
            // Kim's Method のための加速度累積とサンプル数カウント
            self.stepAccelSum += abs(rawG)
            self.stepSampleCount += 1
            
            let now = Date()
            self.magnitudeBuffer.append(self.filteredG)
            self.timeBuffer.append(now)
            if self.magnitudeBuffer.count > self.bufferSize {
                self.magnitudeBuffer.removeFirst()
                self.timeBuffer.removeFirst()
            }
            
            // 3. 【方向不変】ジャイロの3軸合成値（ノルム）のみを計算してバッファへ保存
            let rx = dm.rotationRate.x
            let ry = dm.rotationRate.y
            let rz = dm.rotationRate.z
            let gyro_norm = sqrt(rx*rx + ry*ry + rz*rz)
            
            self.longGyroNormBuffer.append(gyro_norm)
            if self.longGyroNormBuffer.count > self.longBufferSize {
                self.longGyroNormBuffer.removeFirst()
            }
            
            guard self.magnitudeBuffer.count == self.bufferSize else { return }
            
            // 4. 動的閾値の減衰
            self.dynamicThreshold = max(self.baseNoiseFloor, self.dynamicThreshold * self.decayRate)
            
            // 非対称ウィンドウによるピーク判定
            let centerG = self.magnitudeBuffer[self.targetIndex]
            let isOverThreshold = centerG > self.dynamicThreshold
            let isLocalPeak = isOverThreshold &&
                              self.magnitudeBuffer.prefix(self.targetIndex).allSatisfy { $0 < centerG } &&
                              self.magnitudeBuffer.suffix(self.bufferSize - self.targetIndex - 1).allSatisfy { $0 < centerG }
            
            if isLocalPeak && now.timeIntervalSince(self.lastDetectedTime) > self.cooldownTime {
                
                // ピーク検知で閾値を跳ね上げ
                self.dynamicThreshold = max(self.dynamicThreshold, centerG * self.bumpFactor)
                
                let peakTime = self.timeBuffer[self.targetIndex]
                let interval = (self.lastDetectedTime == Date.distantPast) ? 0.5 : peakTime.timeIntervalSince(self.lastDetectedTime)
                
                self.lastDetectedTime = peakTime
                self.stepCount += 1
                
                let peak_g = centerG
                self.pastIntervals.append(interval)
                if self.pastIntervals.count > 5 { self.pastIntervals.removeFirst() }
                self.pastPeaks.append(peak_g)
                if self.pastPeaks.count > 5 { self.pastPeaks.removeFirst() }
                
                let lr_asymmetry = abs(peak_g - self.lastPeakG)
                self.lastPeakG = peak_g
                
                // --- 旋回角度 (前回ステップからのyaw変化量) ---
                let currentYaw = dm.attitude.yaw
                var heading_change: Double = 0.0
                if let prevYaw = self.lastStepYaw {
                    heading_change = self.normalizeAngle(currentYaw - prevYaw)
                }
                self.lastStepYaw = currentYaw
                
                // --- 歩幅推定 (Kim's Method & 1歩目対策) ---
                var step_length = 0.0
                if interval > 1.2 || self.stepSampleCount > 60 {
                    step_length = self.defaultStepLength
                } else {
                    let avgAccel = self.stepAccelSum / Double(max(1, self.stepSampleCount))
                    step_length = self.stepLengthK * cbrt(avgAccel)
                }
                // リセット
                self.stepAccelSum = 0.0
                self.stepSampleCount = 0
                
                let ts = DateFormatter.localizedString(from: peakTime, dateStyle: .none, timeStyle: .medium)
                
                // --- 【改修】向き依存を排除した全10個の精鋭特徴量 ---
                let features: [Double] = [
                    peak_g,                               // 0: 踏み込みG (地球基準)
                    interval,                             // 1: 時間間隔
                    self.variance(self.pastIntervals),    // 2: 間隔分散
                    self.variance(self.pastPeaks),        // 3: 踏み込み分散
                    gyro_norm,                            // 4: ピーク時ジャイロノルム
                    self.rms(self.longGyroNormBuffer),    // 5: ★ジャイロノルムRMS (不変)
                    self.stdDev(self.longGyroNormBuffer), // 6: ★ジャイロノルム標準偏差 (不変)
                    lr_asymmetry,                         // 7: 左右対称性
                    heading_change,                       // 8: 向き変化 (推論時は除外)
                    step_length                           // 9: 歩幅
                ]
                
                // OSC送信を実行
                self.oscClient.sendFeatures(features)
                
                // CSV保存用レコード
                let record = StepRecord(
                    stepNum: self.stepCount, timestamp: ts,
                    peak_g: features[0], step_interval: features[1], step_interval_var_5: features[2], peak_g_var_5: features[3],
                    gyro_norm_at_peak: features[4], gyro_norm_rms: features[5], gyro_norm_std: features[6],
                    lr_asymmetry: features[7], heading_change: features[8], step_length: features[9]
                )
                self.stepHistory.append(record)
                
                self.stepStatus = "検知: \(String(format: "%.2f", peak_g))G"
                self.lastStepTime = ts
                
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                    if self.stepStatus.starts(with: "検知") { self.stepStatus = "監視中..." }
                }
            }
        }
    }
    
    func stopTracking() {
        motionManager.stopDeviceMotionUpdates()
        stepStatus = "静止中"
        isRecording = false
    }
    
    func generateCSVString() -> String {
        var csv = "step_num,timestamp,peak_g,step_interval,step_interval_var_5,peak_g_var_5,gyro_norm_at_peak,gyro_norm_rms,gyro_norm_std,lr_asymmetry,heading_change,step_length\n"
        for r in stepHistory {
            csv += "\(r.stepNum),\(r.timestamp),\(r.peak_g),\(r.step_interval),\(r.step_interval_var_5),\(r.peak_g_var_5),\(r.gyro_norm_at_peak),\(r.gyro_norm_rms),\(r.gyro_norm_std),\(r.lr_asymmetry),\(r.heading_change),\(r.step_length)\n"
        }
        return csv
    }
    
    private func variance(_ a: [Double]) -> Double {
        guard a.count > 1 else { return 0.0 }
        let avg = a.reduce(0,+) / Double(a.count)
        return a.reduce(0){ $0 + ($1-avg)*($1-avg) } / Double(a.count-1)
    }
    private func stdDev(_ a: [Double]) -> Double { sqrt(variance(a)) }
    private func rms(_ a: [Double]) -> Double {
        guard !a.isEmpty else { return 0.0 }
        return sqrt(a.reduce(0){ $0 + $1*$1 } / Double(a.count))
    }
    private func normalizeAngle(_ angle: Double) -> Double {
        var a = angle
        while a > .pi { a -= 2 * .pi }
        while a < -.pi { a += 2 * .pi }
        return a
    }
}

// ShareSheet は変更なし
struct ShareSheet: UIViewControllerRepresentable {
    var activityItems: [Any]
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: nil)
    }
    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}

struct ContentView: View {
    @StateObject private var manager = MotionStepManager()
    @State private var showShareSheet = false
    @State private var shareText = ""
    
    @State private var targetIP = "192.168.1.XX"

    var body: some View {
        VStack(spacing: 20) {
            
            HStack {
                Text("MacのIP:")
                    .font(.headline)
                TextField("192.168...", text: $targetIP)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                    .keyboardType(.numbersAndPunctuation)
            }
            .padding(.horizontal)
            
            Text(manager.stepStatus)
                .font(.largeTitle).bold()
                .foregroundColor(manager.stepStatus.starts(with: "検知") ? .red : .primary)
            
            VStack(spacing: 8) {
                Text("最後の踏み付け時刻").font(.subheadline).foregroundColor(.secondary)
                Text(manager.lastStepTime)
                    .font(.system(size: 30, weight: .bold, design: .monospaced))
                Text("歩数: \(manager.stepCount)").font(.title2)
                Text(String(format: "現在(地球基準): %.2f G", manager.currentG))
                    .font(.caption).foregroundColor(.gray)
            }
            
            VStack(spacing: 16) {
                HStack(spacing: 16) {
                    Button("検知スタート") {
                        manager.startTracking(targetIP: targetIP)
                    }
                    .font(.headline).padding().frame(maxWidth: .infinity)
                    .background(Color.blue).foregroundColor(.white).cornerRadius(12)
                    
                    Button("ストップ") { manager.stopTracking() }
                    .font(.headline).padding().frame(maxWidth: .infinity)
                    .background(Color.gray.opacity(0.2)).cornerRadius(12)
                }
                Button("CSVデータを共有") {
                    shareText = manager.generateCSVString()
                    showShareSheet = true
                }
                .font(.headline).padding().frame(maxWidth: .infinity)
                .background(manager.stepCount > 0 && !manager.isRecording ? Color.green : Color.gray.opacity(0.3))
                .foregroundColor(.white)
                .disabled(manager.stepCount == 0 || manager.isRecording)
                .cornerRadius(12)
            }
            .padding(.horizontal)
        }
        .padding()
        .sheet(isPresented: $showShareSheet) {
            ShareSheet(activityItems: [shareText])
        }
    }
}

#Preview { ContentView() }
