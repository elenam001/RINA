import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)

def load_metrics():
    with open("hybrid_metrics.json") as f:
        return json.load(f)

def create_csv(metrics):
    rows = []
    
    for network_type in ["rina", "tcp", "hybrid"]:
        # Latency
        for size, values in metrics[network_type]["latency"].items():
            rows.append({
                "network_type": network_type,
                "metric": "latency",
                "parameter": f"size_{size}",
                "avg": values["avg_latency"],
                "min": values["min_latency"],
                "max": values["max_latency"],
                "jitter": values["avg_jitter"]
            })
        
        # Throughput
        for size, value in metrics[network_type]["throughput"].items():
            if isinstance(value, dict):
                continue  # Skip nested metrics
            rows.append({
                "network_type": network_type,
                "metric": "throughput",
                "parameter": f"size_{size}",
                "value": value
            })
            
        # Sustained Throughput
        if "sustained" in metrics[network_type]["throughput"]:
            sustained = metrics[network_type]["throughput"]["sustained"]
            rows.append({
                "network_type": network_type,
                "metric": "sustained_throughput",
                "parameter": "overall",
                "avg": sustained["average"],
                "min": sustained["min"],
                "max": sustained["max"]
            })
            
        # Packet Delivery Ratio
        for param, value in metrics[network_type]["packet_delivery_ratio"].items():
            if isinstance(value, dict):
                continue
            rows.append({
                "network_type": network_type,
                "metric": "packet_delivery_ratio",
                "parameter": param,
                "value": value
            })
            
        # Flow Control
        if "flow_control" in metrics[network_type]:
            for key, value in metrics[network_type]["flow_control"].items():
                if isinstance(value, dict):
                    continue
                rows.append({
                    "network_type": network_type,
                    "metric": f"flow_control_{key}",
                    "parameter": "overall",
                    "value": value
                })
    
    df = pd.DataFrame(rows)
    df.to_csv("network_metrics.csv", index=False)
    return df

def plot_throughput(metrics):
    fig, ax = plt.subplots()
    for network_type in ["rina", "tcp", "hybrid"]:
        throughput = metrics[network_type]["throughput"]
        sizes = [k for k in throughput.keys() if not isinstance(throughput[k], dict)]
        values = [throughput[k] for k in sizes]
        ax.plot(sizes, values, marker='o', label=network_type.upper())
    
    ax.set_title("Throughput by Packet Size")
    ax.set_xlabel("Packet Size (bytes)")
    ax.set_ylabel("Throughput (Mbps)")
    ax.legend()
    plt.savefig("throughput_by_size.png")
    plt.close()

def plot_latency(metrics):
    fig, ax = plt.subplots()
    for network_type in ["rina", "tcp", "hybrid"]:
        latencies = []
        sizes = []
        for size, values in metrics[network_type]["latency"].items():
            latencies.append(values["avg_latency"])
            sizes.append(int(size))
        
        ax.plot(sizes, latencies, marker='o', label=network_type.upper())
    
    ax.set_title("Average Latency by Packet Size")
    ax.set_xlabel("Packet Size (bytes)")
    ax.set_ylabel("Latency (ms)")
    ax.legend()
    plt.savefig("latency_by_size.png")
    plt.close()

# Updated plot_pdr function in visualize_metrics.py
def plot_pdr(metrics):
    fig, ax = plt.subplots()
    
    # Collect all unique parameters across all network types
    all_params = set()
    for net_type in ["rina", "tcp", "hybrid"]:
        all_params.update(metrics[net_type]["packet_delivery_ratio"].keys())
    all_params = sorted(all_params, key=lambda x: int(x.split('_')[-1]) if x.startswith('load_') else int(x))
    
    width = 0.25
    x = range(len(all_params))
    
    for i, network_type in enumerate(["rina", "tcp", "hybrid"]):
        pdr_values = []
        for param in all_params:
            # Get value if exists, else None
            pdr_values.append(metrics[network_type]["packet_delivery_ratio"].get(param, 0))
        
        ax.bar([pos + i*width for pos in x], pdr_values, width, label=network_type.upper())
    
    ax.set_title("Packet Delivery Ratio Comparison")
    ax.set_xlabel("Test Scenario")
    ax.set_ylabel("Delivery Ratio (%)")
    ax.set_xticks([pos + width for pos in x])
    ax.set_xticklabels(all_params, rotation=45, ha='right')
    ax.legend()
    plt.tight_layout()
    plt.savefig("packet_delivery_ratio.png")
    plt.close()

def plot_scalability(metrics):
    fig, ax = plt.subplots()
    for network_type in ["rina", "tcp", "hybrid"]:
        counts = []
        setup_times = []
        
        # Get the correct key based on network type
        time_key = "setup_time_per_flow" if network_type == "rina" else "setup_time_per_conn"
        
        for key, value in metrics[network_type]["scalability"].items():
            if time_key in value:
                counts.append(int(key.split("_")[-1]))
                setup_times.append(value[time_key])
            else:
                print(f"Warning: Missing {time_key} in {network_type} scalability data for {key}")
        
        if counts and setup_times:
            ax.plot(counts, setup_times, marker='o', label=network_type.upper())
    
    ax.set_title("Connection Setup Time per Flow/Connection")
    ax.set_xlabel("Number of Concurrent Flows/Connections")
    ax.set_ylabel("Setup Time per Instance (s)")
    ax.legend()
    plt.savefig("scalability.png")
    plt.close()

def main():
    metrics = load_metrics()
    df = create_csv(metrics)
    
    plot_throughput(metrics)
    plot_latency(metrics)
    plot_pdr(metrics)
    plot_scalability(metrics)
    
    print("Visualization complete. Check PNG files and network_metrics.csv")

if __name__ == "__main__":
    main()