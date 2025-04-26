import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# Create output directories
os.makedirs('csv_output', exist_ok=True)
os.makedirs('charts', exist_ok=True)

# Load the JSON data
with open('RINA/rina_metrics.json', 'r') as f:
    rina_data = json.load(f)

with open('RINA/tcp_metrics.json', 'r') as f:
    tcp_data = json.load(f)

with open('RINA/hybrid_metrics.json', 'r') as f:
    hybrid_data = json.load(f)

# 1. THROUGHPUT COMPARISON
def extract_throughput_data():
    # Initialize dataframes for each network type
    networks = ['perfect', 'lan', 'wifi', 'congested']
    packet_sizes = [64, 512, 1024, 4096, 8192]
    
    all_data = []
    
    # Extract TCP data
    for network in networks:
        for size in packet_sizes:
            if str(size) in tcp_data['throughput_tcp_network'][network]:
                row = {
                    'Protocol': 'TCP',
                    'Network': network,
                    'Packet_Size': size,
                    'Throughput_Mbps': tcp_data['throughput_tcp_network'][network][str(size)]['throughput_mbps'],
                    'Delivery_Ratio': tcp_data['throughput_tcp_network'][network][str(size)]['delivery_ratio']
                }
                all_data.append(row)
    
    # Extract RINA data
    for network in networks:
        for size in packet_sizes:
            if str(size) in rina_data['throughput_realistic_networks'][network]:
                row = {
                    'Protocol': 'RINA',
                    'Network': network,
                    'Packet_Size': size,
                    'Throughput_Mbps': rina_data['throughput_realistic_networks'][network][str(size)]['throughput_mbps'],
                    'Delivery_Ratio': 100.0  # Not directly available in the same way, using placeholder
                }
                all_data.append(row)
    
    # Extract Hybrid data
    for network in networks:
        for size in packet_sizes:
            if str(size) in hybrid_data['throughput_hybrid_network'][network]:
                row = {
                    'Protocol': 'Hybrid',
                    'Network': network,
                    'Packet_Size': size,
                    'Throughput_Mbps': hybrid_data['throughput_hybrid_network'][network][str(size)]['throughput_mbps'],
                    'Delivery_Ratio': hybrid_data['throughput_hybrid_network'][network][str(size)]['delivery_ratio']
                }
                all_data.append(row)
    
    # Create dataframe
    df = pd.DataFrame(all_data)
    
    # Save to CSV
    df.to_csv('csv_output/throughput_comparison.csv', index=False)
    
    return df

# 2. LATENCY COMPARISON
def extract_latency_data():
    networks = ['perfect', 'lan', 'wifi', 'congested']
    packet_sizes = [64, 512, 1024, 4096]
    
    all_data = []
    
    # Extract TCP latency data
    for network in networks:
        for size in packet_sizes:
            if str(size) in tcp_data['latency_jitter_tcp'][network]:
                row = {
                    'Protocol': 'TCP',
                    'Network': network,
                    'Packet_Size': size,
                    'Avg_Latency_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['avg_latency_ms'],
                    'Min_Latency_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['min_latency_ms'],
                    'Max_Latency_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['max_latency_ms'],
                    'Avg_Jitter_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['avg_jitter_ms'],
                    'Avg_RTT_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['avg_rtt_ms']
                }
                all_data.append(row)
    
    # Extract RINA latency data
    for network in networks:
        for size in packet_sizes:
            if str(size) in rina_data['latency_jitter_realistic'][network]:
                row = {
                    'Protocol': 'RINA',
                    'Network': network,
                    'Packet_Size': size,
                    'Avg_Latency_ms': rina_data['latency_jitter_realistic'][network][str(size)]['avg_latency_ms'],
                    'Min_Latency_ms': rina_data['latency_jitter_realistic'][network][str(size)]['min_latency_ms'],
                    'Max_Latency_ms': rina_data['latency_jitter_realistic'][network][str(size)]['max_latency_ms'],
                    'Avg_Jitter_ms': rina_data['latency_jitter_realistic'][network][str(size)]['avg_jitter_ms'],
                    'Avg_RTT_ms': rina_data['latency_jitter_realistic'][network][str(size)]['avg_rtt_ms']
                }
                all_data.append(row)
    
    # Extract Hybrid latency data
    for network in networks:
        for size in packet_sizes:
            if str(size) in hybrid_data['latency_jitter_hybrid'][network]:
                row = {
                    'Protocol': 'Hybrid',
                    'Network': network,
                    'Packet_Size': size,
                    'Avg_Latency_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['avg_latency_ms'],
                    'Min_Latency_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['min_latency_ms'],
                    'Max_Latency_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['max_latency_ms'],
                    'Avg_Jitter_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['avg_jitter_ms'],
                    'Avg_RTT_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['avg_rtt_ms']
                }
                all_data.append(row)
    
    # Create dataframe
    df = pd.DataFrame(all_data)
    
    # Save to CSV
    df.to_csv('csv_output/latency_comparison.csv', index=False)
    
    return df

# Add these functions to your existing Python script

def extract_detailed_scalability_data():
    """
    Extract more detailed scalability metrics from the JSON data
    """
    connection_counts = [1, 5, 10, 25]  # Include 50 for RINA
    
    all_data = []
    
    # Extract TCP data
    for count in [1, 5, 10, 25]:  # TCP doesn't have 50
        if str(count) in tcp_data['concurrent_tcp_connections']:
            row = {
                'Protocol': 'TCP',
                'Connection_Count': count,
                'Successful_Connections': tcp_data['concurrent_tcp_connections'][str(count)]['successful_connections'],
                'Establishment_Time_ms': tcp_data['concurrent_tcp_connections'][str(count)]['establishment_time_per_conn_ms'],
                'Success_Rate': tcp_data['concurrent_tcp_connections'][str(count)]['data_exchange_success_rate'],
                'Memory_Usage_MB': tcp_data['concurrent_tcp_connections'][str(count)].get('memory_usage_mb', None),
                'CPU_Usage_Percent': tcp_data['concurrent_tcp_connections'][str(count)].get('cpu_usage_percent', None)
            }
            all_data.append(row)
    
    # Extract RINA data for all available networks
    networks = ['perfect', 'lan', 'wifi', 'congested']
    for network in networks:
        if network in rina_data['scalability_concurrent_flows']:
            for count in connection_counts:
                if str(count) in rina_data['scalability_concurrent_flows'][network]:
                    row = {
                        'Protocol': 'RINA',
                        'Network': network,
                        'Connection_Count': count,
                        'Successful_Connections': rina_data['scalability_concurrent_flows'][network][str(count)]['successful_flows'],
                        'Establishment_Time_ms': rina_data['scalability_concurrent_flows'][network][str(count)]['allocation_time_per_flow_ms'],
                        'Success_Rate': rina_data['scalability_concurrent_flows'][network][str(count)]['data_send_success_rate'],
                        'Bandwidth_Per_Flow_Mbps': rina_data['scalability_concurrent_flows'][network][str(count)]['bandwidth_per_flow_mbps'],
                        'Memory_Usage_MB': rina_data['scalability_concurrent_flows'][network][str(count)].get('memory_usage_mb', None),
                        'CPU_Usage_Percent': rina_data['scalability_concurrent_flows'][network][str(count)].get('cpu_usage_percent', None)
                    }
                    all_data.append(row)
    
    # Extract Hybrid data
    for count in [1, 5, 10, 25]:  # Hybrid doesn't have 50
        if str(count) in hybrid_data['concurrent_tcp_connections']:
            row = {
                'Protocol': 'Hybrid',
                'Connection_Count': count,
                'Successful_Connections': hybrid_data['concurrent_tcp_connections'][str(count)]['successful_connections'],
                'Establishment_Time_ms': hybrid_data['concurrent_tcp_connections'][str(count)]['establishment_time_per_conn_ms'],
                'Success_Rate': hybrid_data['concurrent_tcp_connections'][str(count)]['data_exchange_success_rate'],
                'Memory_Usage_MB': hybrid_data['concurrent_tcp_connections'][str(count)].get('memory_usage_mb', None),
                'CPU_Usage_Percent': hybrid_data['concurrent_tcp_connections'][str(count)].get('cpu_usage_percent', None)
            }
            all_data.append(row)
    
    # Create dataframe
    df = pd.DataFrame(all_data)
    
    # Calculate additional scalability metrics if possible
    if 'Memory_Usage_MB' in df.columns and not df['Memory_Usage_MB'].isna().all():
        # Memory efficiency = connections per MB of memory
        df['Memory_Efficiency'] = df['Successful_Connections'] / df['Memory_Usage_MB'].replace(0, float('nan'))
    
    if 'CPU_Usage_Percent' in df.columns and not df['CPU_Usage_Percent'].isna().all():
        # CPU efficiency = connections per percent of CPU
        df['CPU_Efficiency'] = df['Successful_Connections'] / df['CPU_Usage_Percent'].replace(0, float('nan'))
    
    # Save to CSV
    df.to_csv('csv_output/scalability_detailed.csv', index=False)
    
    return df

# 3. PACKET DELIVERY RATIO COMPARISON
def extract_pdr_data():
    networks = ['perfect', 'lan', 'wifi', 'congested']
    packet_sizes = [64, 1024, 4096]  # Some datasets don't have all sizes
    
    all_data = []
    
    # Extract TCP data
    for network in networks:
        for size in [64, 1024, 4096]:  # TCP only has 64 and 1024
            if str(size) in tcp_data['packet_delivery_ratio_tcp'][network]:
                row = {
                    'Protocol': 'TCP',
                    'Network': network,
                    'Packet_Size': size,
                    'Sent': tcp_data['packet_delivery_ratio_tcp'][network][str(size)]['sent'],
                    'Received': tcp_data['packet_delivery_ratio_tcp'][network][str(size)]['received'],
                    'Delivery_Ratio': tcp_data['packet_delivery_ratio_tcp'][network][str(size)]['delivery_ratio']
                }
                all_data.append(row)
    
    # Extract RINA data
    for network in networks:
        for size in packet_sizes:
            if str(size) in rina_data['packet_delivery_ratio_realistic'][network]:
                row = {
                    'Protocol': 'RINA',
                    'Network': network,
                    'Packet_Size': size,
                    'Sent': rina_data['packet_delivery_ratio_realistic'][network][str(size)]['sent'],
                    'Received': rina_data['packet_delivery_ratio_realistic'][network][str(size)]['received'],
                    'Delivery_Ratio': rina_data['packet_delivery_ratio_realistic'][network][str(size)]['delivery_ratio']
                }
                all_data.append(row)
    
    # Extract Hybrid data
    for network in networks:
        for size in [64, 1024, 4096]:  # Hybrid only has 64 and 1024
            if str(size) in hybrid_data['packet_delivery_ratio_hybrid'][network]:
                row = {
                    'Protocol': 'Hybrid',
                    'Network': network,
                    'Packet_Size': size,
                    'Sent': hybrid_data['packet_delivery_ratio_hybrid'][network][str(size)]['sent'],
                    'Received': hybrid_data['packet_delivery_ratio_hybrid'][network][str(size)]['received'],
                    'Delivery_Ratio': hybrid_data['packet_delivery_ratio_hybrid'][network][str(size)]['delivery_ratio']
                }
                all_data.append(row)
    
    # Create dataframe
    df = pd.DataFrame(all_data)
    
    # Save to CSV
    df.to_csv('csv_output/packet_delivery_ratio.csv', index=False)
    
    return df

# 4. CONCURRENT CONNECTIONS/FLOWS
def extract_concurrent_data():
    connection_counts = [1, 5, 10, 25]  # 50 only in RINA
    
    all_data = []
    
    # Extract TCP data
    for count in [1, 5, 10, 25]:  # TCP doesn't have 50
        row = {
            'Protocol': 'TCP',
            'Target_Count': count,
            'Successful_Count': tcp_data['concurrent_tcp_connections'][str(count)]['successful_connections'],
            'Establishment_Time_ms': tcp_data['concurrent_tcp_connections'][str(count)]['establishment_time_per_conn_ms'],
            'Success_Rate': tcp_data['concurrent_tcp_connections'][str(count)]['data_exchange_success_rate']
        }
        all_data.append(row)
    
    # Extract RINA data for perfect network
    for count in connection_counts:
        if str(count) in rina_data['scalability_concurrent_flows']['perfect']:
            row = {
                'Protocol': 'RINA',
                'Target_Count': count,
                'Successful_Count': rina_data['scalability_concurrent_flows']['perfect'][str(count)]['successful_flows'],
                'Establishment_Time_ms': rina_data['scalability_concurrent_flows']['perfect'][str(count)]['allocation_time_per_flow_ms'],
                'Success_Rate': rina_data['scalability_concurrent_flows']['perfect'][str(count)]['data_send_success_rate'],
                'Bandwidth_Per_Flow_Mbps': rina_data['scalability_concurrent_flows']['perfect'][str(count)]['bandwidth_per_flow_mbps']
            }
            all_data.append(row)
    
    # Extract Hybrid data
    for count in [1, 5, 10, 25]:  # Hybrid doesn't have 50
        row = {
            'Protocol': 'Hybrid',
            'Target_Count': count,
            'Successful_Count': hybrid_data['concurrent_tcp_connections'][str(count)]['successful_connections'],
            'Establishment_Time_ms': hybrid_data['concurrent_tcp_connections'][str(count)]['establishment_time_per_conn_ms'],
            'Success_Rate': hybrid_data['concurrent_tcp_connections'][str(count)]['data_exchange_success_rate']
        }
        all_data.append(row)
    
    # Create dataframe
    df = pd.DataFrame(all_data)
    
    # Save to CSV
    df.to_csv('csv_output/concurrent_connections.csv', index=False)
    
    return df

# VISUALIZATIONS

# 1. Throughput comparison across protocols and networks
def plot_throughput_comparison(df):
    # Get unique network profiles
    networks = df['Network'].unique()
    
    # Create a separate chart for each network profile
    for network in networks:
        # Filter data for this network
        network_df = df[df['Network'] == network]
        
        # Create figure
        plt.figure(figsize=(10, 6))
        
        # Create bar chart
        sns.barplot(x='Packet_Size', y='Throughput_Mbps', hue='Protocol', 
                   data=network_df, errorbar=None, palette='viridis')
        
        # Add titles and labels
        plt.title(f'Throughput Comparison - {network.capitalize()} Network')
        plt.xlabel('Packet Size (bytes)')
        plt.ylabel('Throughput (Mbps)')
        plt.legend(title='Protocol')
        
        # Save the figure
        plt.tight_layout()
        plt.savefig(f'charts/throughput_{network}_network.png', dpi=300)
        plt.close()
        
        # Create log scale version for better visibility of small values
        plt.figure(figsize=(10, 6))
        
        # Create bar chart
        ax = sns.barplot(x='Packet_Size', y='Throughput_Mbps', hue='Protocol', 
                       data=network_df, errorbar=None, palette='viridis')
        
        # Set y-axis to log scale
        ax.set_yscale('log')
        
        # Add titles and labels
        plt.title(f'Throughput Comparison - {network.capitalize()} Network (Log Scale)')
        plt.xlabel('Packet Size (bytes)')
        plt.ylabel('Throughput (Mbps) - Log Scale')
        plt.legend(title='Protocol')
        
        # Save the figure
        plt.tight_layout()
        plt.savefig(f'charts/throughput_{network}_network_log.png', dpi=300)
        plt.close()
    
    # Also create a consolidated view with all networks in one figure
    plt.figure(figsize=(16, 10))
    
    # Create facet grid with one chart per network
    g = sns.FacetGrid(df, col='Network', height=5, aspect=1.2)
    g.map_dataframe(sns.barplot, x='Packet_Size', y='Throughput_Mbps', 
                   hue='Protocol', errorbar=None, palette='viridis')
    
    # Add titles and labels
    g.set_axis_labels('Packet Size (bytes)', 'Throughput (Mbps)')
    g.set_titles(col_template='{col_name} Network')
    g.add_legend(title='Protocol')
    
    # Save the figure
    plt.tight_layout()
    plt.savefig('charts/throughput_all_networks.png', dpi=300)
    plt.close()

# 2. Latency comparison
def plot_latency_comparison(df):
    # Filter out congested network for better scale in first plot
    df_no_congested = df[df['Network'] != 'congested']
    
    plt.figure(figsize=(14, 8))
    
    # Create facet grid by network and packet size
    g = sns.FacetGrid(df_no_congested, col='Network', row='Packet_Size', height=3, aspect=1.5)
    g.map_dataframe(sns.barplot, x='Protocol', y='Avg_Latency_ms', errorbar=None, palette='cool')
    
    g.set_axis_labels('Protocol', 'Average Latency (ms)')
    g.set_titles(col_template='{col_name} Network', row_template='Packet Size: {row_name} bytes')
    
    plt.tight_layout()
    plt.savefig('charts/latency_comparison_no_congested.png', dpi=300)
    
    # Create a separate plot for all networks including congested
    g = sns.FacetGrid(df, col='Network', row='Packet_Size', height=3, aspect=1.5)
    g.map_dataframe(sns.barplot, x='Protocol', y='Avg_Latency_ms', errorbar=None, palette='cool')
    
    g.set_axis_labels('Protocol', 'Average Latency (ms)')
    g.set_titles(col_template='{col_name} Network', row_template='Packet Size: {row_name} bytes')
    
    plt.tight_layout()
    plt.savefig('charts/latency_comparison_all.png', dpi=300)
    
    # Plot jitter comparison
    g = sns.FacetGrid(df, col='Network', height=5, aspect=1.2)
    g.map_dataframe(sns.barplot, x='Protocol', y='Avg_Jitter_ms', hue='Packet_Size', errorbar=None, palette='rocket')
    
    g.set_axis_labels('Protocol', 'Average Jitter (ms)')
    g.set_titles(col_template='{col_name} Network')
    g.add_legend(title='Packet Size (bytes)')
    
    plt.tight_layout()
    plt.savefig('charts/jitter_comparison.png', dpi=300)

def plot_jitter_comparison(df):
    plt.figure(figsize=(16, 8))
    g = sns.FacetGrid(df, col='Network', height=6, aspect=1.2)
    g.map_dataframe(sns.barplot, x='Packet_Size', y='Avg_Jitter_ms', 
                   hue='Protocol', errorbar=None, palette='Set2')
    
    g.set_axis_labels('Packet Size (bytes)', 'Average Jitter (ms)')
    g.set_titles(col_template='{col_name} Network')
    g.add_legend(title='Protocol')
    
    # Improve readability
    for ax in g.axes.flat:
        ax.grid(True, linestyle='--', alpha=0.6)
        for label in ax.get_xticklabels():
            label.set_rotation(45)
    
    plt.tight_layout()
    plt.savefig('charts/jitter_by_network_packetsize.png', dpi=300)
    
    # 2. Protocol-focused jitter comparison
    plt.figure(figsize=(16, 8))
    g = sns.FacetGrid(df, col='Protocol', height=6, aspect=1.2)
    g.map_dataframe(sns.barplot, x='Network', y='Avg_Jitter_ms', 
                   hue='Packet_Size', errorbar=None, palette='viridis')
    
    g.set_axis_labels('Network Type', 'Average Jitter (ms)')
    g.set_titles(col_template='{col_name} Protocol')
    g.add_legend(title='Packet Size (bytes)')
    
    # Improve readability
    for ax in g.axes.flat:
        ax.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig('charts/jitter_by_protocol_network.png', dpi=300)
    
    # 3. Heatmap visualization for jitter comparison
    pivot_df = df.pivot_table(
        index=['Protocol', 'Packet_Size'], 
        columns='Network', 
        values='Avg_Jitter_ms'
    )
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(pivot_df, annot=True, cmap='YlGnBu', fmt='.2f', linewidths=.5)
    plt.title('Average Jitter (ms) Across Networks, Protocols and Packet Sizes')
    plt.tight_layout()
    plt.savefig('charts/jitter_heatmap.png', dpi=300)
    
    # 4. Box plot to show jitter distribution and variability
    plt.figure(figsize=(18, 10))
    g = sns.FacetGrid(df, col='Network', row='Protocol', height=4, aspect=1.3)
    g.map_dataframe(sns.boxplot, x='Packet_Size', y='Avg_Jitter_ms', palette='Set3')
    
    g.set_axis_labels('Packet Size (bytes)', 'Average Jitter (ms)')
    g.set_titles(col_template='{col_name} Network', row_template='{row_name}')
    
    # Improve readability
    for ax in g.axes.flat:
        if ax is not None:
            ax.grid(True, linestyle='--', alpha=0.6)
            for label in ax.get_xticklabels():
                label.set_rotation(45)
    
    plt.tight_layout()
    plt.savefig('charts/jitter_boxplot_by_protocol_network.png', dpi=300)
    
    # 5. Line plot showing jitter trends
    plt.figure(figsize=(14, 8))
    sns.lineplot(data=df, x='Packet_Size', y='Avg_Jitter_ms', 
                 hue='Protocol', style='Network', markers=True, 
                 linewidth=2.5, palette='Dark2')
    
    plt.title('Jitter Trends Across Packet Sizes')
    plt.xlabel('Packet Size (bytes)')
    plt.ylabel('Average Jitter (ms)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(title='', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig('charts/jitter_trends_line.png', dpi=300)

    # 6. Violin plot for jitter distribution
    plt.figure(figsize=(16, 10))
    sns.violinplot(data=df, x='Protocol', y='Avg_Jitter_ms', 
                  hue='Network', split=True, palette='Set1')
    
    plt.title('Jitter Distribution by Protocol and Network')
    plt.xlabel('Protocol')
    plt.ylabel('Average Jitter (ms)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(title='Network Type')
    plt.tight_layout()
    plt.savefig('charts/jitter_violin_plot.png', dpi=300)
    
    # 7. Correlation between jitter and latency
    plt.figure(figsize=(10, 8))
    sns.scatterplot(data=df, x='Avg_Latency_ms', y='Avg_Jitter_ms', 
                   hue='Protocol', style='Network', size='Packet_Size',
                   sizes=(50, 200), alpha=0.7)
    
    plt.title('Correlation Between Latency and Jitter')
    plt.xlabel('Average Latency (ms)')
    plt.ylabel('Average Jitter (ms)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(title='', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig('charts/jitter_latency_correlation.png', dpi=300)

    print("jitter visualization charts created successfully!")

# 3. Packet Delivery Ratio comparison
def plot_pdr_comparison(df):
    plt.figure(figsize=(14, 8))
    
    # Create facet grid by network and packet size
    g = sns.FacetGrid(df, col='Network', row='Packet_Size', height=3, aspect=1.5)
    g.map_dataframe(sns.barplot, x='Protocol', y='Delivery_Ratio', errorbar=None, palette='mako')
    
    g.set_axis_labels('Protocol', 'Packet Delivery Ratio (%)')
    g.set_titles(col_template='{col_name} Network', row_template='Packet Size: {row_name} bytes')
    
    # Set y-axis limits for better comparison
    for ax in g.axes.flat:
        ax.set_ylim(0, 105)  # Slightly above 100% for clear view
    
    plt.tight_layout()
    plt.savefig('charts/packet_delivery_ratio.png', dpi=300)
    
    # Focus on congested network only
    df_congested = df[df['Network'] == 'congested']
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_congested, x='Protocol', y='Delivery_Ratio', hue='Packet_Size', errorbar=None, palette='mako')
    plt.title('Packet Delivery Ratio in Congested Network')
    plt.ylabel('Delivery Ratio (%)')
    plt.ylim(0, 100)
    plt.legend(title='Packet Size (bytes)')
    plt.tight_layout()
    plt.savefig('charts/pdr_congested.png', dpi=300)

# 4. Concurrent Connections/Flows
def plot_concurrent_comparison(df):
    plt.figure(figsize=(12, 7))
    
    # Plot establishment time vs connection count
    sns.lineplot(data=df, x='Target_Count', y='Establishment_Time_ms', hue='Protocol', 
                marker='o', palette='tab10', linewidth=2.5)
    
    plt.title('Connection/Flow Establishment Time per Count')
    plt.xlabel('Number of Concurrent Connections/Flows')
    plt.ylabel('Establishment Time per Connection (ms)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('charts/concurrent_establishment_time.png', dpi=300)
    
    # Log scale version
    plt.figure(figsize=(12, 7))
    sns.lineplot(data=df, x='Target_Count', y='Establishment_Time_ms', hue='Protocol', 
                marker='o', palette='tab10', linewidth=2.5)
    plt.yscale('log')
    plt.title('Connection/Flow Establishment Time (Log Scale)')
    plt.xlabel('Number of Concurrent Connections/Flows')
    plt.ylabel('Establishment Time per Connection (ms) - Log Scale')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('charts/concurrent_establishment_time_log.png', dpi=300)
    
    # RINA-specific plot for bandwidth allocation
    if 'Bandwidth_Per_Flow_Mbps' in df.columns:
        rina_df = df[df['Protocol'] == 'RINA']
        if not rina_df.empty:
            plt.figure(figsize=(10, 6))
            sns.lineplot(data=rina_df, x='Target_Count', y='Bandwidth_Per_Flow_Mbps', 
                        marker='o', color='green', linewidth=2.5)
            plt.title('RINA Bandwidth Allocation per Flow')
            plt.xlabel('Number of Concurrent Flows')
            plt.ylabel('Bandwidth per Flow (Mbps)')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            plt.savefig('charts/rina_bandwidth_allocation.png', dpi=300)

# Add this function to your existing Python script
def extract_rtt_data():
    networks = ['perfect', 'lan', 'wifi', 'congested']
    packet_sizes = [64, 512, 1024, 4096]
    
    all_data = []
    
    # Extract RINA RTT data
    for network in networks:
        for size in packet_sizes:
            if str(size) in rina_data['round_trip_time_realistic'][network]:
                row = {
                    'Protocol': 'RINA',
                    'Network': network,
                    'Packet_Size': size,
                    'Avg_RTT_ms': rina_data['round_trip_time_realistic'][network][str(size)]['avg_rtt_ms'],
                    'Min_RTT_ms': rina_data['round_trip_time_realistic'][network][str(size)]['min_rtt_ms'],
                    'Max_RTT_ms': rina_data['round_trip_time_realistic'][network][str(size)]['max_rtt_ms']
                }
                all_data.append(row)
    
    # Extract RTT data from TCP latency_jitter data since it contains RTT
    for network in networks:
        for size in packet_sizes:
            if str(size) in tcp_data['latency_jitter_tcp'][network]:
                row = {
                    'Protocol': 'TCP',
                    'Network': network,
                    'Packet_Size': size,
                    'Avg_RTT_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['avg_rtt_ms'],
                    'Min_RTT_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['min_latency_ms'] * 2,  # Approximating min RTT
                    'Max_RTT_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['max_latency_ms'] * 2   # Approximating max RTT
                }
                all_data.append(row)
    
    # Extract RTT data from Hybrid latency_jitter data
    for network in networks:
        for size in packet_sizes:
            if str(size) in hybrid_data['latency_jitter_hybrid'][network]:
                row = {
                    'Protocol': 'Hybrid',
                    'Network': network,
                    'Packet_Size': size,
                    'Avg_RTT_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['avg_rtt_ms'],
                    'Min_RTT_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['min_latency_ms'] * 2,  # Approximating min RTT
                    'Max_RTT_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['max_latency_ms'] * 2   # Approximating max RTT
                }
                all_data.append(row)
    
    # Create dataframe
    df = pd.DataFrame(all_data)
    
    # Save to CSV
    df.to_csv('csv_output/rtt_comparison.csv', index=False)
    
    return df

def plot_detailed_scalability_comparison(df):
    """
    Create comprehensive scalability visualizations
    """
    # Import matplotlib inside the function to ensure it's available
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    # 1. Connection establishment time scaling
    plt.figure(figsize=(12, 7))
    sns.lineplot(data=df, x='Connection_Count', y='Establishment_Time_ms', 
                hue='Protocol', marker='o', palette='tab10', linewidth=2.5)
    
    plt.title('Connection Establishment Time Scaling')
    plt.xlabel('Number of Concurrent Connections')
    plt.ylabel('Establishment Time per Connection (ms)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('charts/scalability_establishment_time.png', dpi=300)
    plt.close()
    
    # 2. Success rate scaling
    plt.figure(figsize=(12, 7))
    sns.lineplot(data=df, x='Connection_Count', y='Success_Rate', 
                hue='Protocol', marker='o', palette='Set1', linewidth=2.5)
    
    plt.title('Connection Success Rate Scaling')
    plt.xlabel('Number of Concurrent Connections')
    plt.ylabel('Success Rate (%)')
    plt.ylim(0, 105)  # Give a bit of headroom above 100%
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('charts/scalability_success_rate.png', dpi=300)
    plt.close()
    
    # 3. If we have resource usage data, plot those as well
    if 'Memory_Usage_MB' in df.columns and not df['Memory_Usage_MB'].isna().all():
        plt.figure(figsize=(12, 7))
        sns.lineplot(data=df, x='Connection_Count', y='Memory_Usage_MB', 
                    hue='Protocol', marker='o', palette='viridis', linewidth=2.5)
        
        plt.title('Memory Usage Scaling')
        plt.xlabel('Number of Concurrent Connections')
        plt.ylabel('Memory Usage (MB)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig('charts/scalability_memory_usage.png', dpi=300)
        plt.close()
        
        # Memory efficiency
        if 'Memory_Efficiency' in df.columns:
            plt.figure(figsize=(12, 7))
            sns.lineplot(data=df, x='Connection_Count', y='Memory_Efficiency', 
                        hue='Protocol', marker='o', palette='viridis', linewidth=2.5)
            
            plt.title('Memory Efficiency Scaling (Connections per MB)')
            plt.xlabel('Number of Concurrent Connections')
            plt.ylabel('Connections per MB')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            plt.savefig('charts/scalability_memory_efficiency.png', dpi=300)
            plt.close()
    
    if 'CPU_Usage_Percent' in df.columns and not df['CPU_Usage_Percent'].isna().all():
        plt.figure(figsize=(12, 7))
        sns.lineplot(data=df, x='Connection_Count', y='CPU_Usage_Percent', 
                    hue='Protocol', marker='o', palette='rocket', linewidth=2.5)
        
        plt.title('CPU Usage Scaling')
        plt.xlabel('Number of Concurrent Connections')
        plt.ylabel('CPU Usage (%)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig('charts/scalability_cpu_usage.png', dpi=300)
        plt.close()
        
        # CPU efficiency
        if 'CPU_Efficiency' in df.columns:
            plt.figure(figsize=(12, 7))
            sns.lineplot(data=df, x='Connection_Count', y='CPU_Efficiency', 
                        hue='Protocol', marker='o', palette='rocket', linewidth=2.5)
            
            plt.title('CPU Efficiency Scaling (Connections per % CPU)')
            plt.xlabel('Number of Concurrent Connections')
            plt.ylabel('Connections per % CPU')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            plt.savefig('charts/scalability_cpu_efficiency.png', dpi=300)
            plt.close()
    
    # 4. RINA-specific bandwidth allocation scaling
    rina_df = df[df['Protocol'] == 'RINA']
    if 'Bandwidth_Per_Flow_Mbps' in df.columns and not rina_df.empty:
        plt.figure(figsize=(12, 7))
        
        # If we have multiple networks, show them separately
        if 'Network' in rina_df.columns:
            sns.lineplot(data=rina_df, x='Connection_Count', y='Bandwidth_Per_Flow_Mbps',
                        hue='Network', marker='o', linewidth=2.5)
        else:
            sns.lineplot(data=rina_df, x='Connection_Count', y='Bandwidth_Per_Flow_Mbps',
                        marker='o', color='green', linewidth=2.5)
        
        plt.title('RINA Bandwidth Allocation Scaling')
        plt.xlabel('Number of Concurrent Flows')
        plt.ylabel('Bandwidth per Flow (Mbps)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig('charts/scalability_rina_bandwidth.png', dpi=300)
        plt.close()
    
    # 5. Combined performance visualization - create radar chart
    try:
        # We need these imports for radar chart
        import numpy as np
        from matplotlib.projections import register_projection
        from matplotlib.projections.polar import PolarAxes
        from matplotlib.spines import Spine
        from matplotlib.path import Path
        from matplotlib.patches import Circle, RegularPolygon
        from matplotlib.transforms import Affine2D
        
        # Find protocols and metrics to compare
        protocols = df['Protocol'].unique()
        
        # Use the largest connection count for comparison
        max_conn_by_protocol = df.groupby('Protocol')['Connection_Count'].max()
        max_conn = max_conn_by_protocol.min()  # Use the smallest of the max connections to compare fairly
        
        comparison_df = df[df['Connection_Count'] == max_conn]
        
        # Define metrics for radar chart (normalized)
        metrics = []

        if 'Establishment_Time_ms' in comparison_df.columns:
            # Lower establishment time is better, so invert for radar chart
            comparison_df['Establishment_Speed'] = 1.0 / comparison_df['Establishment_Time_ms']
            comparison_df['Establishment_Speed'] = comparison_df['Establishment_Speed'] / comparison_df['Establishment_Speed'].max() * 100
            metrics.append('Establishment_Speed')
            
        if 'Success_Rate' in comparison_df.columns:
            metrics.append('Success_Rate')
            
        if 'Memory_Efficiency' in comparison_df.columns and not comparison_df['Memory_Efficiency'].isna().all():
            comparison_df['Memory_Efficiency_Normalized'] = comparison_df['Memory_Efficiency'] / comparison_df['Memory_Efficiency'].max() * 100
            metrics.append('Memory_Efficiency_Normalized')
            
        if 'CPU_Efficiency' in comparison_df.columns and not comparison_df['CPU_Efficiency'].isna().all():
            comparison_df['CPU_Efficiency_Normalized'] = comparison_df['CPU_Efficiency'] / comparison_df['CPU_Efficiency'].max() * 100
            metrics.append('CPU_Efficiency_Normalized')
        
        # If we have enough metrics, create a radar chart
        if len(metrics) >= 3:
            def radar_factory(num_vars, frame='circle'):
                """Create a radar chart with `num_vars` axes."""
                theta = np.linspace(0, 2*np.pi, num_vars, endpoint=False)
                
                class RadarAxes(PolarAxes):
                    name = 'radar'
                    
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, **kwargs)
                        self.set_theta_zero_location('N')
                        
                    def fill(self, *args, closed=True, **kwargs):
                        """Override fill so that line is closed by default"""
                        return super().fill(closed=closed, *args, **kwargs)
                        
                    def plot(self, *args, **kwargs):
                        """Override plot so that line is closed by default"""
                        lines = super().plot(*args, **kwargs)
                        for line in lines:
                            self._close_line(line)
                            
                    def _close_line(self, line):
                        x, y = line.get_data()
                        if x[0] != x[-1]:
                            x = np.concatenate((x, [x[0]]))
                            y = np.concatenate((y, [y[0]]))
                            line.set_data(x, y)
                            
                    def set_varlabels(self, labels):
                        self.set_thetagrids(np.degrees(theta), labels)
                        
                register_projection(RadarAxes)
                return theta

            # Create the radar chart
            theta = radar_factory(len(metrics), frame='circle')
            
            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='radar'))
            
            # Plot each protocol
            for protocol in protocols:
                protocol_data = comparison_df[comparison_df['Protocol'] == protocol]
                if not protocol_data.empty:
                    values = [protocol_data[metric].values[0] for metric in metrics]
                    ax.plot(theta, values, 'o-', linewidth=2, label=protocol)
                    ax.fill(theta, values, alpha=0.25)
            
            ax.set_varlabels(metrics)
            ax.set_ylim(0, 100)
            
            # Check if frame='circle' needs grid setup
            if hasattr(ax, 'set_rgrids'):
                grid = np.linspace(0, 100, 6)
                ax.set_rgrids(grid, labels=['%d%%' % x for x in grid])
            
            plt.legend(loc='upper right')
            plt.title(f'Protocol Scalability Comparison at {max_conn} Connections', size=15)
            plt.tight_layout()
            plt.savefig('charts/scalability_radar_comparison.png', dpi=300)
            plt.close()
            
    except Exception as e:
        print(f"Could not create radar chart: {e}")
    
    print("Scalability visualization charts created successfully!")

def create_scalability_summary_csv(df):
    """
    Create a summary CSV showing scalability metrics for each protocol
    """
    # Group by protocol and connection count
    if 'Network' in df.columns:
        summary = df.groupby(['Protocol', 'Network', 'Connection_Count']).agg({
            'Establishment_Time_ms': 'mean',
            'Success_Rate': 'mean',
            'Successful_Connections': 'mean',
            'Memory_Usage_MB': 'mean',
            'CPU_Usage_Percent': 'mean',
            'Memory_Efficiency': 'mean',
            'CPU_Efficiency': 'mean',
            'Bandwidth_Per_Flow_Mbps': 'mean'
        }).reset_index()
    else:
        summary = df.groupby(['Protocol', 'Connection_Count']).agg({
            'Establishment_Time_ms': 'mean',
            'Success_Rate': 'mean',
            'Successful_Connections': 'mean',
            'Memory_Usage_MB': 'mean',
            'CPU_Usage_Percent': 'mean',
            'Memory_Efficiency': 'mean',
            'CPU_Efficiency': 'mean'
        }).reset_index()
    
    # Calculate scaling factors
    protocols = summary['Protocol'].unique()
    
    scaling_data = []
    
    for protocol in protocols:
        protocol_data = summary[summary['Protocol'] == protocol].sort_values('Connection_Count')
        
        if len(protocol_data) >= 2:
            # Calculate how metrics scale between lowest and highest connection counts
            lowest = protocol_data.iloc[0]
            highest = protocol_data.iloc[-1]
            
            scaling_row = {
                'Protocol': protocol,
                'Min_Connections': lowest['Connection_Count'],
                'Max_Connections': highest['Connection_Count'],
                'Connection_Scale_Factor': highest['Connection_Count'] / lowest['Connection_Count'],
                'Establishment_Time_Scale_Factor': highest['Establishment_Time_ms'] / lowest['Establishment_Time_ms'],
                'Success_Rate_Change': highest['Success_Rate'] - lowest['Success_Rate'],
            }
            
            if 'Memory_Usage_MB' in protocol_data.columns and not protocol_data['Memory_Usage_MB'].isna().all():
                scaling_row['Memory_Usage_Scale_Factor'] = highest['Memory_Usage_MB'] / lowest['Memory_Usage_MB']
            
            if 'CPU_Usage_Percent' in protocol_data.columns and not protocol_data['CPU_Usage_Percent'].isna().all():
                scaling_row['CPU_Usage_Scale_Factor'] = highest['CPU_Usage_Percent'] / lowest['CPU_Usage_Percent']
            
            scaling_data.append(scaling_row)
    
    # Create scaling factors dataframe
    scaling_df = pd.DataFrame(scaling_data)
    
    # Save to CSV
    summary.to_csv('csv_output/scalability_metrics_by_protocol.csv', index=False)
    scaling_df.to_csv('csv_output/scalability_scaling_factors.csv', index=False)
    
    return summary, scaling_df


def plot_rtt_comparison(df):
    # 1. Create bar plots for Average RTT comparison
    plt.figure(figsize=(16, 10))
    g = sns.FacetGrid(df, col='Network', row='Packet_Size', height=3, aspect=1.5)
    g.map_dataframe(sns.barplot, x='Protocol', y='Avg_RTT_ms', errorbar=None, palette='viridis')
    
    g.set_axis_labels('Protocol', 'Average RTT (ms)')
    g.set_titles(col_template='{col_name} Network', row_template='Packet Size: {row_name} bytes')
    
    # Improve readability
    for ax in g.axes.flat:
        ax.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig('charts/rtt_comparison_bar.png', dpi=300)
    plt.close()
    
    # 2. Create error bar plots to show RTT ranges (min, avg, max)
    plt.figure(figsize=(18, 12))
    
    # Set up plot grid
    networks = df['Network'].unique()
    protocols = df['Protocol'].unique()
    
    fig, axes = plt.subplots(len(networks), 1, figsize=(12, 4*len(networks)))
    
    for i, network in enumerate(networks):
        ax = axes[i] if len(networks) > 1 else axes
        network_data = df[df['Network'] == network]
        
        for j, protocol in enumerate(protocols):
            protocol_data = network_data[network_data['Protocol'] == protocol]
            
            if not protocol_data.empty:
                # Group by packet size
                for packet_size in protocol_data['Packet_Size'].unique():
                    size_data = protocol_data[protocol_data['Packet_Size'] == packet_size]
                    
                    if not size_data.empty:
                        x_pos = j + (protocols.tolist().index(protocol) * 0.3) * (len(protocol_data['Packet_Size'].unique()) / 4)
                        
                        # Plot error bars for min, avg, max RTT
                        ax.errorbar(
                            x=x_pos + 0.1 * protocols.tolist().index(protocol),
                            y=size_data['Avg_RTT_ms'].values[0],
                            yerr=[[size_data['Avg_RTT_ms'].values[0] - size_data['Min_RTT_ms'].values[0]],
                                  [size_data['Max_RTT_ms'].values[0] - size_data['Avg_RTT_ms'].values[0]]],
                            fmt='o',
                            capsize=5,
                            label=f"{protocol} - {packet_size} bytes"
                        )
        
        ax.set_title(f'RTT Range for {network.capitalize()} Network')
        ax.set_ylabel('RTT (ms)')
        ax.set_xlabel('Protocol and Packet Size')
        ax.grid(True, linestyle='--', alpha=0.6)
        
        # Set x-ticks
        ax.set_xticks(range(len(protocols)))
        ax.set_xticklabels(protocols)
    
    plt.tight_layout()
    plt.savefig('charts/rtt_range_comparison.png', dpi=300)
    plt.close()
    
    # 3. Create a heatmap of RTT values
    pivot_df = df.pivot_table(
        index=['Protocol', 'Packet_Size'],
        columns='Network',
        values='Avg_RTT_ms'
    )
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(pivot_df, annot=True, cmap='YlGnBu', fmt='.2f', linewidths=.5)
    plt.title('Average RTT (ms) Across Networks, Protocols and Packet Sizes')
    plt.tight_layout()
    plt.savefig('charts/rtt_heatmap.png', dpi=300)
    plt.close()
    
    # 4. Create line plots to show trends of RTT across packet sizes
    plt.figure(figsize=(14, 8))
    for network in df['Network'].unique():
        network_data = df[df['Network'] == network]
        plt.figure(figsize=(10, 6))
        
        for protocol in network_data['Protocol'].unique():
            protocol_data = network_data[network_data['Protocol'] == protocol]
            protocol_data = protocol_data.sort_values('Packet_Size')
            plt.plot(protocol_data['Packet_Size'], protocol_data['Avg_RTT_ms'], 
                    marker='o', linewidth=2, label=protocol)
        
        plt.title(f'RTT Trends by Packet Size - {network.capitalize()} Network')
        plt.xlabel('Packet Size (bytes)')
        plt.ylabel('Average RTT (ms)')
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()
        plt.tight_layout()
        plt.savefig(f'charts/rtt_trends_{network}.png', dpi=300)
        plt.close()
    
    # 5. Create box plots to compare RTT distribution across protocols
    plt.figure(figsize=(14, 10))
    g = sns.FacetGrid(df, col='Network', height=6, aspect=1.2)
    g.map_dataframe(sns.boxplot, x='Protocol', y='Avg_RTT_ms', hue='Packet_Size', palette='Set3')
    
    g.set_axis_labels('Protocol', 'Average RTT (ms)')
    g.set_titles(col_template='{col_name} Network')
    g.add_legend(title='Packet Size (bytes)')
    
    # Improve readability
    for ax in g.axes.flat:
        ax.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig('charts/rtt_boxplot.png', dpi=300)
    plt.close()
    
    print("RTT visualization charts created successfully!")

def create_summary_comparison():
    # Create a summary table comparing key metrics
    throughput_df = pd.read_csv('csv_output/throughput_comparison.csv')
    latency_df = pd.read_csv('csv_output/latency_comparison.csv')
    pdr_df = pd.read_csv('csv_output/packet_delivery_ratio.csv')
    
    # Average throughput by protocol and network
    throughput_summary = throughput_df.groupby(['Protocol', 'Network'])['Throughput_Mbps'].mean().reset_index()
    throughput_summary = throughput_summary.pivot(index='Protocol', columns='Network', values='Throughput_Mbps')
    throughput_summary.columns = [f'Avg_Throughput_{col}' for col in throughput_summary.columns]
    
    # Average latency by protocol and network
    latency_summary = latency_df.groupby(['Protocol', 'Network'])['Avg_Latency_ms'].mean().reset_index()
    latency_summary = latency_summary.pivot(index='Protocol', columns='Network', values='Avg_Latency_ms')
    latency_summary.columns = [f'Avg_Latency_{col}' for col in latency_summary.columns]
    
    # Average PDR by protocol and network
    pdr_summary = pdr_df.groupby(['Protocol', 'Network'])['Delivery_Ratio'].mean().reset_index()
    pdr_summary = pdr_summary.pivot(index='Protocol', columns='Network', values='Delivery_Ratio')
    pdr_summary.columns = [f'Avg_PDR_{col}' for col in pdr_summary.columns]
    
    # Combine the summaries
    summary = pd.concat([throughput_summary, latency_summary, pdr_summary], axis=1)
    
    # Save to CSV
    summary.to_csv('csv_output/protocol_summary_comparison.csv')
    
    return summary

# Execute functions
throughput_df = extract_throughput_data()
latency_df = extract_latency_data()
pdr_df = extract_pdr_data()
concurrent_df = extract_concurrent_data()
rtt_df = extract_rtt_data()
scalability_df = extract_detailed_scalability_data()

plot_throughput_comparison(throughput_df)
plot_latency_comparison(latency_df)
plot_jitter_comparison(latency_df)
plot_pdr_comparison(pdr_df)
plot_rtt_comparison(rtt_df)
plot_concurrent_comparison(concurrent_df)
plot_detailed_scalability_comparison(scalability_df)

# Create summary
summary_df = create_summary_comparison()

print("Analysis complete! CSV files and charts have been created.")