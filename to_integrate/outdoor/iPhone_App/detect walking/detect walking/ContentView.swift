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
    
    func sendFeatures(_ features: [Double]) {
        guard let connection = connection, connection.state == .ready else { return }
        
        var data = Data()
        let address = "/step/features"
        
        // 1. アドレス
        data.append(address.data(using: .utf8)!)
        data.append(0)
        while data.count % 4 != 0 { data.append(0) }
        
        // 2. タイプタグ
        var typeString = ","
        for _ in features { typeString += "f" }
        data.append(typeString.data(using: .utf8)!)
        data.append(0)
        while data.count % 4 != 0 { data.append(0) }
        
        // 3. Float32ペイロード
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
// 構造体
// -----------------------------------------
struct StepRecord {
    let stepNum: Int
    let timestamp: String
    let peak_g: Double; let step_interval: Double; let step_interval_var_5: Double; let peak_g_var_5: Double
    let gyro_norm_at_peak: Double; let gyro_x_rms: Double; let gyro_y_rms: Double; let gyro_z_rms: Double
    let lr_asymmetry: Double; let gravity_x_std: Double; let gravity_y_std: Double; let pitch_std: Double; let roll_std: Double
    let heading_change: Double; let step_length: Double
}

// -----------------------------------------
// Motion Manager
// -----------------------------------------
class MotionStepManager: ObservableObject {
    private let motionManager = CMMotionManager()
    let oscClient = OSCClient()
    
    @Published var stepStatus: String = "静止中"
    @Published var lastStepTime: String = "---"
    @Published var currentG: Double = 0.0 // LPF適用後のGを表示
    @Published var stepCount: Int = 0
    @Published var isRecording: Bool = false
    
    private var stepHistory: [StepRecord] = []
    
    // --- LPF & 動的閾値パラメータ ---
    private let alpha: Double = 0.45             // LPFの強さ (0.0~1.0) 低いほど滑らかだが遅延増
    private var filteredG: Double = 0.0
    
    private var dynamicThreshold: Double = 0.15  // 初期閾値
    private let baseNoiseFloor: Double = 0.15    // 固定下限値 (重力除去済みのため低くてよい)
    private let decayRate: Double = 0.97         // 減衰率 (50Hz環境。毎フレーム乗算)
    private let bumpFactor: Double = 0.5         // ピーク検知時に現在のGの何%を次の閾値にするか
    
    // --- 非対称ウィンドウバッファ ---
    private let bufferSize = 7                   // 過去5、現在(検知対象)1、未来1
    private let targetIndex = 5                  // バッファ配列内のピーク判定位置
    
    private var magnitudeBuffer: [Double] = []
    private var timeBuffer: [Date] = []
    
    // 特徴量用バッファ
    private var longGyroXBuffer: [Double] = []
    private var longGyroYBuffer: [Double] = []
    private var longGyroZBuffer: [Double] = []
    private var longGravityXBuffer: [Double] = []
    private var longGravityYBuffer: [Double] = []
    private var longPitchBuffer: [Double] = []
    private var longRollBuffer: [Double] = []
    private let longBufferSize = 50
    
    private let cooldownTime: TimeInterval = 0.25
    private var pastIntervals: [Double] = []
    private var pastPeaks: [Double] = []
    private var lastPeakG: Double = 0.0          // ベースライン変更に伴い初期値を0.0に変更
    private var lastDetectedTime: Date = Date.distantPast
    
    // --- 進行方向(旋回)検出用 ---
    // dm.attitude.yaw は「鉛直軸(重力方向)まわりの回転角」なので、
    // 絶対的な方角(磁北基準)ではなくても「前回ステップからどれだけ向きが変わったか」の検出には十分使える
    private var lastStepYaw: Double? = nil
    
    // --- 歩幅推定 (Kim's Method & 1歩目対策) 用 ---
    private var stepAccelSum: Double = 0.0       // 1ステップ間の加速度絶対値の累積
    private var stepSampleCount: Int = 0         // 1ステップ間のサンプル数
    private let stepLengthK: Double = 0.5        // キャリブレーション係数
    private let defaultStepLength: Double = 0.60 // 1歩目（停止後の再開時）に適用するデフォルト歩幅（メートル）// 個人差が大きいので要キャリブレーション(目安 0.3〜0.7)
    
    func startTracking(targetIP: String) {
        oscClient.connect(ip: targetIP, port: 5005)
        
        guard motionManager.isDeviceMotionAvailable else {
            self.stepStatus = "DeviceMotion利用不可"
            return
        }
        
        magnitudeBuffer.removeAll(); timeBuffer.removeAll()
        longGyroXBuffer.removeAll(); longGyroYBuffer.removeAll(); longGyroZBuffer.removeAll()
        longGravityXBuffer.removeAll(); longGravityYBuffer.removeAll()
        longPitchBuffer.removeAll(); longRollBuffer.removeAll()
        pastIntervals.removeAll(); pastPeaks.removeAll(); stepHistory.removeAll()
        
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
        
        // DeviceMotionに一本化
        motionManager.startDeviceMotionUpdates(to: .main) { [weak self] dmData, error in
            guard let self = self, let dm = dmData else { return }
            // 1. userAcceleration (純粋な動き) と gravity (重力方向) の取得
            let ax = dm.userAcceleration.x
            let ay = dm.userAcceleration.y
            let az = dm.userAcceleration.z

            let gx = dm.gravity.x
            let gy = dm.gravity.y
            let gz = dm.gravity.z

            // 2. 内積（ドット積）を計算し、上下方向の加速度成分のみを抽出する
            // 重力は常に下を向いているため、足の振り上げと踏みつけで符号が綺麗に反転します。
            let verticalAccel = ax * gx + ay * gy + az * gz

            // ※踏みつけの衝撃が、正または負どちらのピークに出るかは波形を見て確認し、
            // 負に出る場合は符号を反転( let rawG = -verticalAccel )させてください。
            let rawG = verticalAccel

            // 3. 指数移動平均(EMA)によるローパスフィルタ
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
            
            // 特徴量計算用の履歴保存
            self.longGyroXBuffer.append(dm.rotationRate.x)
            self.longGyroYBuffer.append(dm.rotationRate.y)
            self.longGyroZBuffer.append(dm.rotationRate.z)
            self.longGravityXBuffer.append(dm.gravity.x)
            self.longGravityYBuffer.append(dm.gravity.y)
            self.longPitchBuffer.append(dm.attitude.pitch)
            self.longRollBuffer.append(dm.attitude.roll)
            
            if self.longGyroXBuffer.count > self.longBufferSize {
                self.longGyroXBuffer.removeFirst(); self.longGyroYBuffer.removeFirst(); self.longGyroZBuffer.removeFirst()
                self.longGravityXBuffer.removeFirst(); self.longGravityYBuffer.removeFirst()
                self.longPitchBuffer.removeFirst(); self.longRollBuffer.removeFirst()
            }
            
            guard self.magnitudeBuffer.count == self.bufferSize else { return }
            
            // 3. 動的閾値の減衰 (O(1)処理)
            self.dynamicThreshold = max(self.baseNoiseFloor, self.dynamicThreshold * self.decayRate)
            
            // 非対称ウィンドウによるピーク判定 (遅延20ms)
            let centerG = self.magnitudeBuffer[self.targetIndex]
            
            let isOverThreshold = centerG > self.dynamicThreshold
            let isLocalPeak = isOverThreshold &&
                              self.magnitudeBuffer.prefix(self.targetIndex).allSatisfy { $0 < centerG } &&
                              self.magnitudeBuffer.suffix(self.bufferSize - self.targetIndex - 1).allSatisfy { $0 < centerG }
            
            if isLocalPeak && now.timeIntervalSince(self.lastDetectedTime) > self.cooldownTime {
                
                // ピークを検知したら閾値を跳ね上げる
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
                
                let rx = dm.rotationRate.x
                let ry = dm.rotationRate.y
                let rz = dm.rotationRate.z
                let gyro_norm_at_peak = sqrt(rx*rx + ry*ry + rz*rz)
                
                let lr_asymmetry = abs(peak_g - self.lastPeakG)
                self.lastPeakG = peak_g
                
                // --- 旋回角度 (前回ステップからのyaw変化量、単位:ラジアン) ---
                let currentYaw = dm.attitude.yaw
                var heading_change: Double = 0.0
                if let prevYaw = self.lastStepYaw {
                    heading_change = self.normalizeAngle(currentYaw - prevYaw)
                }
                self.lastStepYaw = currentYaw
                // --- 歩幅推定 (Kim's Method & 1歩目のデフォルト強制適用) ---
                var step_length = 0.0

                // 前回の検知から1.2秒(60フレーム)以上空いた場合は「1歩目・歩き始め」と判定して固定値を適用
                if interval > 1.2 || self.stepSampleCount > 60 {
                    step_length = self.defaultStepLength
                } else {
                    // 継続した歩行中は Kim's Method で歩幅算出: K * cbrt(sum / N)
                    let avgAccel = self.stepAccelSum / Double(max(1, self.stepSampleCount))
                    step_length = self.stepLengthK * cbrt(avgAccel)
                }

                // 次のステップに向けて累積値とカウントをリセット
                self.stepAccelSum = 0.0
                self.stepSampleCount = 0
                
                let ts = DateFormatter.localizedString(from: peakTime, dateStyle: .none, timeStyle: .medium)
                
                let features: [Double] = [
                    peak_g, interval, self.variance(self.pastIntervals), self.variance(self.pastPeaks),
                    gyro_norm_at_peak, self.rms(self.longGyroXBuffer), self.rms(self.longGyroYBuffer), self.rms(self.longGyroZBuffer),
                    lr_asymmetry, self.stdDev(self.longGravityXBuffer), self.stdDev(self.longGravityYBuffer),
                    self.stdDev(self.longPitchBuffer), self.stdDev(self.longRollBuffer),
                    heading_change, step_length
                ]
                
                self.oscClient.sendFeatures(features)
                
                let record = StepRecord(
                    stepNum: self.stepCount, timestamp: ts,
                    peak_g: features[0], step_interval: features[1], step_interval_var_5: features[2], peak_g_var_5: features[3],
                    gyro_norm_at_peak: features[4], gyro_x_rms: features[5], gyro_y_rms: features[6], gyro_z_rms: features[7],
                    lr_asymmetry: features[8], gravity_x_std: features[9], gravity_y_std: features[10], pitch_std: features[11], roll_std: features[12],
                    heading_change: features[13], step_length: features[14]
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
        var csv = "step_num,timestamp,peak_g,step_interval,step_interval_var_5,peak_g_var_5,gyro_norm_at_peak,gyro_x_rms,gyro_y_rms,gyro_z_rms,lr_asymmetry,gravity_x_std,gravity_y_std,pitch_std,roll_std,heading_change,step_length\n"
        for r in stepHistory {
            csv += "\(r.stepNum),\(r.timestamp),\(r.peak_g),\(r.step_interval),\(r.step_interval_var_5),\(r.peak_g_var_5),\(r.gyro_norm_at_peak),\(r.gyro_x_rms),\(r.gyro_y_rms),\(r.gyro_z_rms),\(r.lr_asymmetry),\(r.gravity_x_std),\(r.gravity_y_std),\(r.pitch_std),\(r.roll_std),\(r.heading_change),\(r.step_length)\n"
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
    // yaw角の差分を -π〜π の範囲に正規化 (±πをまたぐ瞬間のジャンプを防ぐ)
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
                Text(String(format: "現在(重力抜): %.2f G", manager.currentG))
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

