import json
import matplotlib.pyplot as plt
import pandas as pd
import os

# Ensure output directories exist
os.makedirs('charts', exist_ok=True)
os.makedirs('csv', exist_ok=True)

def load_metrics():
    with open('metrics.json') as f:
        return json.load(f)

def plot_throughput(metrics):
    data = metrics.get('throughput_realistic_networks', {})
    plt.figure(figsize=(10, 6))
    
    for profile in data:
        packet_sizes = []
        throughputs = []
        for size_str, values in data[profile].items():
            packet_sizes.append(int(size_str))
            throughputs.append(values['throughput_mbps'])
        
        plt.plot(packet_sizes, throughputs, marker='o', label=profile)
    
    plt.xlabel('Packet Size (bytes)')
    plt.ylabel('Throughput (Mbps)')
    plt.title('Network Throughput by Packet Size and Profile')
    plt.legend()
    plt.grid(True)
    plt.savefig('charts/throughput.png')
    plt.close()

def plot_latency_jitter(metrics):
    data = metrics.get('latency_jitter_realistic', {})
    for profile in data:
        plt.figure(figsize=(10, 6))
        packet_sizes = []
        latencies = []
        jitters = []
        
        for size_str, values in data[profile].items():
            packet_sizes.append(int(size_str))
            latencies.append(values['avg_latency_ms'])
            jitters.append(values['avg_jitter_ms'])
        
        plt.plot(packet_sizes, latencies, marker='o', label='Latency')
        plt.plot(packet_sizes, jitters, marker='s', label='Jitter')
        
        plt.xlabel('Packet Size (bytes)')
        plt.ylabel('Time (ms)')
        plt.title(f'Latency & Jitter - {profile}')
        plt.legend()
        plt.grid(True)
        plt.savefig(f'charts/latency_jitter_{profile}.png')
        plt.close()

def plot_pdr(metrics):
    data = metrics.get('packet_delivery_ratio_realistic', {})
    profiles = list(data.keys())
    packet_sizes = list(next(iter(data.values())).keys()) if data else []
    
    for size_str in packet_sizes:
        plt.figure(figsize=(10, 6))
        pdr_values = []
        for profile in profiles:
            pdr_values.append(data[profile][size_str]['delivery_ratio'])
        
        plt.bar(profiles, pdr_values)
        plt.xlabel('Network Profile')
        plt.ylabel('Packet Delivery Ratio (%)')
        plt.title(f'PDR for {size_str} byte Packets')
        plt.ylim(0, 100)
        plt.grid(True)
        plt.savefig(f'charts/pdr_{size_str}.png')
        plt.close()

def plot_rtt(metrics):
    data = metrics.get('round_trip_time_realistic', {})
    plt.figure(figsize=(10, 6))
    
    for profile in data:
        packet_sizes = []
        rtts = []
        for size_str, values in data[profile].items():
            packet_sizes.append(int(size_str))
            rtts.append(values['avg_rtt_ms'])
        
        plt.plot(packet_sizes, rtts, marker='o', label=profile)
    
    plt.xlabel('Packet Size (bytes)')
    plt.ylabel('Average RTT (ms)')
    plt.title('Round Trip Time by Profile')
    plt.legend()
    plt.grid(True)
    plt.savefig('charts/rtt.png')
    plt.close()

def plot_scalability(metrics):
    data = metrics.get('scalability_concurrent_flows', {})
    for profile in data:
        flow_counts = []
        success_rates = []
        allocation_times = []
        
        for flow_str, values in data[profile].items():
            flow_counts.append(int(flow_str))
            success_rates.append((values['successful_flows'] / values['target_flows']) * 100)
            allocation_times.append(values['allocation_time_per_flow_ms'])
        
        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        color = 'tab:red'
        ax1.set_xlabel('Number of Flows')
        ax1.set_ylabel('Success Rate (%)', color=color)
        ax1.plot(flow_counts, success_rates, marker='o', color=color)
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.set_ylim(0, 100)
        
        ax2 = ax1.twinx()
        color = 'tab:blue'
        ax2.set_ylabel('Allocation Time per Flow (ms)', color=color)
        ax2.plot(flow_counts, allocation_times, marker='s', color=color)
        ax2.tick_params(axis='y', labelcolor=color)
        
        plt.title(f'Scalability - {profile}')
        fig.tight_layout()
        plt.savefig(f'charts/scalability_{profile}.png')
        plt.close()

def export_to_csv(metrics):
    # Throughput
    throughput_data = []
    for profile, sizes in metrics.get('throughput_realistic_networks', {}).items():
        for size, values in sizes.items():
            throughput_data.append({
                'profile': profile,
                'packet_size': int(size),
                'throughput_mbps': values['throughput_mbps'],
                'packets_sent': values['packets_sent'],
                'packets_per_second': values['packets_per_second']
            })
    pd.DataFrame(throughput_data).to_csv('csv/throughput.csv', index=False)

    # Latency & Jitter
    latency_data = []
    for profile, sizes in metrics.get('latency_jitter_realistic', {}).items():
        for size, values in sizes.items():
            latency_data.append({
                'profile': profile,
                'packet_size': int(size),
                'avg_latency_ms': values['avg_latency_ms'],
                'min_latency_ms': values['min_latency_ms'],
                'max_latency_ms': values['max_latency_ms'],
                'avg_jitter_ms': values['avg_jitter_ms']
            })
    pd.DataFrame(latency_data).to_csv('csv/latency_jitter.csv', index=False)

    # PDR
    pdr_data = []
    for profile, sizes in metrics.get('packet_delivery_ratio_realistic', {}).items():
        for size, values in sizes.items():
            pdr_data.append({
                'profile': profile,
                'packet_size': int(size),
                'sent': values['sent'],
                'received': values['received'],
                'delivery_ratio': values['delivery_ratio']
            })
    pd.DataFrame(pdr_data).to_csv('csv/pdr.csv', index=False)

    # RTT
    rtt_data = []
    for profile, sizes in metrics.get('round_trip_time_realistic', {}).items():
        for size, values in sizes.items():
            rtt_data.append({
                'profile': profile,
                'packet_size': int(size),
                'avg_rtt_ms': values['avg_rtt_ms'],
                'min_rtt_ms': values['min_rtt_ms'],
                'max_rtt_ms': values['max_rtt_ms']
            })
    pd.DataFrame(rtt_data).to_csv('csv/rtt.csv', index=False)

    # Scalability
    scalability_data = []
    for profile, flows in metrics.get('scalability_concurrent_flows', {}).items():
        for flow, values in flows.items():
            scalability_data.append({
                'profile': profile,
                'target_flows': values['target_flows'],
                'successful_flows': values['successful_flows'],
                'allocation_time_seconds': values['allocation_time_seconds'],
                'allocation_time_per_flow_ms': values['allocation_time_per_flow_ms'],
                'data_send_success_rate': values['data_send_success_rate']
            })
    pd.DataFrame(scalability_data).to_csv('csv/scalability.csv', index=False)

def main():
    metrics = load_metrics()
    
    plot_throughput(metrics)
    plot_latency_jitter(metrics)
    plot_pdr(metrics)
    plot_rtt(metrics)
    plot_scalability(metrics)
    
    export_to_csv(metrics)
    print("Visualization and CSV export completed!")

if __name__ == "__main__":
    main()