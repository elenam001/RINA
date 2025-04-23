import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np
from pathlib import Path

def load_metrics(file_path="metrics.json"):
    """Load metrics from the JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def ensure_output_dir(directory="visualization_output"):
    """Ensure the output directory exists"""
    Path(directory).mkdir(exist_ok=True)
    return directory

def save_plot(fig, filename, directory="visualization_output"):
    """Save a figure to the output directory"""
    plt.tight_layout()
    fig.savefig(os.path.join(directory, filename), dpi=300, bbox_inches='tight')
    plt.close(fig)

def visualize_throughput(metrics, output_dir):
    """Visualize throughput metrics"""
    throughput_data = metrics.get("throughput_realistic_networks", {})
    if not throughput_data:
        print("No throughput data found")
        return
    
    # Create dataframe for plotting
    rows = []
    for profile, profile_data in throughput_data.items():
        for packet_size, metrics in profile_data.items():
            rows.append({
                "Profile": profile,
                "Packet Size (bytes)": int(packet_size),
                "Throughput (Mbps)": metrics["throughput_mbps"],
                "Packets per Second": metrics["packets_per_second"]
            })
    
    df = pd.DataFrame(rows)
    
    # Save as CSV
    df.to_csv(os.path.join(output_dir, "throughput_summary.csv"), index=False)
    
    # Create throughput vs packet size plot
    plt.figure(figsize=(12, 8))
    sns.lineplot(data=df, x="Packet Size (bytes)", y="Throughput (Mbps)", 
                hue="Profile", marker='o', linewidth=2)
    plt.xscale('log')
    plt.grid(True, alpha=0.3)
    plt.title("Throughput vs Packet Size Across Network Profiles")
    plt.savefig(os.path.join(output_dir, "throughput_vs_packet_size.png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    # Create bar plot for different profiles
    fig, ax = plt.subplots(figsize=(14, 8))
    pivot_df = df.pivot(index="Packet Size (bytes)", columns="Profile", values="Throughput (Mbps)")
    pivot_df.plot(kind='bar', ax=ax)
    plt.grid(True, alpha=0.3)
    plt.title("Throughput Comparison by Network Profile")
    plt.ylabel("Throughput (Mbps)")
    plt.xticks(rotation=45)
    plt.savefig(os.path.join(output_dir, "throughput_by_profile.png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    # Create packets per second vs packet size plot
    plt.figure(figsize=(12, 8))
    sns.lineplot(data=df, x="Packet Size (bytes)", y="Packets per Second", 
                hue="Profile", marker='o', linewidth=2)
    plt.xscale('log')
    plt.yscale('log')
    plt.grid(True, alpha=0.3)
    plt.title("Packets per Second vs Packet Size")
    plt.savefig(os.path.join(output_dir, "pps_vs_packet_size.png"), dpi=300, bbox_inches='tight')
    plt.close()

def visualize_latency_jitter(metrics, output_dir):
    """Visualize latency and jitter metrics"""
    latency_data = metrics.get("latency_jitter_realistic", {})
    if not latency_data:
        print("No latency data found")
        return
    
    # Create dataframe for plotting
    rows = []
    for profile, profile_data in latency_data.items():
        for packet_size, metrics in profile_data.items():
            rows.append({
                "Profile": profile,
                "Packet Size (bytes)": int(packet_size),
                "Avg Latency (ms)": metrics["avg_latency_ms"],
                "Min Latency (ms)": metrics["min_latency_ms"],
                "Max Latency (ms)": metrics["max_latency_ms"],
                "Avg Jitter (ms)": metrics["avg_jitter_ms"],
                "Max Jitter (ms)": metrics["max_jitter_ms"]
            })
    
    df = pd.DataFrame(rows)
    
    # Save as CSV
    df.to_csv(os.path.join(output_dir, "latency_jitter_summary.csv"), index=False)
    
    # Create latency vs packet size plot
    plt.figure(figsize=(12, 8))
    sns.lineplot(data=df, x="Packet Size (bytes)", y="Avg Latency (ms)", 
                hue="Profile", marker='o', linewidth=2)
    plt.grid(True, alpha=0.3)
    plt.title("Average Latency vs Packet Size")
    plt.savefig(os.path.join(output_dir, "latency_vs_packet_size.png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    # Create jitter vs packet size plot
    plt.figure(figsize=(12, 8))
    sns.lineplot(data=df, x="Packet Size (bytes)", y="Avg Jitter (ms)", 
                hue="Profile", marker='o', linewidth=2)
    plt.grid(True, alpha=0.3)
    plt.title("Average Jitter vs Packet Size")
    plt.savefig(os.path.join(output_dir, "jitter_vs_packet_size.png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    # Create profile comparison for latency
    fig, ax = plt.subplots(figsize=(14, 8))
    pivot_df = df.pivot(index="Packet Size (bytes)", columns="Profile", values="Avg Latency (ms)")
    pivot_df.plot(kind='bar', ax=ax)
    plt.grid(True, alpha=0.3)
    plt.title("Average Latency Comparison by Network Profile")
    plt.ylabel("Latency (ms)")
    plt.xticks(rotation=45)
    plt.savefig(os.path.join(output_dir, "latency_by_profile.png"), dpi=300, bbox_inches='tight')
    plt.close()

def visualize_packet_delivery_ratio(metrics, output_dir):
    """Visualize packet delivery ratio metrics"""
    pdr_data = metrics.get("packet_delivery_ratio_realistic", {})
    if not pdr_data:
        print("No packet delivery ratio data found")
        return
    
    # Create dataframe for plotting
    rows = []
    for profile, profile_data in pdr_data.items():
        for packet_size, metrics in profile_data.items():
            rows.append({
                "Profile": profile,
                "Packet Size (bytes)": int(packet_size),
                "Sent Packets": metrics["sent"],
                "Received Packets": metrics["received"],
                "Delivery Ratio (%)": metrics["delivery_ratio"]
            })
    
    df = pd.DataFrame(rows)
    
    # Save as CSV
    df.to_csv(os.path.join(output_dir, "pdr_summary.csv"), index=False)
    
    # Create packet delivery ratio vs packet size plot
    plt.figure(figsize=(12, 8))
    sns.lineplot(data=df, x="Packet Size (bytes)", y="Delivery Ratio (%)", 
                hue="Profile", marker='o', linewidth=2)
    plt.grid(True, alpha=0.3)
    plt.title("Packet Delivery Ratio vs Packet Size")
    plt.savefig(os.path.join(output_dir, "pdr_vs_packet_size.png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    # Create bar plot for different profiles
    fig, ax = plt.subplots(figsize=(14, 8))
    pivot_df = df.pivot(index="Packet Size (bytes)", columns="Profile", values="Delivery Ratio (%)")
    pivot_df.plot(kind='bar', ax=ax)
    plt.grid(True, alpha=0.3)
    plt.title("Packet Delivery Ratio Comparison by Network Profile")
    plt.ylabel("Delivery Ratio (%)")
    plt.xticks(rotation=45)
    plt.savefig(os.path.join(output_dir, "pdr_by_profile.png"), dpi=300, bbox_inches='tight')
    plt.close()

def visualize_rtt(metrics, output_dir):
    """Visualize round trip time metrics"""
    rtt_data = metrics.get("round_trip_time_realistic", {})
    if not rtt_data:
        print("No RTT data found")
        return
    
    # Create dataframe for plotting
    rows = []
    for profile, profile_data in rtt_data.items():
        for packet_size, metrics in profile_data.items():
            rows.append({
                "Profile": profile,
                "Packet Size (bytes)": int(packet_size),
                "Avg RTT (ms)": metrics["avg_rtt_ms"],
                "Min RTT (ms)": metrics["min_rtt_ms"],
                "Max RTT (ms)": metrics["max_rtt_ms"]
            })
    
    df = pd.DataFrame(rows)
    
    # Save as CSV
    df.to_csv(os.path.join(output_dir, "rtt_summary.csv"), index=False)
    
    # Create RTT vs packet size plot
    plt.figure(figsize=(12, 8))
    sns.lineplot(data=df, x="Packet Size (bytes)", y="Avg RTT (ms)", 
                hue="Profile", marker='o', linewidth=2)
    plt.grid(True, alpha=0.3)
    plt.title("Average Round Trip Time vs Packet Size")
    plt.savefig(os.path.join(output_dir, "rtt_vs_packet_size.png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    # Create min/avg/max RTT plot for each profile
    for profile in df["Profile"].unique():
        profile_df = df[df["Profile"] == profile]
        plt.figure(figsize=(12, 8))
        
        plt.plot(profile_df["Packet Size (bytes)"], profile_df["Min RTT (ms)"], 
                marker='o', label="Min RTT")
        plt.plot(profile_df["Packet Size (bytes)"], profile_df["Avg RTT (ms)"], 
                marker='s', label="Avg RTT")
        plt.plot(profile_df["Packet Size (bytes)"], profile_df["Max RTT (ms)"], 
                marker='^', label="Max RTT")
        
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.title(f"RTT Analysis for {profile} Profile")
        plt.xlabel("Packet Size (bytes)")
        plt.ylabel("RTT (ms)")
        plt.savefig(os.path.join(output_dir, f"rtt_analysis_{profile}.png"), dpi=300, bbox_inches='tight')
        plt.close()

def visualize_scalability(metrics, output_dir):
    """Visualize scalability metrics"""
    scaling_data = metrics.get("scalability_concurrent_flows", {})
    if not scaling_data:
        print("No scalability data found")
        return
    
    # Create dataframe for plotting
    rows = []
    for profile, profile_data in scaling_data.items():
        for flow_count, metrics in profile_data.items():
            rows.append({
                "Profile": profile,
                "Target Flow Count": metrics["target_flows"],
                "Successful Flows": metrics["successful_flows"],
                "Success Rate (%)": (metrics["successful_flows"] / metrics["target_flows"]) * 100,
                "Allocation Time (s)": metrics["allocation_time_seconds"],
                "Time per Flow (ms)": metrics["allocation_time_per_flow_ms"],
                "Data Send Success (%)": metrics["data_send_success_rate"],
                "Bandwidth per Flow (Mbps)": metrics["bandwidth_per_flow_mbps"]
            })
    
    df = pd.DataFrame(rows)
    
    # Save as CSV
    df.to_csv(os.path.join(output_dir, "scalability_summary.csv"), index=False)
    
    # Create flow success rate plot
    plt.figure(figsize=(12, 8))
    sns.lineplot(data=df, x="Target Flow Count", y="Success Rate (%)", 
                hue="Profile", marker='o', linewidth=2)
    plt.grid(True, alpha=0.3)
    plt.title("Flow Allocation Success Rate vs Target Flow Count")
    plt.savefig(os.path.join(output_dir, "flow_success_rate.png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    # Create allocation time plot
    plt.figure(figsize=(12, 8))
    sns.lineplot(data=df, x="Target Flow Count", y="Time per Flow (ms)", 
                hue="Profile", marker='o', linewidth=2)
    plt.grid(True, alpha=0.3)
    plt.title("Allocation Time per Flow vs Target Flow Count")
    plt.savefig(os.path.join(output_dir, "allocation_time_per_flow.png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    # Create data send success plot
    plt.figure(figsize=(12, 8))
    sns.lineplot(data=df, x="Target Flow Count", y="Data Send Success (%)", 
                hue="Profile", marker='o', linewidth=2)
    plt.grid(True, alpha=0.3)
    plt.title("Data Send Success Rate vs Target Flow Count")
    plt.savefig(os.path.join(output_dir, "data_send_success.png"), dpi=300, bbox_inches='tight')
    plt.close()

def create_comprehensive_summary(metrics, output_dir):
    """Create a comprehensive summary across all metrics"""
    # Extract data from different metrics
    throughput_data = metrics.get("throughput_realistic_networks", {})
    latency_data = metrics.get("latency_jitter_realistic", {})
    pdr_data = metrics.get("packet_delivery_ratio_realistic", {})
    rtt_data = metrics.get("round_trip_time_realistic", {})
    
    # Create a unified dataframe for network profiles
    profiles = set()
    packet_sizes = set()
    
    for data_source in [throughput_data, latency_data, pdr_data, rtt_data]:
        for profile in data_source:
            profiles.add(profile)
            for packet_size in data_source[profile]:
                packet_sizes.add(int(packet_size))
    
    # Create rows with available data
    rows = []
    for profile in sorted(profiles):
        for packet_size in sorted(packet_sizes):
            str_packet_size = str(packet_size)
            
            row = {
                "Profile": profile,
                "Packet Size (bytes)": packet_size
            }
            
            # Add throughput data if available
            if profile in throughput_data and str_packet_size in throughput_data[profile]:
                row["Throughput (Mbps)"] = throughput_data[profile][str_packet_size]["throughput_mbps"]
                row["Packets per Second"] = throughput_data[profile][str_packet_size]["packets_per_second"]
            
            # Add latency/jitter data if available
            if profile in latency_data and str_packet_size in latency_data[profile]:
                row["Avg Latency (ms)"] = latency_data[profile][str_packet_size]["avg_latency_ms"]
                row["Avg Jitter (ms)"] = latency_data[profile][str_packet_size]["avg_jitter_ms"]
            
            # Add PDR data if available
            if profile in pdr_data and str_packet_size in pdr_data[profile]:
                row["Delivery Ratio (%)"] = pdr_data[profile][str_packet_size]["delivery_ratio"]
            
            # Add RTT data if available
            if profile in rtt_data and str_packet_size in rtt_data[profile]:
                row["Avg RTT (ms)"] = rtt_data[profile][str_packet_size]["avg_rtt_ms"]
            
            rows.append(row)
    
    # Create and save the comprehensive summary
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(output_dir, "comprehensive_network_summary.csv"), index=False)
    
    # Create correlation analysis if enough data is available
    try:
        # Drop rows with missing values for correlation analysis
        complete_df = df.dropna()
        if len(complete_df) > 5:  # Only if we have enough data points
            correlation = complete_df.select_dtypes(include=[np.number]).corr()
            plt.figure(figsize=(14, 12))
            sns.heatmap(correlation, annot=True, cmap='coolwarm', vmin=-1, vmax=1)
            plt.title("Correlation Between Network Metrics")
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "metrics_correlation.png"), dpi=300)
            plt.close()
            
            # Save correlation matrix
            correlation.to_csv(os.path.join(output_dir, "metrics_correlation.csv"))
    except:
        print("Could not create correlation analysis due to insufficient or incompatible data")

def main():
    # Load metrics from JSON file
    try:
        metrics = load_metrics()
        print("Metrics loaded successfully")
    except Exception as e:
        print(f"Error loading metrics: {e}")
        return
    
    # Create output directory
    output_dir = ensure_output_dir()
    print(f"Output will be saved to {output_dir}")
    
    # Create visualizations
    visualize_throughput(metrics, output_dir)
    visualize_latency_jitter(metrics, output_dir)
    visualize_packet_delivery_ratio(metrics, output_dir)
    visualize_rtt(metrics, output_dir)
    visualize_scalability(metrics, output_dir)
    
    # Create comprehensive summary
    create_comprehensive_summary(metrics, output_dir)
    
    print(f"Visualization complete. Results saved to {output_dir}")

if __name__ == "__main__":
    # Set visual style for plots
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (12, 8)
    plt.rcParams['axes.labelsize'] = 12
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['xtick.labelsize'] = 10
    plt.rcParams['ytick.labelsize'] = 10
    
    main()