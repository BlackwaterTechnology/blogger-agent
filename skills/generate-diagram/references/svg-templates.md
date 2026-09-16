# 原生 SVG 高阶组件模板库 (Native SVG Templates)

本文档固化了 **6 大专业表现模式** 的原生 SVG 标准组件样板代码。所有模板基于 `1200px` 宽画布，统一遵循移动端字号规范（正文 ≥28px，标题 ≥34px），直接复制即可按需调整节点与文案。

---

## 模板 A：系统拓扑边界图 (Topology Map - 对标 UML 部署图/组件图)

**适用**：微服务依赖、K8s 容器包含、云网络 VPC / Subnet / Node 隔离边界。

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 900" width="1200" height="900">
  <defs>
    <linearGradient id="bg_topo" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090E17" />
      <stop offset="100%" stop-color="#0F172A" />
    </linearGradient>
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#38BDF8" />
    </marker>
  </defs>

  <rect width="1200" height="900" fill="url(#bg_topo)" />

  <!-- Header -->
  <g transform="translate(50, 40)">
    <rect width="260" height="40" rx="20" fill="#1E293B" stroke="#38BDF8" stroke-width="1.5" />
    <text x="20" y="27" fill="#38BDF8" font-family="-apple-system, sans-serif" font-size="24" font-weight="800">架构拓扑 · 边界建模</text>
    <text x="0" y="105" fill="#F8FAFC" font-family="-apple-system, sans-serif" font-size="44" font-weight="900">系统拓扑边界：服务包含与网络组网</text>
    <text x="0" y="145" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="28" font-weight="600">展示跨边界调用链路与安全隔离域</text>
  </g>

  <!-- Outer Boundary (e.g. VPC / Cluster) -->
  <g transform="translate(50, 195)">
    <rect width="1100" height="540" rx="18" fill="#111E33" stroke="#334155" stroke-width="2" stroke-dasharray="6,6" />
    <text x="30" y="45" fill="#38BDF8" font-family="-apple-system, sans-serif" font-size="28" font-weight="800">📦 Kubernetes Cluster (VPC: 10.0.0.0/16)</text>

    <!-- Node 1 Container -->
    <g transform="translate(30, 70)">
      <rect width="500" height="430" rx="14" fill="#0B1329" stroke="#38BDF8" stroke-width="1.5" />
      <text x="24" y="40" fill="#7DD3FC" font-family="-apple-system, sans-serif" font-size="28" font-weight="800">Node A (Control Plane)</text>
      
      <!-- Pod Component -->
      <rect x="24" y="65" width="452" height="150" rx="10" fill="#1E293B" stroke="#64748B" stroke-width="1" />
      <text x="44" y="115" fill="#F8FAFC" font-family="-apple-system, sans-serif" font-size="28" font-weight="700">API Server & Controller</text>
      <text x="44" y="155" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">Port 6443 · mTLS Auth</text>

      <rect x="24" y="240" width="452" height="150" rx="10" fill="#1E293B" stroke="#64748B" stroke-width="1" />
      <text x="44" y="290" fill="#F8FAFC" font-family="-apple-system, sans-serif" font-size="28" font-weight="700">etcd Cluster (Raft Log)</text>
      <text x="44" y="330" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">Port 2379 · Persistent Storage</text>
    </g>

    <!-- Connecting Bus / Arrow -->
    <path d="M 530 200 L 570 200" stroke="#38BDF8" stroke-width="3" marker-end="url(#arrow)" />
    <text x="532" y="185" fill="#38BDF8" font-family="-apple-system, sans-serif" font-size="22" font-weight="700">gRPC</text>

    <!-- Node 2 Container -->
    <g transform="translate(570, 70)">
      <rect width="500" height="430" rx="14" fill="#0B1329" stroke="#10B981" stroke-width="1.5" />
      <text x="24" y="40" fill="#6EE7B7" font-family="-apple-system, sans-serif" font-size="28" font-weight="800">Node B (Worker Node)</text>
      
      <rect x="24" y="65" width="452" height="150" rx="10" fill="#1E293B" stroke="#64748B" stroke-width="1" />
      <text x="44" y="115" fill="#F8FAFC" font-family="-apple-system, sans-serif" font-size="28" font-weight="700">App Workload Pod</text>
      <text x="44" y="155" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">Limits: 2C / 4GiB · Web Traffic</text>

      <rect x="24" y="240" width="452" height="150" rx="10" fill="#1E293B" stroke="#64748B" stroke-width="1" />
      <text x="44" y="290" fill="#F8FAFC" font-family="-apple-system, sans-serif" font-size="28" font-weight="700">Kubelet & Envoy Proxy</text>
      <text x="44" y="330" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">Node Agent · Health Probe</text>
    </g>
  </g>

  <!-- Bottom Takeaway -->
  <g transform="translate(50, 765)">
    <rect width="1100" height="100" rx="14" fill="#1E293B" stroke="#38BDF8" stroke-width="1.5" />
    <text x="30" y="42" fill="#38BDF8" font-family="-apple-system, sans-serif" font-size="26" font-weight="800">💡 架构原则：跨节点通信强制 mTLS 加密与网络策略审计</text>
    <text x="30" y="76" fill="#CBD5E1" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">控制面与数据面物理隔离，消除单点故障扩散风险。</text>
  </g>
</svg>
```

---

## 模板 B：状态机闭环图 (State Machine - 对标 UML 状态机图)

**适用**：Pod 生命周期、重试退避算法、健康检测探针、订单状态变迁。

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 920" width="1200" height="920">
  <defs>
    <linearGradient id="bg_state" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090E17" />
      <stop offset="100%" stop-color="#0F172A" />
    </linearGradient>
    <marker id="arrow_pink" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#F472B6" />
    </marker>
    <marker id="arrow_green" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#34D399" />
    </marker>
  </defs>

  <rect width="1200" height="920" fill="url(#bg_state)" />

  <!-- Header -->
  <g transform="translate(50, 40)">
    <rect width="280" height="40" rx="20" fill="#1E293B" stroke="#EC4899" stroke-width="1.5" />
    <text x="20" y="27" fill="#F472B6" font-family="-apple-system, sans-serif" font-size="24" font-weight="800">状态建模 · 生命周期回路</text>
    <text x="0" y="105" fill="#F8FAFC" font-family="-apple-system, sans-serif" font-size="44" font-weight="900">健康探测与指数退避重试状态机</text>
    <text x="0" y="145" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="28" font-weight="600">穷尽异常分支与自动自愈回路，杜绝状态悬空</text>
  </g>

  <!-- States Canvas -->
  <g transform="translate(50, 200)">
    <!-- State 1: PENDING -->
    <rect x="0" y="80" width="220" height="120" rx="16" fill="#1E293B" stroke="#94A3B8" stroke-width="2" />
    <text x="35" y="130" fill="#F8FAFC" font-family="-apple-system, sans-serif" font-size="30" font-weight="800">PENDING</text>
    <text x="35" y="165" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">资源调度中</text>

    <!-- Transition 1 -> 2 -->
    <path d="M 220 140 L 330 140" stroke="#34D399" stroke-width="3" marker-end="url(#arrow_green)" />
    <text x="230" y="125" fill="#34D399" font-family="-apple-system, sans-serif" font-size="22" font-weight="700">Scheduled</text>

    <!-- State 2: RUNNING -->
    <rect x="330" y="80" width="240" height="120" rx="16" fill="#0D281E" stroke="#10B981" stroke-width="2" />
    <text x="365" y="130" fill="#6EE7B7" font-family="-apple-system, sans-serif" font-size="30" font-weight="800">RUNNING</text>
    <text x="365" y="165" fill="#A7F3D0" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">探针 200 OK</text>

    <!-- Transition 2 -> 3 (Failure) -->
    <path d="M 570 140 L 680 140" stroke="#F472B6" stroke-width="3" marker-end="url(#arrow_pink)" />
    <text x="580" y="125" fill="#F472B6" font-family="-apple-system, sans-serif" font-size="22" font-weight="700">Probe Failed</text>

    <!-- State 3: BACKOFF RETRY -->
    <rect x="680" y="80" width="260" height="120" rx="16" fill="#2B141C" stroke="#EF4444" stroke-width="2" />
    <text x="710" y="130" fill="#FCA5A5" font-family="-apple-system, sans-serif" font-size="30" font-weight="800">BACKOFF</text>
    <text x="710" y="165" fill="#CBD5E1" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">[retry_count &lt; 3]</text>

    <!-- Loop: 3 -> 2 (Backoff Delay Loop) -->
    <path d="M 810 80 C 810 0, 450 0, 450 70" fill="none" stroke="#F59E0B" stroke-width="2.5" stroke-dasharray="6,4" marker-end="url(#arrow_green)" />
    <text x="530" y="25" fill="#FBBF24" font-family="-apple-system, sans-serif" font-size="22" font-weight="700">指数退避 (2s, 4s, 8s) 重启</text>

    <!-- Transition 3 -> 4 (Fatal Crash) -->
    <path d="M 810 200 L 810 320" stroke="#EF4444" stroke-width="3" marker-end="url(#arrow_pink)" />
    <text x="825" y="265" fill="#EF4444" font-family="-apple-system, sans-serif" font-size="22" font-weight="700">[retry >= 3] 熔断</text>

    <!-- State 4: CRASH_LOOP -->
    <rect x="680" y="320" width="260" height="120" rx="16" fill="#1B131D" stroke="#EF4444" stroke-width="2.5" />
    <text x="705" y="370" fill="#EF4444" font-family="-apple-system, sans-serif" font-size="28" font-weight="900">CrashLoopBackOff</text>
    <text x="705" y="405" fill="#FCA5A5" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">发送 PagerDuty 告警</text>
  </g>

  <!-- Bottom Takeaway -->
  <g transform="translate(50, 785)">
    <rect width="1100" height="95" rx="14" fill="#1E293B" stroke="#EC4899" stroke-width="1.5" />
    <text x="30" y="40" fill="#F472B6" font-family="-apple-system, sans-serif" font-size="26" font-weight="800">★ 状态机设计铁律：任何异常分支必须显式定义最大重试计数与熔断出口</text>
    <text x="30" y="74" fill="#CBD5E1" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">严禁死循环重试，防止雪崩击穿下游存储依赖。</text>
  </g>
</svg>
```

---

## 模板 C：垂直因果时序管道 (Causal Pipeline - 对标 UML 活动图/顺序图)

**适用**：故障排查扩散链路、SOP 实施流程、端到端数据流水线。

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 950" width="1200" height="950">
  <defs>
    <linearGradient id="bg_pipe" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090E17" />
      <stop offset="100%" stop-color="#0F172A" />
    </linearGradient>
  </defs>

  <rect width="1200" height="950" fill="url(#bg_pipe)" />

  <!-- Header -->
  <g transform="translate(50, 35)">
    <rect width="280" height="42" rx="21" fill="#1E293B" stroke="#A855F7" stroke-width="1.5" />
    <text x="24" y="29" fill="#C084FC" font-family="-apple-system, sans-serif" font-size="26" font-weight="800">时序管道 · 故障因果链</text>
    <text x="0" y="105" fill="#F8FAFC" font-family="-apple-system, sans-serif" font-size="44" font-weight="900">故障级联扩散链：从错误配置到系统雪崩</text>
    <text x="0" y="145" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="28" font-weight="600">四步因果演进：还原生产事故的连锁传播机制</text>
  </g>

  <!-- Pipeline Steps (Stacked) -->
  <g transform="translate(50, 190)">
    <!-- Vertical connecting line -->
    <line x1="45" y1="40" x2="45" y2="580" stroke="#475569" stroke-width="4" stroke-dasharray="6,6" />

    <!-- Step 1 -->
    <g transform="translate(0, 0)">
      <circle cx="45" cy="50" r="28" fill="#1E293B" stroke="#38BDF8" stroke-width="3" />
      <text x="35" y="58" fill="#38BDF8" font-family="-apple-system, sans-serif" font-size="26" font-weight="900">01</text>
      <rect x="100" y="0" width="1000" height="110" rx="14" fill="#111E33" stroke="#38BDF8" stroke-width="1.5" />
      <text x="130" y="44" fill="#F8FAFC" font-family="-apple-system, sans-serif" font-size="28" font-weight="800">配置失真：CPU Requests 虚高 90 倍</text>
      <text x="130" y="82" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">实测仅消耗 11m，随意声明 1000m，导致调度器将 CPU 误判为第一瓶颈。</text>
    </g>

    <!-- Step 2 -->
    <g transform="translate(0, 145)">
      <circle cx="45" cy="50" r="28" fill="#1E293B" stroke="#F59E0B" stroke-width="3" />
      <text x="35" y="58" fill="#F59E0B" font-family="-apple-system, sans-serif" font-size="26" font-weight="900">02</text>
      <rect x="100" y="0" width="1000" height="110" rx="14" fill="#241B12" stroke="#F59E0B" stroke-width="1.5" />
      <text x="130" y="44" fill="#FDE68A" font-family="-apple-system, sans-serif" font-size="28" font-weight="800">选型偏差：调度器锁死 c 系列计算型机型</text>
      <text x="130" y="82" fill="#CBD5E1" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">为降低单位核成本避开 m/r 系列，整机内存配比被压缩至 2 GiB/Core 极限。</text>
    </g>

    <!-- Step 3 -->
    <g transform="translate(0, 290)">
      <circle cx="45" cy="50" r="28" fill="#1E293B" stroke="#EF4444" stroke-width="3" />
      <text x="35" y="58" fill="#EF4444" font-family="-apple-system, sans-serif" font-size="26" font-weight="900">03</text>
      <rect x="100" y="0" width="1000" height="110" rx="14" fill="#2B141C" stroke="#EF4444" stroke-width="1.5" />
      <text x="130" y="44" fill="#FCA5A5" font-family="-apple-system, sans-serif" font-size="28" font-weight="800">页缓存挤爆：Direct Reclaim 引发整机冻结</text>
      <text x="130" y="82" fill="#CBD5E1" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">操作系统无剩余内存用于 Page Cache，磁盘 I/O 停滞，Kubelet 探针超时崩溃。</text>
    </g>

    <!-- Step 4 -->
    <g transform="translate(0, 435)">
      <circle cx="45" cy="50" r="28" fill="#2B141C" stroke="#EF4444" stroke-width="3" />
      <text x="35" y="58" fill="#EF4444" font-family="-apple-system, sans-serif" font-size="26" font-weight="900">04</text>
      <rect x="100" y="0" width="1000" height="110" rx="14" fill="#1C1017" stroke="#EF4444" stroke-width="2" />
      <text x="130" y="44" fill="#EF4444" font-family="-apple-system, sans-serif" font-size="28" font-weight="900">缩容失效：整机死锁拒绝碎片整理</text>
      <text x="130" y="82" fill="#FCA5A5" font-family="-apple-system, sans-serif" font-size="24" font-weight="700">虚高 CPU req 被自动伸缩器当成高饱和，整机长期盘踞造成巨额账单浪费！</text>
    </g>
  </g>

  <!-- Bottom Takeaway -->
  <g transform="translate(50, 810)">
    <rect width="1100" height="100" rx="14" fill="#1E293B" stroke="#A855F7" stroke-width="1.5" />
    <text x="30" y="42" fill="#C084FC" font-family="-apple-system, sans-serif" font-size="26" font-weight="800">★ 破局对策：按实测压测指标声明 requests，从根源切断级联死锁链</text>
    <text x="30" y="76" fill="#CBD5E1" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">配置即架构约束，前端的一行随意虚报，必将在底层操作系统引发百倍雪崩。</text>
  </g>
</svg>
```

---

## 模板 D：二元对抗与 2x2 权衡矩阵 (Trade-off Matrix)

**适用**：选型对抗（❌旧模式 vs ✅新模式）、成本/稳定性四象限。

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 880" width="1200" height="880">
  <defs>
    <linearGradient id="bg_matrix" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090E17" />
      <stop offset="100%" stop-color="#0F172A" />
    </linearGradient>
  </defs>

  <rect width="1200" height="880" fill="url(#bg_matrix)" />

  <!-- Header -->
  <g transform="translate(50, 40)">
    <rect width="280" height="42" rx="21" fill="#1E293B" stroke="#F59E0B" stroke-width="1.5" />
    <text x="24" y="29" fill="#FBBF24" font-family="-apple-system, sans-serif" font-size="26" font-weight="800">架构决策 · 二元权衡矩阵</text>
    <text x="0" y="105" fill="#F8FAFC" font-family="-apple-system, sans-serif" font-size="44" font-weight="900">新旧范式对抗：传统单体 vs 现代事件驱动</text>
    <text x="0" y="145" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="28" font-weight="600">空间对抗破除盲区，直击反模式的技术与商业代价</text>
  </g>

  <!-- 2 Columns VS -->
  <g transform="translate(50, 190)">
    <!-- Left Column: Anti-pattern -->
    <rect x="0" y="0" width="530" height="520" rx="18" fill="#1C141B" stroke="#EF4444" stroke-width="1.5" />
    <g transform="translate(25, 25)">
      <rect width="200" height="40" rx="8" fill="#EF4444" opacity="0.2" />
      <text x="16" y="28" fill="#F87171" font-family="-apple-system, sans-serif" font-size="26" font-weight="800">❌ 传统同步单体</text>
      
      <text x="0" y="80" fill="#FCA5A5" font-family="-apple-system, sans-serif" font-size="30" font-weight="800">强耦合与高昂故障半径</text>
      
      <text x="0" y="140" fill="#E2E8F0" font-family="-apple-system, sans-serif" font-size="26" font-weight="700">• 同步 HTTP 阻塞链条长</text>
      <text x="0" y="180" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">任一微服务延迟陡增直接耗尽连接池</text>

      <text x="0" y="240" fill="#E2E8F0" font-family="-apple-system, sans-serif" font-size="26" font-weight="700">• 局部故障引发全局雪崩</text>
      <text x="0" y="280" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">缺乏削峰与缓冲，流量峰值击垮核心库</text>

      <text x="0" y="340" fill="#E2E8F0" font-family="-apple-system, sans-serif" font-size="26" font-weight="700">• 发布升级牵一发而动全身</text>
      <text x="0" y="380" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">多团队共用单体代码库，部署周期拉长</text>

      <rect x="0" y="420" width="480" height="50" rx="8" fill="#2B141C" />
      <text x="16" y="455" fill="#EF4444" font-family="-apple-system, sans-serif" font-size="24" font-weight="800">代价：可用性脆弱，维护成本呈指数级攀升</text>
    </g>

    <!-- Right Column: Best Practice -->
    <g transform="translate(570, 0)">
      <rect x="0" y="0" width="530" height="520" rx="18" fill="#0D261E" stroke="#10B981" stroke-width="1.5" />
      <g transform="translate(25, 25)">
        <rect width="200" height="40" rx="8" fill="#10B981" opacity="0.2" />
        <text x="16" y="28" fill="#34D399" font-family="-apple-system, sans-serif" font-size="26" font-weight="800">✅ 现代事件驱动</text>
        
        <text x="0" y="80" fill="#6EE7B7" font-family="-apple-system, sans-serif" font-size="30" font-weight="800">异步解耦与天然削峰隔离</text>
        
        <text x="0" y="140" fill="#E2E8F0" font-family="-apple-system, sans-serif" font-size="26" font-weight="700">• Kafka / MQ 消息持久化隔离</text>
        <text x="0" y="180" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">上游毫秒级确认返回，下游按需消费</text>

        <text x="0" y="240" fill="#E2E8F0" font-family="-apple-system, sans-serif" font-size="26" font-weight="700">• 故障半径收敛至单一服务</text>
        <text x="0" y="280" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">消费者宕机数据不丢，修复后断点续传</text>

        <text x="0" y="340" fill="#E2E8F0" font-family="-apple-system, sans-serif" font-size="26" font-weight="700">• 独立迭代与水平伸缩自由</text>
        <text x="0" y="380" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">业务域清晰自治，单模块发布零停机</text>

        <rect x="0" y="420" width="480" height="50" rx="8" fill="#123B2F" />
        <text x="16" y="455" fill="#34D399" font-family="-apple-system, sans-serif" font-size="24" font-weight="800">优势：99.99% 高可用，支持业务弹性扩张</text>
      </g>
    </g>
  </g>

  <!-- Bottom Takeaway -->
  <g transform="translate(50, 740)">
    <rect width="1100" height="100" rx="14" fill="#1E293B" stroke="#F59E0B" stroke-width="1.5" />
    <text x="30" y="42" fill="#FBBF24" font-family="-apple-system, sans-serif" font-size="26" font-weight="800">决策分水岭：当单日请求超千万或跨团队协作受阻时，果断切入事件驱动架构</text>
    <text x="30" y="76" fill="#CBD5E1" font-family="-apple-system, sans-serif" font-size="24" font-weight="500">用短暂的异步复杂度，置换长期的系统弹力与研发工程吞吐率。</text>
  </g>
</svg>
```

---

## 模板 E：macOS 拟真 CLI 终端切片 (Terminal Slice - 实证量化)

**适用**：真实命令输出、报错切片还原、压测结果回放。

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 680" width="1200" height="680">
  <defs>
    <linearGradient id="bg_term" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090E17" />
      <stop offset="100%" stop-color="#0F172A" />
    </linearGradient>
  </defs>

  <rect width="1200" height="680" fill="url(#bg_term)" />

  <!-- Terminal Window (w=1100, h=580) -->
  <g transform="translate(50, 45)">
    <!-- Terminal Outer Shell -->
    <rect width="1100" height="580" rx="16" fill="#0A0E17" stroke="#334155" stroke-width="2" />
    
    <!-- Title Bar -->
    <rect width="1100" height="46" rx="16" fill="#1E293B" />
    <rect y="30" width="1100" height="16" fill="#1E293B" />
    
    <!-- macOS Traffic Light Buttons -->
    <circle cx="28" cy="23" r="7" fill="#EF4444" />
    <circle cx="50" cy="23" r="7" fill="#F59E0B" />
    <circle cx="72" cy="23" r="7" fill="#10B981" />
    
    <!-- Window Title -->
    <text x="550" y="29" text-anchor="middle" fill="#94A3B8" font-family="-apple-system, sans-serif" font-size="20" font-weight="600">bash — kubectl get nodes -o wide</text>

    <!-- Terminal Code Body -->
    <g transform="translate(30, 80)">
      <!-- Command 1 -->
      <text x="0" y="28" fill="#38BDF8" font-family="'JetBrains Mono', 'SF Mono', monospace" font-size="26" font-weight="700">$ kubectl get nodes -l karpenter.sh/nodepool=default</text>
      
      <!-- Output Header -->
      <text x="0" y="75" fill="#94A3B8" font-family="'JetBrains Mono', 'SF Mono', monospace" font-size="22" font-weight="600">NAME                                  STATUS   ROLES    AGE   INSTANCE-TYPE   ZONE</text>
      
      <!-- Output Rows -->
      <text x="0" y="115" fill="#F8FAFC" font-family="'JetBrains Mono', 'SF Mono', monospace" font-size="22" font-weight="500">ip-10-0-12-84.ec2.internal           Ready    &lt;none&gt;   8d    c5a.large       us-east-1a</text>
      <text x="0" y="155" fill="#F8FAFC" font-family="'JetBrains Mono', 'SF Mono', monospace" font-size="22" font-weight="500">ip-10-0-18-91.ec2.internal           Ready    &lt;none&gt;   8d    c5a.large       us-east-1b</text>
      <text x="0" y="195" fill="#EF4444" font-family="'JetBrains Mono', 'SF Mono', monospace" font-size="22" font-weight="700">ip-10-0-24-11.ec2.internal           NotReady &lt;none&gt;   2h    c5a.large       us-east-1a</text>

      <line x1="0" y1="230" x2="1040" y2="230" stroke="#334155" stroke-width="1" />

      <!-- Command 2 -->
      <text x="0" y="275" fill="#38BDF8" font-family="'JetBrains Mono', 'SF Mono', monospace" font-size="26" font-weight="700">$ kubectl describe node ip-10-0-24-11 | grep -E "Out of memory|Kubelet stopped"</text>
      
      <text x="0" y="325" fill="#EF4444" font-family="'JetBrains Mono', 'SF Mono', monospace" font-size="24" font-weight="800">System OOM encountered: Eviction manager: direct reclaim stall &gt; 30s</text>
      <text x="0" y="365" fill="#FCA5A5" font-family="'JetBrains Mono', 'SF Mono', monospace" font-size="22" font-weight="500">Kubelet probe timeout: container search-svc failed liveness check, restarting...</text>
      <text x="0" y="405" fill="#F59E0B" font-family="'JetBrains Mono', 'SF Mono', monospace" font-size="22" font-weight="700">Warning: Node ip-10-0-24-11 status is now NotReady (Direct Reclaim Freeze)</text>
    </g>
  </g>
</svg>
```
