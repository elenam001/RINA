import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from pathlib import Path
from matplotlib.colors import LinearSegmentedColormap

def main():
    # Set the style for better aesthetics
    plt.style.use('ggplot')
    sns.set_context("talk")
    
    # Load metrics from JSON file
    with open("metrics.json", "r") as f:
        metrics = json.load(f)
    
    # Create a figure with custom grid layout
    fig = plt.figure(figsize=(20, 16))
    gs = gridspec.GridSpec(3, 4, figure=fig)
    
    # Define custom color palettes
    main_colors = ["#3498db", "#2ecc71", "#e74c3c", "#f39c12", "#9b59b6"]
    cmap_blue = LinearSegmentedColormap.from_list("", ["#d4e6f1", "#3498db", "#1a5276"])
    
    # 1. Latency Distribution - Upper Left
    ax1 = fig.add_subplot(gs[0, 0:2])
    sns.histplot(metrics["latency"]["values"], bins=20, kde=True, color=main_colors[0], ax=ax1)
    ax1.axvline(metrics["latency"]["average"], color=main_colors[2], linestyle='dashed', linewidth=2, 
                label=f'Mean: {metrics["latency"]["average"]:.2f}ms')
    ax1.axvline(metrics["latency"]["percentile_95"], color=main_colors[3], linestyle='dashed', linewidth=2,
               label=f'P95: {metrics["latency"]["percentile_95"]:.2f}ms')
    ax1.set_title("Latency Distribution", fontweight='bold', fontsize=14)
    ax1.set_xlabel("Latency (ms)")
    ax1.set_ylabel("Frequency")
    ax1.legend()
    
    # 2. Throughput by packet size - Upper Right
    ax2 = fig.add_subplot(gs[0, 2:4])
    sizes = sorted([int(s) for s in metrics["throughput"]["by_size"].keys()])
    values = [metrics["throughput"]["by_size"][str(s)] for s in sizes]
    
    bars = ax2.bar(range(len(sizes)), values, color=main_colors[1])
    ax2.set_xticks(range(len(sizes)))
    ax2.set_xticklabels([f"{s} bytes" for s in sizes])
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax2.annotate(f'{height:.1f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')
    
    ax2.set_title("Throughput by Packet Size", fontweight='bold', fontsize=14)
    ax2.set_xlabel("Packet Size")
    ax2.set_ylabel("Throughput (Mbps)")
    
    # 3. Performance Metrics Dashboard - Middle Left
    ax3 = fig.add_subplot(gs[1, 0:2])
    metric_names = ["Avg. Latency", "Avg. Jitter", "Avg. Throughput", "Packet Delivery", "Avg. RTT"]
    metric_values = [
        metrics["latency"]["average"],
        metrics["jitter"]["average"],
        metrics["throughput"]["average"],
        metrics["packet_delivery_ratio"]["ratio"],
        metrics["round_trip_time"]["average"]
    ]
    
    # Normalize values for consistent bar heights
    norm_values = []
    units = ["ms", "ms", "Mbps", "%", "ms"]
    norm_factors = [50, 20, 10, 1, 50]  # Normalize to approximately same scale
    
    for val, factor in zip(metric_values, norm_factors):
        norm_values.append(val / factor)
    
    bars = ax3.barh(metric_names, norm_values, color=main_colors)
    
    # Add actual values as text
    for i, (val, unit) in enumerate(zip(metric_values, units)):
        ax3.text(norm_values[i] + 0.1, i, f"{val:.2f} {unit}", va='center')
    
    ax3.set_title("Performance Metrics Summary", fontweight='bold', fontsize=14)
    ax3.set_xlabel("Normalized Scale")
    ax3.set_xlim(0, max(norm_values) * 1.2)
    ax3.spines['top'].set_visible(False)
    ax3.spines['right'].set_visible(False)
    
    # 4. Jitter vs. Latency Scatter - Middle Right
    ax4 = fig.add_subplot(gs[1, 2:4])
    
    # Create pairs of jitter and latency values
    jitter_values = metrics["jitter"]["values"]
    latency_values = metrics["latency"]["values"][:len(jitter_values)]  # Match lengths
    
    sns.scatterplot(x=latency_values, y=jitter_values, alpha=0.6, color=main_colors[4], ax=ax4)
    ax4.set_title("Jitter vs. Latency Relationship", fontweight='bold', fontsize=14)
    ax4.set_xlabel("Latency (ms)")
    ax4.set_ylabel("Jitter (ms)")
    
    # Add a trend line
    if len(jitter_values) > 1:
        z = np.polyfit(latency_values, jitter_values, 1)
        p = np.poly1d(z)
        ax4.plot(sorted(latency_values), p(sorted(latency_values)), 
                 linestyle="--", color=main_colors[2], linewidth=2)
    
    # 5. QoS Compliance - Bottom Left
    ax5 = fig.add_subplot(gs[2, 0])
    labels = ['Compliant', 'Latency\nViolations', 'Bandwidth\nViolations']
    
    # Handle potential division by zero
    total_tests = len(metrics["qos"]["tests"]) if metrics["qos"]["tests"] else 1
    violations = [
        metrics["qos"]["compliance_rate"]/100, 
        metrics["qos"]["latency_violations"]/total_tests, 
        metrics["qos"]["bandwidth_violations"]/total_tests
    ]
    
    wedges, texts, autotexts = ax5.pie(
        violations, 
        labels=labels, 
        autopct='%1.1f%%',
        colors=[main_colors[1], main_colors[2], main_colors[3]],
        startangle=90,
        wedgeprops={'width': 0.5, 'edgecolor': 'w', 'linewidth': 2}
    )
    
    # Make the pie chart look better
    for text in texts:
        text.set_fontsize(10)
    for autotext in autotexts:
        autotext.set_fontsize(10)
        autotext.set_fontweight('bold')
    
    ax5.set_title("QoS Compliance", fontweight='bold', fontsize=14)
    
    # 6. Packet Delivery Visualization - Bottom Middle-Left
    ax6 = fig.add_subplot(gs[2, 1])
    delivered = metrics["packet_delivery_ratio"]["total_received"]
    lost = metrics["packet_delivery_ratio"]["total_sent"] - delivered
    
    # Create a more interesting packet visualization
    ax6.bar(['Packets'], [delivered], label='Delivered', color=main_colors[1])
    ax6.bar(['Packets'], [lost], bottom=[delivered], label='Lost', color=main_colors[2])
    
    # Annotate with percentages
    total = delivered + lost
    if total > 0:  # Avoid division by zero
        delivered_pct = (delivered / total) * 100
        lost_pct = (lost / total) * 100
        
        ax6.annotate(f'{delivered_pct:.1f}%\n({delivered} pkts)',
                    xy=('Packets', delivered/2),
                    ha='center', va='center', color='white', fontweight='bold')
        
        if lost > 0:
            ax6.annotate(f'{lost_pct:.1f}%\n({lost} pkts)',
                        xy=('Packets', delivered + lost/2),
                        ha='center', va='center', color='white', fontweight='bold')
    
    ax6.set_title("Packet Delivery", fontweight='bold', fontsize=14)
    ax6.legend(loc='upper right')
    ax6.set_ylim(0, total * 1.1)
    
    # 7. Flow Management - Bottom Middle-Right
    ax7 = fig.add_subplot(gs[2, 2])
    
    flow_counts = metrics["scalability"]["concurrent_flows"]
    setup_times = metrics["scalability"]["flow_setup_times"]
    
    ax7.plot(flow_counts, setup_times, 'o-', color=main_colors[0], linewidth=2, markersize=8)
    
    for i, (count, time) in enumerate(zip(flow_counts, setup_times)):
        ax7.annotate(f"{time:.3f}s",
                    xy=(count, time),
                    xytext=(5, 5),
                    textcoords="offset points")
    
    ax7.set_title("Flow Setup Performance", fontweight='bold', fontsize=14)
    ax7.set_xlabel("Number of Concurrent Flows")
    ax7.set_ylabel("Setup Time (seconds)")
    ax7.grid(True, linestyle='--', alpha=0.7)
    
    # 8. Bandwidth Utilization - Bottom Right
    ax8 = fig.add_subplot(gs[2, 3])
    
    targets = [int(entry["target"]) for entry in metrics["resource_utilization"]["bandwidth_usage"]]
    achieved = [entry["achieved"] for entry in metrics["resource_utilization"]["bandwidth_usage"]]
    utilization = [entry["utilization"] for entry in metrics["resource_utilization"]["bandwidth_usage"]]
    
    width = 0.35
    x = np.arange(len(targets))
    
    ax8.bar(x - width/2, [t for t in targets], width, label='Target', color='lightgray', edgecolor='gray')
    ax8.bar(x + width/2, achieved, width, label='Achieved', color=main_colors[0], edgecolor='darkblue')
    
    # Add utilization percentages
    for i, (target, achieved, util) in enumerate(zip(targets, achieved, utilization)):
        ax8.annotate(f"{util:.1f}%",
                    xy=(i, max(target, achieved)),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center')
    
    ax8.set_title("Bandwidth Utilization", fontweight='bold', fontsize=14)
    ax8.set_xlabel("Target Bandwidth (Mbps)")
    ax8.set_ylabel("Bandwidth (Mbps)")
    ax8.set_xticks(x)
    ax8.set_xticklabels(targets)
    ax8.legend()
    
    # Add a title to the entire figure
    fig.suptitle("RINA Network Performance Analysis", fontsize=20, fontweight='bold', y=0.98)
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Save high-resolution image
    plt.savefig("enhanced_rina_metrics.png", dpi=300, bbox_inches='tight')
    
    # Also save in vector format for high-quality printing or publications
    plt.savefig("enhanced_rina_metrics.svg", format='svg', bbox_inches='tight')
    
    print("Enhanced visualization saved to enhanced_rina_metrics.png and enhanced_rina_metrics.svg")

if __name__ == "__main__":
    main()