import json
import csv
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

def load_metrics(metrics_file="hybrid_metrics.json"):
    """Load metrics from the JSON file"""
    try:
        with open(metrics_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Metrics file '{metrics_file}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not parse '{metrics_file}' as JSON.")
        return None

def ensure_output_dirs():
    """Create output directories if they don't exist"""
    Path("./charts").mkdir(exist_ok=True)
    Path("./csv_data").mkdir(exist_ok=True)

def generate_throughput_charts(metrics):
    """Generate charts for throughput metrics"""
    if 'throughput_hybrid_network' not in metrics:
        print("No throughput metrics found.")
        return
    
    throughput_data = metrics['throughput_hybrid_network']
    
    # Prepare data for CSV
    csv_data = []
    for profile, profile_data in throughput_data.items():
        for packet_size, metrics in profile_data.items():
            csv_data.append({
                'profile': profile,
                'packet_size': packet_size,
                'throughput_mbps': metrics['throughput_mbps'],
                'packets_per_second': metrics['packets_per_second'],
                'delivery_ratio': metrics['delivery_ratio']
            })
    
    # Write CSV
    with open('./csv_data/throughput_metrics.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['profile', 'packet_size', 'throughput_mbps', 
                                              'packets_per_second', 'delivery_ratio'])
        writer.writeheader()
        writer.writerows(csv_data)
    
    # Create DataFrame for plotting
    df = pd.DataFrame(csv_data)
    
    # Plot throughput vs packet size for each profile
    plt.figure(figsize=(12, 8))
    sns.barplot(x='packet_size', y='throughput_mbps', hue='profile', data=df)
    plt.title('Throughput vs Packet Size Across Network Profiles')
    plt.xlabel('Packet Size (bytes)')
    plt.ylabel('Throughput (Mbps)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('./charts/throughput_vs_packet_size.png')
    
    # Plot packets per second
    plt.figure(figsize=(12, 8))
    sns.barplot(x='packet_size', y='packets_per_second', hue='profile', data=df)
    plt.title('Packet Rate vs Packet Size Across Network Profiles')
    plt.xlabel('Packet Size (bytes)')
    plt.ylabel('Packets per Second')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('./charts/packet_rate_vs_packet_size.png')
    
    # Plot delivery ratio
    plt.figure(figsize=(12, 8))
    sns.barplot(x='profile', y='delivery_ratio', hue='packet_size', data=df)
    plt.title('Packet Delivery Ratio Across Network Profiles')
    plt.xlabel('Network Profile')
    plt.ylabel('Delivery Ratio (%)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('./charts/delivery_ratio_by_profile.png')
    
    print("Generated throughput charts and CSV data.")

def generate_latency_charts(metrics):
    """Generate charts for latency metrics"""
    if 'latency_jitter_hybrid' not in metrics:
        print("No latency metrics found.")
        return
    
    latency_data = metrics['latency_jitter_hybrid']
    
    # Prepare data for CSV
    csv_data = []
    for profile, profile_data in latency_data.items():
        for packet_size, metrics in profile_data.items():
            csv_data.append({
                'profile': profile,
                'packet_size': packet_size,
                'avg_latency_ms': metrics['avg_latency_ms'],
                'min_latency_ms': metrics['min_latency_ms'],
                'max_latency_ms': metrics['max_latency_ms'],
                'avg_jitter_ms': metrics['avg_jitter_ms'],
                'avg_rtt_ms': metrics['avg_rtt_ms']
            })
    
    # Write CSV
    with open('./csv_data/latency_metrics.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['profile', 'packet_size', 'avg_latency_ms', 
                                              'min_latency_ms', 'max_latency_ms', 
                                              'avg_jitter_ms', 'avg_rtt_ms'])
        writer.writeheader()
        writer.writerows(csv_data)
    
    # Create DataFrame for plotting
    df = pd.DataFrame(csv_data)
    
    # Plot average latency
    plt.figure(figsize=(12, 8))
    sns.barplot(x='profile', y='avg_latency_ms', hue='packet_size', data=df)
    plt.title('Average Latency Across Network Profiles')
    plt.xlabel('Network Profile')
    plt.ylabel('Average Latency (ms)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('./charts/avg_latency_by_profile.png')
    
    # Plot latency range
    plt.figure(figsize=(12, 8))
    
    # Calculate positions for grouped bars
    profiles = df['profile'].unique()
    packet_sizes = sorted(df['packet_size'].unique())
    n_sizes = len(packet_sizes)
    width = 0.25  # Width of each bar
    
    # Prepare the plot
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Create positions for bars
    positions = np.arange(len(profiles))
    
    # Plot min, avg, max for each profile and packet size
    for i, size in enumerate(packet_sizes):
        size_data = df[df['packet_size'] == size]
        
        # Get positions for this packet size
        size_positions = positions + (i - n_sizes/2 + 0.5) * width
        
        # Plot error bars from min to max
        ax.bar(size_positions, 
               size_data['avg_latency_ms'], 
               width=width, 
               label=f'{size} bytes')
        
        # Add error bars from min to max
        ax.errorbar(size_positions, 
                   size_data['avg_latency_ms'], 
                   yerr=[size_data['avg_latency_ms'] - size_data['min_latency_ms'], 
                         size_data['max_latency_ms'] - size_data['avg_latency_ms']],
                   fmt='none', 
                   ecolor='black', 
                   capsize=5)
    
    # Set labels and title
    ax.set_xlabel('Network Profile')
    ax.set_ylabel('Latency (ms)')
    ax.set_title('Latency Range (Min-Avg-Max) Across Network Profiles')
    ax.set_xticks(positions)
    ax.set_xticklabels(profiles)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('./charts/latency_range_by_profile.png')
    
    # Plot jitter
    plt.figure(figsize=(12, 8))
    sns.barplot(x='profile', y='avg_jitter_ms', hue='packet_size', data=df)
    plt.title('Average Jitter Across Network Profiles')
    plt.xlabel('Network Profile')
    plt.ylabel('Jitter (ms)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('./charts/jitter_by_profile.png')
    
    print("Generated latency charts and CSV data.")

def generate_pdr_charts(metrics):
    """Generate charts for packet delivery ratio metrics"""
    if 'packet_delivery_ratio_hybrid' not in metrics:
        print("No PDR metrics found.")
        return
    
    pdr_data = metrics['packet_delivery_ratio_hybrid']
    
    # Prepare data for CSV
    csv_data = []
    for profile, profile_data in pdr_data.items():
        for packet_size, metrics in profile_data.items():
            csv_data.append({
                'profile': profile,
                'packet_size': packet_size,
                'sent': metrics['sent'],
                'received': metrics['received'],
                'delivery_ratio': metrics['delivery_ratio']
            })
    
    # Write CSV
    with open('./csv_data/pdr_metrics.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['profile', 'packet_size', 'sent', 'received', 'delivery_ratio'])
        writer.writeheader()
        writer.writerows(csv_data)
    
    # Create DataFrame for plotting
    df = pd.DataFrame(csv_data)
    
    # Plot PDR by profile
    plt.figure(figsize=(12, 8))
    sns.barplot(x='profile', y='delivery_ratio', hue='packet_size', data=df)
    plt.title('Packet Delivery Ratio Across Network Profiles')
    plt.xlabel('Network Profile')
    plt.ylabel('Delivery Ratio (%)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('./charts/pdr_by_profile.png')
    
    # Plot sent vs received packets
    plt.figure(figsize=(14, 10))
    
    # Prepare data for grouped bar chart
    profiles = df['profile'].unique()
    packet_sizes = sorted(df['packet_size'].unique())
    
    # Set width of bars
    barWidth = 0.35
    
    # Set positions of the bars on X axis
    r1 = np.arange(len(profiles))
    r2 = [x + barWidth for x in r1]
    
    # Create subplots for each packet size
    fig, axes = plt.subplots(1, len(packet_sizes), figsize=(18, 8), sharey=True)
    
    # If only one packet size, make axes iterable
    if len(packet_sizes) == 1:
        axes = [axes]
    
    for i, size in enumerate(packet_sizes):
        size_data = df[df['packet_size'] == size]
        
        # Extract sent and received values for this packet size
        sent_vals = size_data['sent'].values
        recv_vals = size_data['received'].values
        
        # Create bars
        axes[i].bar(r1, sent_vals, width=barWidth, label='Sent', color='skyblue')
        axes[i].bar(r2, recv_vals, width=barWidth, label='Received', color='lightgreen')
        
        # Add labels and title
        axes[i].set_xlabel('Network Profile')
        if i == 0:
            axes[i].set_ylabel('Packet Count')
        axes[i].set_title(f'Packet Size: {size} bytes')
        axes[i].set_xticks([r + barWidth/2 for r in range(len(profiles))])
        axes[i].set_xticklabels(profiles)
        axes[i].legend()
        axes[i].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('./charts/sent_vs_received.png')
    
    print("Generated PDR charts and CSV data.")

def generate_connection_charts(metrics):
    """Generate charts for connection metrics"""
    connection_metrics = {}
    
    if 'concurrent_tcp_connections' in metrics:
        connection_metrics['concurrent'] = metrics['concurrent_tcp_connections']
    if 'tcp_reconnection_resilience' in metrics:
        connection_metrics['reconnection'] = metrics['tcp_reconnection_resilience']
    
    if not connection_metrics:
        print("No connection metrics found.")
        return
    
    # Process concurrent connection data
    if 'concurrent' in connection_metrics:
        concurrent_data = connection_metrics['concurrent']
        
        # Prepare data for CSV
        csv_data = []
        for conn_count, metrics in concurrent_data.items():
            csv_data.append({
                'target_connections': metrics['target_connections'],
                'successful_connections': metrics['successful_connections'],
                'establishment_time_seconds': metrics['establishment_time_seconds'],
                'establishment_time_per_conn_ms': metrics['establishment_time_per_conn_ms'],
                'data_exchange_success_rate': metrics['data_exchange_success_rate']
            })
        
        # Write CSV
        with open('./csv_data/concurrent_connection_metrics.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['target_connections', 'successful_connections', 
                                                  'establishment_time_seconds', 
                                                  'establishment_time_per_conn_ms',
                                                  'data_exchange_success_rate'])
            writer.writeheader()
            writer.writerows(csv_data)
        
        # Create DataFrame for plotting
        df = pd.DataFrame(csv_data)
        
        # Plot connection establishment time
        plt.figure(figsize=(12, 8))
        sns.barplot(x='target_connections', y='establishment_time_seconds', data=df)
        plt.title('Connection Establishment Time vs Connection Count')
        plt.xlabel('Number of Connections')
        plt.ylabel('Establishment Time (seconds)')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('./charts/connection_establishment_time.png')
        
        # Plot time per connection
        plt.figure(figsize=(12, 8))
        sns.barplot(x='target_connections', y='establishment_time_per_conn_ms', data=df)
        plt.title('Time per Connection vs Connection Count')
        plt.xlabel('Number of Connections')
        plt.ylabel('Time per Connection (ms)')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('./charts/time_per_connection.png')
        
        # Plot data exchange success rate
        plt.figure(figsize=(12, 8))
        sns.barplot(x='target_connections', y='data_exchange_success_rate', data=df)
        plt.title('Data Exchange Success Rate vs Connection Count')
        plt.xlabel('Number of Connections')
        plt.ylabel('Success Rate (%)')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('./charts/data_exchange_success_rate.png')
    
    # Process reconnection data
    if 'reconnection' in connection_metrics:
        reconnection_data = connection_metrics['reconnection']
        
        # Extract detailed results
        detailed_results = reconnection_data.get('detailed_results', [])
        
        if detailed_results:
            # Write CSV
            with open('./csv_data/reconnection_metrics.csv', 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['attempt', 'first_connection', 
                                                      'reconnection', 'overall_success'])
                writer.writeheader()
                # Filter out error field which might not be present in all entries
                clean_results = []
                for result in detailed_results:
                    clean_result = {k: v for k, v in result.items() 
                                    if k in ['attempt', 'first_connection', 'reconnection', 'overall_success']}
                    clean_results.append(clean_result)
                writer.writerows(clean_results)
            
            # Create DataFrame for plotting
            df = pd.DataFrame(detailed_results)
            
            # Plot reconnection success
            plt.figure(figsize=(12, 8))
            
            # Set positions and width
            index = np.arange(len(df))
            width = 0.3
            
            # Create bars
            plt.bar(index - width/2, df['first_connection'].astype(int), width, label='First Connection')
            plt.bar(index + width/2, df['reconnection'].astype(int), width, label='Reconnection')
            
            # Add labels
            plt.xlabel('Attempt')
            plt.ylabel('Success (1=Yes, 0=No)')
            plt.title('Connection and Reconnection Success by Attempt')
            plt.xticks(index, df['attempt'])
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig('./charts/reconnection_success_by_attempt.png')
            
            # Create summary chart
            plt.figure(figsize=(10, 6))
            summary_data = {
                'Type': ['First Connection', 'Reconnection', 'Overall Success'],
                'Success Rate': [
                    df['first_connection'].mean() * 100,
                    df['reconnection'].mean() * 100,
                    df['overall_success'].mean() * 100
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            sns.barplot(x='Type', y='Success Rate', data=summary_df)
            plt.title('Connection and Reconnection Success Rates')
            plt.ylabel('Success Rate (%)')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig('./charts/reconnection_success_rates.png')
    
    print("Generated connection charts and CSV data.")

def generate_summary_report(metrics):
    """Generate a summary report of all metrics"""
    # Create a comprehensive CSV with key metrics
    summary_data = []
    
    # Extract throughput data if available
    if 'throughput_hybrid_network' in metrics:
        for profile, profile_data in metrics['throughput_hybrid_network'].items():
            for packet_size, metrics_data in profile_data.items():
                row = {
                    'metric_type': 'throughput',
                    'profile': profile,
                    'packet_size': packet_size,
                    'value': metrics_data['throughput_mbps'],
                    'unit': 'Mbps'
                }
                summary_data.append(row)
    
    # Extract latency data if available
    if 'latency_jitter_hybrid' in metrics:
        for profile, profile_data in metrics['latency_jitter_hybrid'].items():
            for packet_size, metrics_data in profile_data.items():
                # Add latency data
                row = {
                    'metric_type': 'latency',
                    'profile': profile,
                    'packet_size': packet_size,
                    'value': metrics_data['avg_latency_ms'],
                    'unit': 'ms'
                }
                summary_data.append(row)
                
                # Add jitter data
                row = {
                    'metric_type': 'jitter',
                    'profile': profile,
                    'packet_size': packet_size,
                    'value': metrics_data['avg_jitter_ms'],
                    'unit': 'ms'
                }
                summary_data.append(row)
    
    # Extract PDR data if available
    if 'packet_delivery_ratio_hybrid' in metrics:
        for profile, profile_data in metrics['packet_delivery_ratio_hybrid'].items():
            for packet_size, metrics_data in profile_data.items():
                row = {
                    'metric_type': 'pdr',
                    'profile': profile,
                    'packet_size': packet_size,
                    'value': metrics_data['delivery_ratio'],
                    'unit': '%'
                }
                summary_data.append(row)
    
    # Write summary CSV
    if summary_data:
        with open('./csv_data/performance_summary.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['metric_type', 'profile', 'packet_size', 'value', 'unit'])
            writer.writeheader()
            writer.writerows(summary_data)
    
    # Create a pivot table for easier analysis
    if summary_data:
        df = pd.DataFrame(summary_data)
        
        # Create a pivot table with profiles as rows, packet sizes as columns, and metrics as values
        metric_types = df['metric_type'].unique()
        
        for metric in metric_types:
            metric_df = df[df['metric_type'] == metric]
            
            # Create pivot table
            pivot = pd.pivot_table(
                metric_df, 
                values='value',
                index=['profile'],
                columns=['packet_size'],
                aggfunc='mean'
            )
            
            # Save pivot table
            pivot.to_csv(f'./csv_data/{metric}_pivot.csv')
    
    print("Generated summary report and pivot tables.")

def create_all_charts_and_csv(metrics_file="hybrid_metrics.json"):
    """Create all charts and CSV files from metrics"""
    metrics = load_metrics(metrics_file)
    if not metrics:
        return
    
    ensure_output_dirs()
    
    # Generate charts and CSV files
    generate_throughput_charts(metrics)
    generate_latency_charts(metrics)
    generate_pdr_charts(metrics)
    generate_connection_charts(metrics)
    generate_summary_report(metrics)
    
    print(f"All charts and CSV files generated successfully.")
    print(f"Charts saved in ./charts/")
    print(f"CSV data saved in ./csv_data/")

if __name__ == "__main__":
    create_all_charts_and_csv()