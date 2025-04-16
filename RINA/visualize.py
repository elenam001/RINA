import json
from pathlib import Path
import matplotlib.pyplot as plt
import csv

def main():
    with open("metrics.json", "r") as f:
        metrics = json.load(f)
    
    plt.figure(figsize=(20, 15))
    
    # 1. Latency & Jitter
    plt.subplot(3, 3, 1)
    plt.hist(metrics["latency"]["values"], bins=20, color='skyblue', edgecolor='black')
    plt.axvline(metrics["latency"]["average"], color='red', linestyle='dashed', linewidth=2)
    plt.axvline(metrics["latency"]["percentile_95"], color='green', linestyle='dashed', linewidth=2)
    plt.title(f"Latency Distribution\nAvg: {metrics['latency']['average']:.2f}ms, P95: {metrics['latency']['percentile_95']:.2f}ms")
    plt.xlabel("Latency (ms)")
    plt.ylabel("Frequency")
    
    # 2. Jitter 
    plt.subplot(3, 3, 2)
    plt.hist(metrics["jitter"]["values"], bins=20, color='lightgreen', edgecolor='black')
    plt.axvline(metrics["jitter"]["average"], color='red', linestyle='dashed', linewidth=2)
    plt.title(f"Jitter Distribution\nAvg: {metrics['jitter']['average']:.2f}ms")
    plt.xlabel("Jitter (ms)")
    plt.ylabel("Frequency")
    
    # 3. Throughput by packet size
    plt.subplot(3, 3, 3)
    sizes = list(metrics["throughput"]["by_size"].keys())
    values = [metrics["throughput"]["by_size"][str(s)] for s in sizes]
    plt.bar([str(s) for s in sizes], values, color='coral')
    plt.title("Throughput by Packet Size")
    plt.xlabel("Packet Size (bytes)")
    plt.ylabel("Throughput (Mbps)")
    
    # 4. Packet Delivery Ratio
    plt.subplot(3, 3, 4)
    labels = ['Delivered', 'Lost']
    sizes = [metrics["packet_delivery_ratio"]["ratio"], 
             100 - metrics["packet_delivery_ratio"]["ratio"]]
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', colors=['lightblue', 'lightcoral'])
    plt.title(f"Packet Delivery Ratio: {metrics['packet_delivery_ratio']['ratio']:.2f}%")
    
    # 5. Round Trip Time
    plt.subplot(3, 3, 5)
    plt.hist(metrics["round_trip_time"]["values"], bins=20, color='plum', edgecolor='black')
    plt.axvline(metrics["round_trip_time"]["average"], color='red', linestyle='dashed', linewidth=2)
    plt.title(f"Round Trip Time\nAvg: {metrics['round_trip_time']['average']:.2f}ms")
    plt.xlabel("RTT (ms)")
    plt.ylabel("Frequency")
    
    # 6. Bandwidth Utilization
    plt.subplot(3, 3, 6)
    targets = [entry["target"] for entry in metrics["resource_utilization"]["bandwidth_usage"]]
    utilization = [entry["utilization"] for entry in metrics["resource_utilization"]["bandwidth_usage"]]
    plt.bar([str(t) for t in targets], utilization, color='khaki')
    plt.title("Bandwidth Utilization by Target")
    plt.xlabel("Target Bandwidth (Mbps)")
    plt.ylabel("Utilization (%)")
    plt.axhline(100, color='grey', linestyle='dashed')
    
    # 7. Scalability - Setup Time vs Flow Count
    plt.subplot(3, 3, 7)
    plt.plot(metrics["scalability"]["concurrent_flows"], 
             metrics["scalability"]["flow_setup_times"], 
             'o-', color='teal')
    plt.title("Flow Setup Time vs. Concurrent Flows")
    plt.xlabel("Number of Flows")
    plt.ylabel("Setup Time (s)")
    
    # 8. QoS Compliance
    plt.subplot(3, 3, 8)
    labels = ['Compliant', 'Latency Violations', 'Bandwidth Violations']
    violations = [metrics["qos"]["compliance_rate"]/100, 
                 metrics["qos"]["latency_violations"]/len(metrics["qos"]["tests"]), 
                 metrics["qos"]["bandwidth_violations"]/len(metrics["qos"]["tests"])]
    plt.pie(violations, labels=labels, autopct='%1.1f%%', 
            colors=['lightgreen', 'salmon', 'lightgrey'])
    plt.title(f"QoS Compliance: {metrics['qos']['compliance_rate']:.2f}%")
    
    # 9. Summary Statistics
    plt.subplot(3, 3, 9)
    plt.axis('off')
    summary = (
        f"RINA Performance Summary\n\n"
        f"Average Latency: {metrics['latency']['average']:.2f} ms\n"
        f"Average Jitter: {metrics['jitter']['average']:.2f} ms\n"
        f"Average Throughput: {metrics['throughput']['average']:.2f} Mbps\n"
        f"Packet Delivery Ratio: {metrics['packet_delivery_ratio']['ratio']:.2f}%\n"
        f"Average RTT: {metrics['round_trip_time']['average']:.2f} ms\n"
        f"QoS Compliance Rate: {metrics['qos']['compliance_rate']:.2f}%\n"
        f"Max Concurrent Flows: {max(metrics['scalability']['concurrent_flows'])}"
    )
    plt.text(0.5, 0.5, summary, ha='center', va='center', fontsize=12)
    
    plt.tight_layout()
    plt.savefig("enhanced_rina_metrics.png", dpi=300)
    print("Enhanced visualization saved to enhanced_rina_metrics.png")

if __name__ == "__main__":
    main()