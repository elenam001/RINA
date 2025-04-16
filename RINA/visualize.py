import json
from pathlib import Path
import matplotlib.pyplot as plt
import csv

def main():
    with open("metrics.json", "r") as f:
        metrics = json.load(f)
    
    # Create CSV report
    csv_path = Path("rina_metrics.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Average Latency (ms)", sum(metrics["latency"])/len(metrics["latency"])])
        writer.writerow(["Max Jitter (ms)", metrics["jitter"]])
        writer.writerow(["Throughput (Mbps)", metrics["throughput"]])
        writer.writerow(["Packet Loss (%)", metrics["packet_loss"]])
        writer.writerow(["QoS Latency Compliance", 
                       f"{metrics['qos_compliance']['actual_latency']}/{metrics['qos_compliance']['target_latency']} ms"])
        writer.writerow(["QoS Bandwidth Compliance", 
                       f"{metrics['qos_compliance']['allocated_bandwidth']}/{metrics['qos_compliance']['target_bandwidth']} Mbps"])

    # Create visualization figure
    plt.figure(figsize=(15, 10))
    
    # Latency Distribution
    plt.subplot(2, 2, 1)
    plt.hist(metrics["latency"], bins=20, color='skyblue', edgecolor='black')
    plt.title(f"Latency Distribution\nAvg: {sum(metrics['latency'])/len(metrics['latency']):.2f}ms")
    plt.xlabel("Latency (ms)")
    plt.ylabel("Frequency")
    
    # Throughput
    plt.subplot(2, 2, 2)
    plt.bar(["Throughput"], [metrics["throughput"]], color='lightgreen')
    plt.title(f"Throughput: {metrics['throughput']:.2f} Mbps")
    plt.ylim(0, 100)
    
    # Packet Loss
    plt.subplot(2, 2, 3)
    plt.pie([100 - metrics["packet_loss"], metrics["packet_loss"]], 
            labels=["Received", "Lost"], 
            colors=['lightcoral', 'grey'], 
            autopct='%1.1f%%')
    plt.title(f"Packet Loss: {metrics['packet_loss']:.2f}%")
    
    # QoS Compliance
    plt.subplot(2, 2, 4)
    qos = metrics["qos_compliance"]
    plt.barh(["Latency", "Bandwidth"], 
            [qos["actual_latency"], qos["allocated_bandwidth"]], 
            color='lightblue', 
            height=0.4)
    plt.barh(["Latency", "Bandwidth"], 
            [qos["target_latency"], qos["target_bandwidth"]], 
            color='none', 
            edgecolor='black', 
            linewidth=2,
            height=0.4)
    plt.title("QoS Compliance")
    plt.xlim(0, max(qos["target_latency"], qos["target_bandwidth"]) + 10)
    
    plt.tight_layout()
    plt.savefig("rina_metrics.png")
    print(f"Visualization saved to rina_metrics.png\nCSV report saved to {csv_path}")
    plt.show()

if __name__ == "__main__":
    main()