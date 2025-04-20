import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import pandas as pd
from pathlib import Path
from matplotlib.colors import LinearSegmentedColormap

def main():
    plt.style.use('ggplot')
    sns.set_context("talk")
    with open("metrics.json", "r") as f:
        metrics = json.load(f)
    export_to_csv(metrics)
    fig = plt.figure(figsize=(20, 18))
    gs = gridspec.GridSpec(3, 3, figure=fig)
    main_colors = ["#3498db", "#2ecc71", "#e74c3c", "#f39c12", "#9b59b6"]
    cmap_blue = LinearSegmentedColormap.from_list("", ["#d4e6f1", "#3498db", "#1a5276"])
    
    # 1. Latency Distribution
    ax1 = fig.add_subplot(gs[0, 0])
    if metrics["latency"]["values"]:
        sns.histplot(metrics["latency"]["values"], bins=20, kde=True, color=main_colors[0], ax=ax1)
        ax1.axvline(metrics["latency"]["average"], color=main_colors[2], linestyle='dashed', linewidth=2, 
                    label=f'Mean: {metrics["latency"]["average"]:.2f}ms')
        ax1.axvline(metrics["latency"]["percentile_95"], color=main_colors[3], linestyle='dashed', linewidth=2,
                   label=f'P95: {metrics["latency"]["percentile_95"]:.2f}ms')
        ax1.set_title("Latency Distribution", fontweight='bold', fontsize=14)
        ax1.set_xlabel("Latency (ms)")
        ax1.set_ylabel("Frequency")
        ax1.legend()
    else:
        ax1.text(0.5, 0.5, 'No Latency Data', ha='center', va='center')
        ax1.set_title("Latency Distribution", fontweight='bold', fontsize=14)
    
    # 2. Throughput by Packet Size
    ax2 = fig.add_subplot(gs[0, 1])
    if metrics["throughput"]["by_size"]:
        sizes = sorted([int(s) for s in metrics["throughput"]["by_size"].keys()])
        values = [metrics["throughput"]["by_size"][str(s)] for s in sizes]
        
        bars = ax2.bar(range(len(sizes)), values, color=main_colors[1])
        ax2.set_xticks(range(len(sizes)))
        ax2.set_xticklabels([f"{s} bytes" for s in sizes], rotation=45, ha='right')
        ax2.set_xlabel("Packet Size")
        ax2.set_ylabel("Throughput (Mbps)")
        
        for bar in bars:
            height = bar.get_height()
            ax2.annotate(f'{height:.1f} Mbps',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')
        ax2.set_title("Throughput by Packet Size", fontweight='bold', fontsize=14)
    else:
        ax2.text(0.5, 0.5, 'No Throughput Data', ha='center', va='center')
        ax2.set_title("Throughput by Packet Size", fontweight='bold', fontsize=14)
    
    # 3. Performance Metrics Dashboard
    ax3 = fig.add_subplot(gs[0, 2])
    metric_names = ["Avg. Latency", "Avg. Jitter", "Avg. Throughput", "Packet Delivery", "Avg. RTT"]
    metric_values = [
        metrics["latency"]["average"] if metrics["latency"]["average"] is not None else 0,
        metrics["jitter"]["average"] if metrics["jitter"]["average"] is not None else 0,
        metrics["throughput"]["average"] if metrics["throughput"]["average"] is not None else 0,
        metrics["packet_delivery_ratio"]["ratio"] * 100 if metrics["packet_delivery_ratio"]["ratio"] is not None else 0,
        metrics["round_trip_time"]["average"] if metrics["round_trip_time"]["average"] is not None else 0
    ]
    units = ["ms", "ms", "Mbps", "%", "ms"]
    
    max_value = max(metric_values) if metric_values else 1
    ax3.set_xlim(0, max_value * 1.2)
    
    bars = ax3.barh(metric_names, metric_values, color=main_colors)
    ax3.set_xlabel("Value")
    for i, (val, unit) in enumerate(zip(metric_values, units)):
        text_color = 'black' if val < max_value * 0.3 else 'white'
        ax3.text(val + (max_value * 0.05), i, 
                f"{val:.2f} {unit}", 
                va='center', color=text_color)
    ax3.set_title("Performance Summary", fontweight='bold', fontsize=14)
    
    # 4. Jitter vs. Latency Scatter
    ax4 = fig.add_subplot(gs[1, 0])
    jitter_values = metrics["jitter"]["values"]
    latency_values = metrics["latency"]["values"][:len(jitter_values)]
    
    if jitter_values and latency_values:
        sns.scatterplot(x=latency_values, y=jitter_values, alpha=0.6, 
                       color=main_colors[4], ax=ax4)
        ax4.set_xlabel("Latency (ms)")
        ax4.set_ylabel("Jitter (ms)")
        ax4.set_title("Jitter vs. Latency", fontweight='bold', fontsize=14)
    else:
        ax4.text(0.5, 0.5, 'No Jitter/Latency Data', ha='center', va='center')
        ax4.set_title("Jitter vs. Latency", fontweight='bold', fontsize=14)
    
    # 5. Packet Delivery
    ax5 = fig.add_subplot(gs[1, 1])
    total_sent = metrics["packet_delivery_ratio"]["total_sent"]
    delivered = metrics["packet_delivery_ratio"]["total_received"]
    lost = total_sent - delivered
    
    if total_sent > 0:
        ax5.bar(['Packets'], [delivered], label='Delivered', color=main_colors[1])
        ax5.bar(['Packets'], [lost], bottom=[delivered], label='Lost', color=main_colors[2])
        delivered_pct = (delivered / total_sent) * 100
        ax5.annotate(f'{delivered_pct:.1f}%', xy=('Packets', delivered/2),
                    ha='center', va='center', color='white', fontweight='bold')
        ax5.set_ylabel("Packet Count")
        ax5.legend()
    else:
        ax5.text(0.5, 0.5, 'No Packet Data', ha='center', va='center')
    ax5.set_title("Packet Delivery", fontweight='bold', fontsize=14)
    
    # 6. Flow Management
    ax6 = fig.add_subplot(gs[1, 2])
    flow_counts = metrics["scalability"]["concurrent_flows"]
    setup_times = metrics["scalability"]["flow_setup_times"]
    
    if flow_counts and setup_times:
        sorted_data = sorted(zip(flow_counts, setup_times), key=lambda x: x[0])
        flow_counts, setup_times = zip(*sorted_data) if sorted_data else ([], [])
        
        ax6.plot(flow_counts, setup_times, 'o-', color=main_colors[0], linewidth=2)
        ax6.set_xlabel("Number of Flows")
        ax6.set_ylabel("Setup Time (s)")
        for count, time in zip(flow_counts, setup_times):
            ax6.annotate(f"{time:.3f}s", 
                        xy=(count, time), 
                        xytext=(5, 5), 
                        textcoords='offset points')
        ax6.set_title("Flow Setup Performance", fontweight='bold', fontsize=14)
    else:
        ax6.text(0.5, 0.5, 'No Flow Data', ha='center', va='center')
        ax6.set_title("Flow Setup Performance", fontweight='bold', fontsize=14)
    
    # 7. Flow Control Metrics
    ax7 = fig.add_subplot(gs[2, 0])
    flow_metrics = [
        ("Sent", metrics["flow"]["sent_packets"]),
        ("Received", metrics["flow"]["received_packets"]),
        ("ACKs", metrics["flow"]["ack_packets"]),
        ("Retransmits", metrics["flow"]["retransmitted_packets"])
    ]
    
    labels = [m[0] for m in flow_metrics]
    values = [m[1] if m[1] is not None else 0 for m in flow_metrics]
    
    if any(values):
        bars = ax7.bar(labels, values, color=main_colors[:len(labels)])
        ax7.set_title("Flow Control Performance", fontweight='bold', fontsize=14)
        ax7.set_ylabel("Packet Count")
        
        for bar in bars:
            height = bar.get_height()
            ax7.annotate(f'{int(height)}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')
    else:
        ax7.text(0.5, 0.5, 'No Flow Control Data', ha='center', va='center')
        ax7.set_title("Flow Control Performance", fontweight='bold', fontsize=14)
    
    # Add figure title and adjust layout
    fig.suptitle("RINA Network Performance Analysis", fontsize=20, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])  # Adjusted bottom margin
    
    # Save outputs
    output_path = Path("visualizations")
    output_path.mkdir(exist_ok=True)
    plt.savefig(output_path/"rina_metrics.png", dpi=300, bbox_inches='tight')
    plt.savefig(output_path/"rina_metrics.svg", format='svg', bbox_inches='tight')
    print(f"Visualization saved to {output_path}/rina_metrics.[png/svg]")

def export_to_csv(metrics):
    """Export the metrics to CSV files for easier analysis and sharing"""
    output_path = Path("visualizations")
    output_path.mkdir(exist_ok=True)
    
    # Create dataframes for different metric types
    
    # 1. Latency and Jitter metrics
    if metrics["latency"]["values"] and metrics["jitter"]["values"]:
        latency_jitter_df = pd.DataFrame({
            "latency_ms": metrics["latency"]["values"],
            "jitter_ms": metrics["jitter"]["values"] + [None] * (len(metrics["latency"]["values"]) - len(metrics["jitter"]["values"]))
        })
        latency_jitter_df.to_csv(output_path/"latency_jitter.csv", index=False)
    
    # 2. Throughput by packet size
    if metrics["throughput"]["by_size"]:
        throughput_df = pd.DataFrame({
            "packet_size_bytes": [int(size) for size in metrics["throughput"]["by_size"].keys()],
            "throughput_mbps": list(metrics["throughput"]["by_size"].values())
        })
        throughput_df.to_csv(output_path/"throughput_by_size.csv", index=False)
    
    # 3. Packet delivery ratio
    if metrics["packet_delivery_ratio"]["by_packet_count"]:
        pdr_df = pd.DataFrame({
            "packet_count": [int(count) for count in metrics["packet_delivery_ratio"]["by_packet_count"].keys()],
            "delivery_ratio_percent": list(metrics["packet_delivery_ratio"]["by_packet_count"].values())
        })
        pdr_df.to_csv(output_path/"packet_delivery_ratio.csv", index=False)
    
    # 4. Network load impact
    if metrics["packet_delivery_ratio"]["by_network_load"]:
        load_df = pd.DataFrame({
            "concurrent_flows": [int(load) for load in metrics["packet_delivery_ratio"]["by_network_load"].keys()],
            "delivery_ratio_percent": list(metrics["packet_delivery_ratio"]["by_network_load"].values())
        })
        load_df.to_csv(output_path/"network_load_impact.csv", index=False)
    
    # 5. Round trip time by packet size
    if metrics["round_trip_time"]["by_packet_size"]:
        rtt_data = []
        for size, data in metrics["round_trip_time"]["by_packet_size"].items():
            rtt_data.append({
                "packet_size_bytes": int(size),
                "avg_rtt_ms": data["avg"],
                "min_rtt_ms": data["min"],
                "max_rtt_ms": data["max"],
                "median_rtt_ms": data["median"]
            })
        rtt_df = pd.DataFrame(rtt_data)
        rtt_df.to_csv(output_path/"round_trip_time.csv", index=False)
    
    # 6. Flow control metrics
    if metrics["flow"]["sent_packets"] is not None:
        flow_data = {
            "metric": ["sent_packets", "received_packets", "ack_packets", "retransmitted_packets", 
                      "window_efficiency", "packet_loss_rate"],
            "value": [
                metrics["flow"]["sent_packets"],
                metrics["flow"]["received_packets"],
                metrics["flow"]["ack_packets"],
                metrics["flow"]["retransmitted_packets"],
                metrics["flow"]["window_efficiency"],
                metrics["flow"]["packet_loss_rate"]
            ]
        }
        flow_df = pd.DataFrame(flow_data)
        flow_df.to_csv(output_path/"flow_control.csv", index=False)
    
    
    # 9. Summary metrics file
    summary_data = {
        "metric": [
            "avg_latency_ms", "min_latency_ms", "max_latency_ms", "p95_latency_ms", "p99_latency_ms",
            "avg_jitter_ms", "max_jitter_ms", 
            "avg_throughput_mbps", 
            "packet_delivery_ratio_percent",
            "avg_rtt_ms",
            "max_concurrent_flows",
            "avg_flow_setup_time_seconds",
            "window_efficiency_percent",
            "packet_loss_rate_percent",
        ],
        "value": [
            metrics["latency"]["average"],
            metrics["latency"]["min"],
            metrics["latency"]["max"],
            metrics["latency"]["percentile_95"],
            metrics["latency"]["percentile_99"],
            metrics["jitter"]["average"],
            metrics["jitter"]["max"],
            metrics["throughput"]["average"],
            metrics["packet_delivery_ratio"]["ratio"] * 100 if metrics["packet_delivery_ratio"]["ratio"] is not None else None,
            metrics["round_trip_time"]["average"],
            metrics["scalability"]["max_concurrent_flows"],
            metrics["scalability"]["avg_flow_setup_time"],
            metrics["flow"]["window_efficiency"],
            metrics["flow"]["packet_loss_rate"],
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(output_path/"summary_metrics.csv", index=False)
    
    print(f"CSV data exported to {output_path}/ directory")

if __name__ == "__main__":
    main()